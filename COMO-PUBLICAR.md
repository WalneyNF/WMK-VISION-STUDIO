# Publicação no GitHub — procedimento seguro

**Estado atual:** os arquivos deste pacote foram preparados localmente. Eles não foram enviados automaticamente ao repositório GitHub.

1. Salve o pacote ZIP em `D:\Ferramentas` e extraia em uma pasta separada do projeto já instalado.
2. Revise README, manuais e os arquivos que você deseja publicar.
3. Com Git autenticado, execute `PUBLICAR-NO-GITHUB.ps1` a partir da pasta extraída.
4. O script clona ou verifica `D:\Ferramentas\WMK-VISION-STUDIO-REPO`, confirma o remote, recusa alterações locais existentes, copia os arquivos da aplicação e manuais, e mostra um resumo do commit.
5. Digite `PUBLICAR` somente após verificar a lista de arquivos. Sem essa palavra, o script não envia nada ao GitHub.
6. Confirme o resultado no link https://github.com/WalneyNF/WMK-VISION-STUDIO

**Cuidado com o fork:** se esse repositório ainda for um fork do Supervision, sua estrutura `src/`, licença, testes e documentação originais devem ser preservadas. O script não apaga esses arquivos, mas pode substituir arquivos de mesmo nome na raiz (incluindo README). Por isso, revise o diff antes de confirmar.

**Não suba:** vídeos enviados por usuários, resultados, logs, pesos de modelos, `.venv`, credenciais e outros dados pessoais. O `.gitignore` inclui padrões para esses arquivos.

**Créditos:** Walney Moreira Klein — walneyk@hotmail.com. Também mantenha os avisos de licenças e direitos dos projetos originais.
