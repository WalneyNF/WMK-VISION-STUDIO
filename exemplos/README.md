# Experiências WMK — sem precisar programar

Todos os testes abaixo usam a interface web local. Anote **nome do vídeo**, **modelo**, **confiança**, **resolução**, **FPS de processamento**, **IDs por classe**, **cruzamentos** e **observações visuais**. Compare somente execuções equivalentes.

1. **Trânsito / confiança:** vehicles, YOLO11n, CPU, 416 px; teste 0,25 / 0,35 / 0,50. Resultado esperado: variação na quantidade de detecções; não existe limiar universal ideal.
2. **Trânsito / resolução:** repita 416 / 640 / 960 px. Observe objetos pequenos e tempo de execução.
3. **Pessoas:** people-walking, desmarque Somente veículos. Observe continuidade dos IDs quando alguém se esconde.
4. **Comércio:** grocery-store, desmarque Somente veículos. Veja pessoas parcialmente ocultas e incerteza em regiões movimentadas.
5. **Indústria:** milk-bottling-plant; desmarque Somente veículos. Nem toda categoria de produto é conhecida pelo modelo genérico.
6. **Contagem:** no vídeo de trânsito, mova a linha de 40% para 60%. Mudanças no resultado podem ocorrer pela posição e pela visibilidade.

Em todos os casos, confira pelo menos cinco eventos manualmente no vídeo anotado antes de tirar conclusões sobre precisão.

O arquivo `configuracoes-sugeridas.json` é um guia para copiar parâmetros na interface, **não um preset importável** nesta versão.
