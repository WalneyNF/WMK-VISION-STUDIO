"""Verificações offline: python -m unittest discover -s tests -v."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class EstruturaWMK(unittest.TestCase):
    def test_arquivos_principais(self):
        for nome in ['README.md','app.py','requirements.txt','templates/index.html','static/app.js','static/style.css','static/logo-wmk.png']:
            with self.subTest(nome=nome):
                self.assertTrue((ROOT / nome).is_file())

    def test_manuais_html(self):
        for arq in (ROOT/'manuais').glob('*.html'):
            with self.subTest(nome=arq.name):
                texto=arq.read_text(encoding='utf-8')
                self.assertIn('lang="pt-BR"',texto)
                self.assertIn('</html>',texto)
        self.assertGreaterEqual(len(list((ROOT/'manuais').glob('*.html'))),7)

    def test_presets_validos(self):
        data=json.loads((ROOT/'exemplos/configuracoes-sugeridas.json').read_text(encoding='utf-8'))
        for p in data['experimentos']:
            with self.subTest(preset=p['nome']):
                self.assertTrue(0 < p['confianca'] < 1)
                self.assertIn(p['modelo'],['yolo11n.pt','yolo11s.pt','yolov8n.pt'])

    def test_logo_e_creditos(self):
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('Walney Moreira Klein',readme)
        self.assertIn('static/logo-wmk.png',readme)

if __name__=='__main__': unittest.main()
