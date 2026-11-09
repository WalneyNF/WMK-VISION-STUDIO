# WMK Vision Studio — publicação assistida no fork, SEM reescrever histórico.
# Executar: powershell -ExecutionPolicy Bypass -File .\PUBLICAR-NO-GITHUB.ps1
# Pré-requisitos: Git instalado e GitHub autenticado (Git Credential Manager / SSH).
$ErrorActionPreference = 'Stop'
$origem = Split-Path -Parent $MyInvocation.MyCommand.Path
$destino = 'D:\Ferramentas\WMK-VISION-STUDIO-REPO'
$repo = 'https://github.com/WalneyNF/WMK-VISION-STUDIO.git'
Write-Host 'WMK Vision Studio — publicacao assistida' -ForegroundColor Cyan
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git nao encontrado.' }
if (-not (Test-Path "$destino\.git")) {
  git clone $repo $destino
  if ($LASTEXITCODE -ne 0) { throw 'Falha no clone. Nenhum push realizado.' }
}
Push-Location $destino
try {
  $url = git remote get-url origin
  if ($LASTEXITCODE -ne 0 -or $url -notmatch 'WalneyNF/WMK-VISION-STUDIO(\.git)?$') { throw "Destino inesperado: $url" }
  git fetch origin
  if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel atualizar referencias remotas.' }
  if ((git status --porcelain).Length -ne 0) { throw 'Ha alteracoes locais no repositorio. Revise-as antes de publicar.' }
  $branch=git branch --show-current
  if (-not $branch) { throw 'Repositorio nao esta em uma branch.' }
  $backup = Join-Path $origem 'backup-readme-remoto.md'
  if (Test-Path 'README.md') { Copy-Item 'README.md' $backup -Force }
  # Copia SOMENTE os arquivos da aplicacao e documentacao, preservando src/, tests/ originais, LICENSE e historico do fork.
  foreach ($arquivo in @('README.md','.gitignore','app.py','requirements.txt','INSTALAR.cmd','INICIAR.cmd','CORRIGIR-DEPENDENCIAS.cmd')) {
    Copy-Item (Join-Path $origem $arquivo) (Join-Path $destino $arquivo) -Force
  }
  foreach ($pasta in @('static','templates','assets','manuais','exemplos')) {
    $alvo = Join-Path $destino $pasta
    if (-not (Test-Path $alvo)) { New-Item -ItemType Directory -Path $alvo | Out-Null }
    Copy-Item (Join-Path $origem ($pasta + '\*')) $alvo -Recurse -Force
  }
  git add README.md .gitignore app.py requirements.txt INSTALAR.cmd INICIAR.cmd CORRIGIR-DEPENDENCIAS.cmd static templates assets manuais exemplos
  Write-Host "Arquivos preparados na branch $branch. Revise as alteracoes:" -ForegroundColor Yellow
  git diff --cached --stat
  $resposta=Read-Host 'Digite PUBLICAR para confirmar commit e push; qualquer outra resposta cancela'
  if ($resposta -cne 'PUBLICAR') { Write-Host 'Publicacao cancelada: arquivos preparados localmente, sem commit/push.'; exit 0 }
  git commit -m 'docs: WMK Vision Studio em pt-BR com manuais e exemplos'
  if ($LASTEXITCODE -ne 0) { throw 'Commit falhou.' }
  git push origin $branch
  if ($LASTEXITCODE -ne 0) { throw 'Push falhou. Verifique autenticacao e branch.' }
  Write-Host 'Publicacao concluida no GitHub.' -ForegroundColor Green
} finally { Pop-Location }
