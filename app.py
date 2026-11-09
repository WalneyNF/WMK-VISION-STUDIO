"""WMK Vision Studio - laboratório web local. Requer instalação de requirements.txt."""
from __future__ import annotations
import json, os, shutil, threading, time, uuid, subprocess, logging, traceback, sys, urllib.request, urllib.error
from logging.handlers import RotatingFileHandler
from pathlib import Path
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
UPLOAD = ROOT / 'uploads'; OUTPUT = ROOT / 'resultados'; LOGS = ROOT / 'logs'
UPLOAD.mkdir(exist_ok=True); OUTPUT.mkdir(exist_ok=True); LOGS.mkdir(exist_ok=True)
logger = logging.getLogger('wmk.vision')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = RotatingFileHandler(LOGS / 'wmk-vision.log', maxBytes=3_000_000, backupCount=4, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(handler)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(console)
logger.info('WMK Vision iniciado | Python %s', sys.version.split()[0])
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024**3
ALLOWED = {'.mp4','.avi','.mov','.mkv','.webm','.m4v'}
JOBS = {}; LOCK=threading.Lock()
MODELS = {'yolo11n.pt','yolo11s.pt','yolov8n.pt'}

# Catálogo de mídia de demonstração; URLs fixas para evitar acesso arbitrário a rede interna.
VIDEO_BASE='https://media.roboflow.com/supervision/video-examples/'
VIDEO_CATALOG={
    'vehicles':('vehicles.mp4','Trânsito: veículos','carros e caminhões; linhas de contagem',True),
    'vehicles-2':('vehicles-2.mp4','Trânsito: segunda cena','comparação de cenas e iluminação',True),
    'people-walking':('people-walking.mp4','Pessoas caminhando','rastreamento e fluxo de pessoas',False),
    'market-square':('market-square.mp4','Praça pública','movimentação em áreas abertas',False),
    'grocery-store':('grocery-store.mp4','Mercado / comércio','ocupação e circulação de pessoas',False),
    'subway':('subway.mp4','Estação de metrô','movimentação e cenas densas',False),
    'milk-bottling-plant':('milk-bottling-plant.mp4','Indústria / garrafas','testar classes existentes; modelo específico pode ser necessário',False),
    'beach':('beach-1.mp4','Praia','pessoas em ambiente aberto',False),
    'basketball':('basketball-1.mp4','Basquete','movimento rápido e oclusões',False),
    'skiing':('skiing.mp4','Esqui','rastreamento em movimento',False),
}
CATALOG_DOWNLOAD_LIMIT=250*1024*1024

@app.get('/api/catalogo')
def catalogo():
    return jsonify(videos=[dict(id=k,arquivo=v[0],nome=v[1],objetivo=v[2],somente_veiculos=v[3],disponivel_local=bool((UPLOAD/v[0]).is_file())) for k,v in VIDEO_CATALOG.items()])

@app.post('/api/catalogo/<video_id>/baixar')
def baixar_exemplo(video_id):
    # Baixar apenas nomes previamente permitidos, nunca receber URL do navegador.
    if video_id not in VIDEO_CATALOG:return jsonify(error='Vídeo não está no catálogo.'),404
    filename, title,_,_=VIDEO_CATALOG[video_id]
    dest=UPLOAD/filename
    if dest.is_file() and dest.stat().st_size>0:return jsonify(id='catalogo',filename=filename,size=dest.stat().st_size,origem='cache_local')
    temp=UPLOAD/(filename+'.download')
    total=0
    try:
        req=urllib.request.Request(VIDEO_BASE+filename,headers={'User-Agent':'WMK-Vision-Studio/1.2'})
        with urllib.request.urlopen(req, timeout=45) as resp, temp.open('wb') as target:
            length=int(resp.headers.get('Content-Length') or 0)
            if length>CATALOG_DOWNLOAD_LIMIT:raise ValueError('Vídeo ultrapassa o limite de 250 MB.')
            while True:
                chunk=resp.read(256*1024)
                if not chunk:break
                total+=len(chunk)
                if total>CATALOG_DOWNLOAD_LIMIT:raise ValueError('Vídeo ultrapassa o limite de 250 MB.')
                target.write(chunk)
        if total<1024:raise ValueError('Download muito pequeno: arquivo pode ser inválido.')
        temp.replace(dest)
        logger.info('Catálogo: %s, %s bytes',filename,total)
        return jsonify(id='catalogo',filename=filename,size=total,origem='download')
    except Exception as exc:
        temp.unlink(missing_ok=True)
        logger.exception('Falha ao baixar exemplo %s',video_id)
        return jsonify(error=f'{type(exc).__name__}: {exc}'),502

@app.get('/api/catalogo/<video_id>/arquivo')
def catalogo_arquivo(video_id):
    if video_id not in VIDEO_CATALOG:return jsonify(error='Vídeo não está no catálogo.'),404
    filename=VIDEO_CATALOG[video_id][0]
    if not (UPLOAD/filename).is_file():return jsonify(error='Baixe o vídeo primeiro.'),404
    return send_from_directory(UPLOAD,filename,conditional=True)


def num(value, default, lo, hi, caster=float):
    try: n=caster(value); return max(lo, min(hi,n))
    except (TypeError, ValueError): return default

def snapshot(j):
    return {k:v for k,v in j.items() if k not in ('private_input',)}

def update(jobid, **kw):
    with LOCK: JOBS[jobid].update(kw)

def event_log(jobid, level, message):
    # Logs persistentes, mais últimos registros visíveis na interface.
    getattr(logger, level.lower(), logger.info)('[%s] %s', jobid, message)
    with LOCK:
        if jobid in JOBS:
            recent = JOBS[jobid].setdefault('logs', [])
            recent.append({'hora':time.strftime('%H:%M:%S'), 'nivel':level.upper(), 'mensagem':message})
            if len(recent) > 150: del recent[:-150]

def process(jobid, src, config):
    cap = None; writer = None
    started=time.monotonic()
    try:
        import cv2
        import numpy as np
        import supervision as sv
        from ultralytics import YOLO
        import lap  # obrigatório para associação de IDs no ByteTrack
        event_log(jobid, 'info', f'Dependências carregadas | lap={getattr(lap, "__version__", "disponível")}')
        update(jobid,status='iniciando',message='Abrindo vídeo e carregando detector...')
        event_log(jobid, 'info', f'Abrindo arquivo {src.name} | parâmetros: {json.dumps(config, ensure_ascii=False)}')
        cap=cv2.VideoCapture(str(src))
        if not cap.isOpened(): raise RuntimeError('OpenCV não conseguiu abrir o vídeo enviado.')
        fps=float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        if not 0 < fps <= 240: fps=25.0
        w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if w < 1 or h < 1: raise RuntimeError('Dimensões do vídeo inválidas.')
        # Redimensionamento da saída reduz escrita e uso de disco; inferência é controlada por imgsz.
        max_dim=int(config['saida_largura']); scale=min(1.0,max_dim/w)
        ow=max(2,int(w*scale)//2*2); oh=max(2,int(h*scale)//2*2)
        dest=OUTPUT / f'{jobid}-processado.mp4'
        writer=cv2.VideoWriter(str(dest), cv2.VideoWriter_fourcc(*'mp4v'), fps, (ow,oh))
        if not writer.isOpened(): raise RuntimeError('Não foi possível inicializar a gravação do vídeo.')
        event_log(jobid, 'info', f'Vídeo: {w}x{h}, {fps:.2f} fps, {total} quadros; saída {ow}x{oh}')
        model=YOLO(config['modelo'])
        event_log(jobid, 'info', 'Modelo YOLO carregado: ' + config['modelo'])
        # Linha horizontal ajustável em % da altura; cruzamentos em ambas as direções.
        yy=int(oh*config['linha']/100)
        zone=sv.LineZone(start=sv.Point(0,yy), end=sv.Point(ow-1, yy))
        box=sv.BoxAnnotator(); label=sv.LabelAnnotator(); trace=sv.TraceAnnotator(trace_length=40)
        zone_anno=sv.LineZoneAnnotator(thickness=3,text_thickness=2,text_scale=.7)
        unique=defaultdict(set); frames=0; inferred=0; events=[]; previous=(0,0); last_frame=None
        step=int(config['intervalo']); device=config['dispositivo']
        update(jobid,status='processando',message='Analisando quadros...',total_frames=total)
        while True:
            ok, frame=cap.read()
            if not ok: break
            frames+=1
            if (frames-1)%step != 0 and last_frame is not None:
                writer.write(last_frame)
                continue
            if (ow,oh)!=(w,h): frame=cv2.resize(frame,(ow,oh),interpolation=cv2.INTER_AREA)
            result=model.track(frame,persist=True,tracker='bytetrack.yaml',conf=config['confianca'],imgsz=int(config['resolucao']),verbose=False,device=device)[0]
            det=sv.Detections.from_ultralytics(result)
            # Evita falsas categorias como 'train' quando o usuário restringe às classes veiculares.
            if config['apenas_veiculos']:
                names_allowed={'car','truck','bus','motorcycle','bicycle'}
                det=det[np.array([result.names[int(c)] in names_allowed for c in det.class_id],dtype=bool)]
            tracked=det if det.tracker_id is None else det[det.tracker_id >= 0]
            if tracked.tracker_id is not None:
                for cls,tid in zip(tracked.class_id,tracked.tracker_id):
                    unique[result.names[int(cls)]].add(int(tid))
                zone.trigger(tracked)
                current=(int(zone.in_count),int(zone.out_count))
                for direction, amount in [('entrada',current[0]-previous[0]),('saida',current[1]-previous[1])]:
                    for _ in range(max(0,amount)):
                        events.append({'tempo_s':round((frames-1)/fps,2),'quadro':frames,'tipo':'cruzamento','direcao':direction})
                previous=current
            img=box.annotate(frame.copy(),det)
            ids=det.tracker_id
            texts=[f"{result.names[int(cls)]}"+(f" #{int(ids[i])}" if ids is not None else '')+f" {float(conf):.2f}" for i,(cls,conf) in enumerate(zip(det.class_id,det.confidence))]
            img=label.annotate(img,det,labels=texts)
            if tracked.tracker_id is not None: img=trace.annotate(img,tracked)
            img=zone_anno.annotate(img,zone)
            last_frame=img; writer.write(img); inferred+=1
            if inferred % 25 == 0: event_log(jobid, 'info', f'Quadros inferidos: {inferred} / lidos: {frames}; cruzamentos: {zone.in_count}+{zone.out_count}')
            if inferred % 5 == 0:
                update(jobid,progress=round(100*frames/total,1) if total else 0,processed_frames=frames,inferred_frames=inferred,entries=int(zone.in_count),exits=int(zone.out_count),elapsed=round(time.monotonic()-started,1),message=f'Analisados {inferred} quadros')
        if frames==0: raise RuntimeError('O arquivo não contém quadros de vídeo decodificáveis.')
        cap.release(); cap=None; writer.release(); writer=None
        playable=dest
        ffmpeg=shutil.which('ffmpeg')
        if ffmpeg:
            browser=OUTPUT/f'{jobid}-web.mp4'
            command=[ffmpeg,'-y','-loglevel','error','-i',str(dest),'-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(browser)]
            update(jobid,message='Convertendo vídeo para reprodução no navegador...')
            r=subprocess.run(command,capture_output=True,text=True,timeout=1800)
            if r.returncode==0 and browser.is_file() and browser.stat().st_size: playable=browser
        report={'projeto':'WMK Vision Studio','arquivo_origem':src.name,'modelo':config['modelo'],'configuracao':config,'video':{'largura_origem':w,'altura_origem':h,'largura_saida':ow,'altura_saida':oh,'fps':round(fps,2),'duracao_s':round(frames/fps,2)},'quadros_lidos':frames,'quadros_inferidos':inferred,'segundos_execucao':round(time.monotonic()-started,2),'fps_processamento':round(inferred/max(.001,time.monotonic()-started),2),'ids_unicos_por_classe':{k:len(v) for k,v in sorted(unique.items())},'cruzamentos_linha':{'entrada':int(zone.in_count),'saida':int(zone.out_count)},'eventos':events,'observacoes':['IDs únicos não equivalem necessariamente a objetos reais distintos.','Cruzamentos dependem da qualidade do rastreamento, visibilidade e posição da linha.','Não há medição de velocidade física sem calibração.']}
        path=OUTPUT/f'{jobid}-relatorio.json'; path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        event_log(jobid, 'info', f'Concluído em {report["segundos_execucao"]} s. Relatório: {path.name}')
        update(jobid,status='concluido',progress=100,processed_frames=frames,inferred_frames=inferred,entries=int(zone.in_count),exits=int(zone.out_count),elapsed=report['segundos_execucao'],message='Processamento concluído',video_url=f'/api/resultado/{playable.name}',json_url=f'/api/resultado/{path.name}',report=report)
    except Exception as exc:
        short=f'{type(exc).__name__}: {exc}'
        suggestion = 'Verifique o log do processamento.'
        if isinstance(exc, ModuleNotFoundError) and getattr(exc, 'name', '') == 'lap':
            suggestion = r'Dependência de rastreamento ausente. Execute CORRIGIR-DEPENDENCIAS.cmd na pasta do projeto para instalar lap.'
        elif isinstance(exc, ModuleNotFoundError):
            suggestion = f'Dependência Python ausente ({exc.name}). Execute CORRIGIR-DEPENDENCIAS.cmd.'
        elif 'CUDA' in short.upper() or 'GPU' in short.upper():
            suggestion = 'Altere Dispositivo para CPU e teste novamente.'
        event_log(jobid, 'error', short)
        logger.error('[%s] Traceback: %s', jobid, traceback.format_exc())
        update(jobid,status='erro',message=short,diagnostico=suggestion,traceback=traceback.format_exc(),elapsed=round(time.monotonic()-started,2))
    finally:
        if cap is not None: cap.release()
        if writer is not None: writer.release()


@app.get('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(ROOT/'assets',filename)

@app.get('/manuais/<path:filename>')
def manuais(filename):
    return send_from_directory(ROOT/'manuais',filename)

@app.get('/')
def index(): return render_template('index.html')

@app.post('/api/upload')
def upload():
    file=request.files.get('video')
    if not file or not file.filename: return jsonify(error='Selecione um vídeo.'),400
    suffix=Path(file.filename).suffix.lower()
    if suffix not in ALLOWED: return jsonify(error='Formato não permitido. Utilize MP4, AVI, MOV, MKV ou WEBM.'),400
    uid=uuid.uuid4().hex[:12]; safe=secure_filename(Path(file.filename).stem)[:65] or 'video'
    path=UPLOAD/f'{uid}-{safe}{suffix}'; file.save(path)
    logger.info('UPLOAD %s | %s bytes', path.name, path.stat().st_size)
    if not path.stat().st_size: path.unlink(missing_ok=True); return jsonify(error='Arquivo vazio.'),400
    return jsonify(id=uid,filename=file.filename,size=path.stat().st_size)

@app.post('/api/processar')
def start():
    data=request.get_json(silent=True) or {}; uid=str(data.get('id',''))
    found=([UPLOAD / str(data.get('catalogo'))] if str(data.get('catalogo')) in [v[0] for v in VIDEO_CATALOG.values()] and (UPLOAD / str(data.get('catalogo'))).is_file() else []) if uid=='catalogo' else (list(UPLOAD.glob(f'{uid}-*')) if len(uid)==12 and uid.isalnum() else [])
    if not found: return jsonify(error='Vídeo não encontrado. Faça o upload novamente.'),404
    with LOCK:
        if any(j['status'] in ('iniciando','processando') for j in JOBS.values()): return jsonify(error='Já existe um processamento em andamento. Aguarde a conclusão.'),409
    modelo=data.get('modelo','yolo11n.pt')
    if modelo not in MODELS: return jsonify(error='Modelo não permitido.'),400
    config={'modelo':modelo,'confianca':round(num(data.get('confianca'),.35,.05,.95),2),'resolucao':int(num(data.get('resolucao'),416,320,1280,int)),'linha':int(num(data.get('linha'),50,5,95,int)),'intervalo':int(num(data.get('intervalo'),1,1,10,int)),'saida_largura':int(num(data.get('saida_largura'),1280,320,3840,int)),'dispositivo':'cpu' if data.get('dispositivo')!='0' else '0','apenas_veiculos':bool(data.get('apenas_veiculos',True))}
    jobid=uuid.uuid4().hex[:12]
    with LOCK: JOBS[jobid]={'id':jobid,'status':'iniciando','message':'Iniciando','progress':0,'processed_frames':0,'inferred_frames':0,'entries':0,'exits':0,'elapsed':0,'filename':found[0].name}
    logger.info('TAREFA criada %s', jobid)
    threading.Thread(target=process,args=(jobid,found[0],config),daemon=True).start()
    return jsonify(id=jobid),202

@app.get('/api/status/<jobid>')
def status(jobid):
    with LOCK: job=JOBS.get(jobid); data=snapshot(job) if job else None
    return jsonify(data) if data else (jsonify(error='Tarefa não encontrada'),404)

@app.get('/api/resultado/<filename>')
def result(filename):
    if Path(filename).name != filename: return jsonify(error='Arquivo inválido'),400
    if not (filename.endswith('-relatorio.json') or filename.endswith('-processado.mp4') or filename.endswith('-web.mp4')): return jsonify(error='Arquivo inválido'),400
    return send_from_directory(OUTPUT,filename,as_attachment=filename.endswith('.json'),conditional=True)

@app.get('/api/saude')
def health():
    deps={}
    for name in ('cv2','supervision','ultralytics','lap'):
        try: __import__(name); deps[name]='ok'
        except Exception as e: deps[name]=str(e)[:120]
    return jsonify(status='ok' if all(x=='ok' for x in deps.values()) else 'dependencias_pendentes',dependencias=deps,ffmpeg=bool(shutil.which('ffmpeg')))

@app.get('/api/logs')
def logs():
    # Somente no servidor local. Não expõe arquivos fora da pasta de logs.
    try:
        lines=(LOGS/'wmk-vision.log').read_text(encoding='utf-8', errors='replace').splitlines()
        return jsonify(linhas=lines[-250:],arquivo=str(LOGS/'wmk-vision.log'))
    except OSError as exc:
        return jsonify(linhas=[],erro=str(exc))

@app.errorhandler(413)
def too_large(e):
    logger.warning('Upload excedeu tamanho máximo de 2GB')
    return jsonify(error='O vídeo excede 2 GB. Reduza o arquivo e tente novamente.'), 413

@app.errorhandler(Exception)
def unexpected(exc):
    logger.exception('Erro HTTP não tratado: %s', exc)
    return jsonify(error=f'{type(exc).__name__}: {exc}'),500

if __name__=='__main__':
    app.run(host='127.0.0.1',port=int(os.environ.get('WMK_PORT',8767)),debug=False,threaded=True)
