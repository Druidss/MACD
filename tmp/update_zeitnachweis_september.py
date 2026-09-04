from copy import deepcopy
from datetime import date
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree

src = Path('/Users/adrian/Downloads/Zeitnachweis_08_2026.docx')
out_dir = Path('/Users/adrian/Desktop/BA/MACD/output/word')
out_dir.mkdir(parents=True, exist_ok=True)
dst = out_dir / 'Zeitnachweis_09_2026.docx'

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{%s}' % NS['w']

with ZipFile(src, 'r') as zin:
    files = {name: zin.read(name) for name in zin.namelist()}

root = etree.fromstring(files['word/document.xml'])

# Update the month heading and date range while preserving all formatting runs.
replacements = {
    'Stundenzettel August ': 'Stundenzettel September ',
    'vom 01.08.2026 bis ': 'vom 01.09.2026 bis ',
    '31.08.2026': '30.09.2026',
}
for node in root.xpath('.//w:t', namespaces=NS):
    if node.text in replacements:
        node.text = replacements[node.text]

tables = root.xpath('.//w:tbl', namespaces=NS)
if len(tables) < 2:
    raise RuntimeError('Expected the title table and the main time table.')

main = tables[1]
rows = main.xpath('./w:tr', namespaces=NS)
if len(rows) < 32:
    raise RuntimeError(f'Expected 32 rows including header, found {len(rows)}.')

weekday = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
for day in range(1, 31):
    row = rows[day]
    cells = row.xpath('./w:tc', namespaces=NS)
    day_text = cells[0].xpath('.//w:t', namespaces=NS)
    date_text = cells[1].xpath('.//w:t', namespaces=NS)
    if not day_text or not date_text:
        raise RuntimeError(f'Missing day/date text in row {day}.')
    day_text[0].text = weekday[date(2026, 9, day).weekday()]
    date_text[0].text = f'{day:02d}.09.2026'

# September has 30 days; remove the former 31 August row.
main.remove(rows[31])

files['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone='yes')
with ZipFile(dst, 'w', ZIP_DEFLATED) as zout:
    for name, data in files.items():
        zout.writestr(name, data)

print(dst)
