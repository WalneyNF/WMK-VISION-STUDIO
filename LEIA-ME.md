# WMK Vision Studio — Laboratório de análise de vídeos

**Autor do projeto WMK:** Walney Moreira Klein — walneyk@hotmail.com

## Instalação e execução no Windows
1. Extraia esta pasta em `D:\Ferramentas\WMK-Vision-Studio`.
2. Execute `INSTALAR.cmd` **uma vez**. O ambiente Python e o cache pip são locais à pasta.
3. Para abrir depois, execute `INICIAR.cmd`.
4. Acesse `http://127.0.0.1:8767`.
5. Escolha um vídeo local, ajuste os parâmetros e clique **Iniciar análise do vídeo**.
6. Acompanhe progresso, entradas, saídas e obtenha o vídeo anotado e o JSON.

**Observações:** a primeira execução baixa pesos do YOLO (~MB); a inferência pode ser lenta em CPU. A saída é MP4 (`mp4v`). Se FFmpeg estiver instalado no PATH, a aplicação converte automaticamente para H.264, mais compatível com navegadores. Sem FFmpeg, o vídeo processado ainda pode ser baixado e aberto no VLC, mas pode não tocar no navegador.

**Para usar seu vídeo anterior**: carregue o MP4 original de trânsito, não o vídeo já anotado. Um vídeo já anotado pode receber caixas duplicadas.

## Parâmetros
- **YOLO11n**: mais leve; **YOLO11s**: mais lento, pode detectar mais objetos; **YOLOv8n**: alternativa.
- **Confiança**: probabilidade mínima estimada pelo detector; alta reduz falsas detecções, mas pode perder objetos.
- **Resolução de inferência**: maior detecta melhor objetos pequenos em alguns casos, porém custa CPU/GPU.
- **Linha de contagem**: posição horizontal em porcentagem da imagem; desenhe/arraste na prévia.
- **Intervalo**: quadro 1 de cada N. Quadros não inferidos repetem a última imagem anotada; ajuda a acelerar, mas pode comprometer rastreamento e eventos.
- **Saída**: largura do vídeo anotado; original é preservado sem modificação.
- **CPU/GPU**: GPU 0 exige PyTorch CUDA compatível; use CPU inicialmente.
- **Somente veículos**: filtra classes do COCO, não substitui modelo treinado para uma tarefa específica.

## Métricas
- **Quadros inferidos**: quadros efetivamente analisados pelo modelo.
- **IDs únicos**: identificadores atribuídos pelo rastreador, não contagem garantida de objetos distintos.
- **Entradas/saídas**: eventos quando uma trajetória cruza a linha orientada horizontalmente; não representam necessariamente entrada/saída física da estrada.
- **FPS de processamento**: velocidade alcançada pelo sistema, diferente de FPS original do vídeo.
- **Eventos**: hora e número do quadro de cruzamentos agregados (não associam cada evento a uma classe ou ID específico).

## Estrutura
- `app.py`: servidor Flask, upload, execução em thread e relatório.
- `templates/index.html`: painel principal.
- `static/`: aparência CSS e interações JS.
- `uploads/`: vídeos enviados localmente.
- `resultados/`: MP4 processados e JSON.
- `logs/instalacao.log`: log da instalação.

## Segurança e limites
- Servidor vinculado apenas a `127.0.0.1`; não é para publicação direta na internet.
- Limite de upload: 2 GB. Não há login nem isolamento multiusuário.
- Uma análise ativa por vez. Os históricos de tarefas são armazenados em memória e somem após reiniciar o servidor; os arquivos permanecem em disco.
- Os vídeos permanecem em disco e não são removidos automaticamente. Faça limpeza manual de `uploads` e `resultados` quando não estiver analisando.
- Pesos de modelos YOLO baixados pelo Ultralytics podem ir para diretórios padrão da plataforma.
- Licença MIT do Supervision não substitui as condições de licença aplicáveis ao Ultralytics (AGPL-3.0/comercial, conforme uso).

## Testes rápidos
- `http://127.0.0.1:8767/api/saude` mostra disponibilidade de dependências e FFmpeg.
- Para investigar erros de processamento, observe o texto em **Estado** e o terminal que executa `INICIAR.cmd`.

## Escopo atual e limitações
Funciona como laboratório local de vídeo, **não** sistema de monitoramento CCTV contínuo. Não implementa câmeras IP/RTSP, múltiplas linhas, agentes LLM, banco persistente, autenticação, painel de edição de polígonos ou estatísticas avançadas. O painel é real e as métricas só são preenchidas pelos resultados de processamento; não há contagens simuladas. A disponibilidade efetiva de detecção depende das dependências, do modelo e do vídeo enviados.


## Atualização v1.1 — Erro `No module named lap`
O Ultralytics utiliza a biblioteca `lap` no rastreador ByteTrack. Ela não constava no primeiro `requirements.txt`, e por isso o vídeo podia falhar ao começar a análise. A v1.1 adiciona `lap>=0.5.12`.

**Atualizar instalação existente:** feche a janela atual do servidor, substitua os arquivos do programa e execute `CORRIGIR-DEPENDENCIAS.cmd`; em seguida `INICIAR.cmd`. Não apague `.venv`, vídeos ou resultados existentes. Se instalar do zero, execute `INSTALAR.cmd`.

**Diagnóstico:** o painel exibe erro, recomendação, traceback e logs; os arquivos persistentes ficam em `logs/wmk-vision.log`, `logs/instalacao.log` e `logs/correcao-dependencias.log`. Botões permitem copiar ou baixar logs.

**Créditos:** Walney Moreira Klein — walneyk@hotmail.com, agora visíveis no cabeçalho principal.
