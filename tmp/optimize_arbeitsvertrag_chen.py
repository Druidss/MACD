import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree

src = Path('/Users/adrian/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_k55s0dvj210n12_ec32/temp/RWTemp/2026-08/0bf421cbe27a781105a99f64f37cb9c3/Arbeitsvertrag Chen.docx')
out_dir = Path('/Users/adrian/Desktop/BA/MACD/output/contract')
out_dir.mkdir(parents=True, exist_ok=True)
dst = out_dir / 'Arbeitsvertrag_Chen_optimiert.docx'

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{%s}' % NS['w']
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

with ZipFile(src, 'r') as zin:
    files = {name: zin.read(name) for name in zin.namelist()}

root = etree.fromstring(files['word/document.xml'])
body_started = False
changed = 0

for para in root.xpath('.//w:p', namespaces=NS):
    texts = para.xpath('.//w:t', namespaces=NS)
    original = ''.join((t.text or '') for t in texts)
    if 'Goldene-Bären-Str.' in original:
        ppr = para.find('w:pPr', namespaces=NS)
        if ppr is None:
            ppr = etree.Element(W + 'pPr')
            para.insert(0, ppr)
        jc = ppr.find('w:jc', namespaces=NS)
        if jc is None:
            jc = etree.SubElement(ppr, W + 'jc')
        jc.set(W + 'val', 'left')
    if 'Das Arbeitsverhältnis beginnt am' in original:
        body_started = True
    if original.strip().startswith('Landsberg am Lech, den'):
        body_started = False
    if not body_started or not texts:
        continue

    if re.fullmatch(r'\s*§\s*\d+\s*', original):
        continue

    ppr = para.find('w:pPr', namespaces=NS)
    jc = ppr.find('w:jc', namespaces=NS) if ppr is not None else None
    alignment = jc.get(W + 'val') if jc is not None else None
    if alignment == 'center':
        continue

    # Rebuild ordinary body text as a continuous sentence. This removes
    # artificial run boundaries and manual line breaks that caused stretched
    # spaces while preserving the paragraph's font and numbering format.
    clean = re.sub(r'\s+', ' ', original).strip()
    clean = clean.replace('bekannt zugeben', 'bekannt zu geben')
    clean = clean.replace('Zuviel erhaltenes', 'Zu viel erhaltenes')
    clean = clean.replace('§ 622  Abs.', '§ 622 Abs.')
    clean = clean.replace('§ 622 Abs. 5 BGB  vorliegen', '§ 622 Abs. 5 BGB vorliegen')

    texts[0].text = clean
    texts[0].set(XML_SPACE, 'preserve')
    for node in texts[1:]:
        parent = node.getparent()
        parent.remove(node)
    for br in para.xpath('.//w:br', namespaces=NS):
        br.getparent().remove(br)
    if ppr is None:
        ppr = etree.Element(W + 'pPr')
        para.insert(0, ppr)
    if jc is None:
        jc = etree.SubElement(ppr, W + 'jc')
    jc.set(W + 'val', 'left')
    changed += 1

files['word/document.xml'] = etree.tostring(
    root, xml_declaration=True, encoding='UTF-8', standalone='yes'
)
with ZipFile(dst, 'w', ZIP_DEFLATED) as zout:
    for name, data in files.items():
        zout.writestr(name, data)

print(dst)
print(f'Optimized paragraphs: {changed}')
