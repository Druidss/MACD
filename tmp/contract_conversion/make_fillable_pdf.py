from pathlib import Path
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pypdf.generic import (
    ArrayObject, BooleanObject, DecodedStreamObject, DictionaryObject,
    FloatObject, NameObject, NumberObject, TextStringObject,
)

ROOT = Path('/Users/adrian/Desktop/BA/MACD')
base = ROOT / 'tmp/contract_conversion/docx_render/Arbeitsvertrag_Bai_Shaodong_editierbar.pdf'
output = ROOT / 'output/contract/Arbeitsvertrag_Bai_Shaodong_ausfuellbar.pdf'
header_png = ROOT / 'tmp/contract_conversion/header.png'
header_pdf = ROOT / 'tmp/contract_conversion/header_image_overlay.pdf'

img = Image.new('RGB', (1010, 96), 'white')
draw = ImageDraw.Draw(img)
font_path = '/System/Library/Fonts/Helvetica.ttc'
try:
    font = ImageFont.truetype(font_path, 15)
except OSError:
    font = ImageFont.load_default()
lines = ['Hoshi Landsberg GmbH', 'Max-Planck-Str. 2', '86899 Landsberg am Lech', 'Tel.: 08191-9635781']
for idx, line in enumerate(lines):
    box = draw.textbbox((0, 0), line, font=font)
    draw.text((995 - (box[2] - box[0]), 2 + idx * 19), line, fill='black', font=font)
draw.line((0, 92, 1000, 92), fill='black', width=2)
img.save(header_png)

hc = canvas.Canvas(str(header_pdf), pagesize=A4)
for _ in range(3):
    hc.drawImage(str(header_png), 45, 794, width=505, height=48, mask='auto')
    hc.showPage()
hc.save()

reader = PdfReader(str(base))
writer = PdfWriter()
writer.clone_document_from_reader(reader)
header_reader = PdfReader(str(header_pdf))
for i, page in enumerate(writer.pages):
    page.merge_page(header_reader.pages[i], over=True)

font = DictionaryObject({
    NameObject('/Type'): NameObject('/Font'),
    NameObject('/Subtype'): NameObject('/Type1'),
    NameObject('/BaseFont'): NameObject('/Helvetica'),
    NameObject('/Encoding'): NameObject('/WinAnsiEncoding'),
})
font_ref = writer._add_object(font)
field_refs = ArrayObject()

def add_text_field(page_index, name, tooltip, rect):
    x1, y1, x2, y2 = rect
    appearance = DecodedStreamObject()
    appearance.set_data(b'q Q')
    appearance.update({
        NameObject('/Type'): NameObject('/XObject'),
        NameObject('/Subtype'): NameObject('/Form'),
        NameObject('/BBox'): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(x2-x1), FloatObject(y2-y1)]),
        NameObject('/Resources'): DictionaryObject(),
    })
    appearance_ref = writer._add_object(appearance)
    widget = DictionaryObject({
        NameObject('/Type'): NameObject('/Annot'),
        NameObject('/Subtype'): NameObject('/Widget'),
        NameObject('/FT'): NameObject('/Tx'),
        NameObject('/T'): TextStringObject(name),
        NameObject('/TU'): TextStringObject(tooltip),
        NameObject('/Rect'): ArrayObject([FloatObject(x1), FloatObject(y1), FloatObject(x2), FloatObject(y2)]),
        NameObject('/V'): TextStringObject(''),
        NameObject('/DV'): TextStringObject(''),
        NameObject('/DA'): TextStringObject('/Helv 9 Tf 0 g'),
        NameObject('/F'): NumberObject(4),
        NameObject('/Ff'): NumberObject(0),
        NameObject('/Border'): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)]),
        NameObject('/AP'): DictionaryObject({NameObject('/N'): appearance_ref}),
    })
    widget_ref = writer._add_object(widget)
    page = writer.pages[page_index]
    annots = page.get('/Annots')
    if annots is None:
        annots = ArrayObject()
        page[NameObject('/Annots')] = annots
    annots.append(widget_ref)
    field_refs.append(widget_ref)

add_text_field(2, 'Vertragsdatum', 'Datum des Vertrags', (160, 508, 295, 526))
add_text_field(2, 'Unterschrift_Arbeitgeber', 'Name/Unterschrift Arbeitgeber', (53, 456, 198, 478))
add_text_field(2, 'Unterschrift_Arbeitnehmer', 'Name/Unterschrift Arbeitnehmer', (260, 456, 405, 478))

acroform = DictionaryObject({
    NameObject('/Fields'): field_refs,
    NameObject('/NeedAppearances'): BooleanObject(True),
    NameObject('/DA'): TextStringObject('/Helv 9 Tf 0 g'),
    NameObject('/DR'): DictionaryObject({
        NameObject('/Font'): DictionaryObject({NameObject('/Helv'): font_ref})
    }),
})
writer._root_object[NameObject('/AcroForm')] = writer._add_object(acroform)

with output.open('wb') as f:
    writer.write(f)

check = PdfReader(str(output))
fields = check.get_fields() or {}
expected = {'Vertragsdatum', 'Unterschrift_Arbeitgeber', 'Unterschrift_Arbeitnehmer'}
missing = expected.difference(fields)
if missing:
    raise RuntimeError(f'Missing form fields: {sorted(missing)}')
print(output)
print('Fields:', ', '.join(sorted(fields)))
