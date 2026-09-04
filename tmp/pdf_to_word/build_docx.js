const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, VerticalAlign, WidthType, HeightRule, BorderStyle,
  PageOrientation, Footer, PageNumber, TabStopType, TabStopPosition,
  convertMillimetersToTwip
} = require('/Users/adrian/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/docx');
const fs = require('fs');

const outDir = '/Users/adrian/Desktop/BA/MACD/output/word';
fs.mkdirSync(outDir, { recursive: true });
const outPath = `${outDir}/Zeitnachweis_08_2026.docx`;

const A4_W = 11906;
const A4_H = 16838;
const margin = 560;
const usable = A4_W - 2 * margin;
const black = { style: BorderStyle.SINGLE, size: 12, color: '000000' };
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };

function cell(text, width, opts = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 40, bottom: 25, left: 55, right: 55 },
    borders: opts.borders || { top: black, bottom: black, left: black, right: black },
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      spacing: { before: 0, after: 0, line: 180, lineRule: 'exact' },
      children: [new TextRun({ text, font: 'Arial', size: opts.size || 18, bold: !!opts.bold })]
    })]
  });
}

function fixedTable(rows, widths) {
  return new Table({
    width: { size: usable, type: WidthType.DXA },
    columnWidths: widths,
    layout: 'fixed',
    margins: { top: 0, bottom: 0, left: 0, right: 0 },
    rows
  });
}

const top = new Table({
  width: { size: 5000, type: WidthType.DXA },
  columnWidths: [1500, 3500],
  layout: 'fixed',
  alignment: AlignmentType.CENTER,
  borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none },
  rows: [new TableRow({ height: { value: 420, rule: HeightRule.EXACT }, children: [
    cell('Firma:', 1500, { align: AlignmentType.RIGHT, size: 20, borders: { top: none, bottom: none, left: none, right: none } }),
    cell('', 3500, { borders: { top: none, bottom: black, left: none, right: none } })
  ]})]
});

const titleWidths = [Math.round(usable / 2), usable - Math.round(usable / 2)];
const titleTable = fixedTable([
  new TableRow({ height: { value: 300, rule: HeightRule.EXACT }, children: [
    cell('Stundenzettel August 2026', titleWidths[0], { align: AlignmentType.CENTER, size: 17 }),
    cell('vom 01.08.2026 bis 31.08.2026', titleWidths[1], { align: AlignmentType.CENTER, size: 17 })
  ]})
], titleWidths);

const widths = [572, 1995, 1985, 1985, 1985, 2264];
const headers = ['Tag', 'Datum', 'Beginn', 'Ende', 'Pause', 'Arbeitszeit (abzgl. Pause)'];
const weekdays = ['Sa','So','Mo','Di','Mi','Do','Fr','Sa','So','Mo','Di','Mi','Do','Fr','Sa','So','Mo','Di','Mi','Do','Fr','Sa','So','Mo','Di','Mi','Do','Fr','Sa','So','Mo'];
const rows = [new TableRow({
  tableHeader: true,
  height: { value: 370, rule: HeightRule.EXACT },
  children: headers.map((h, i) => cell(h, widths[i], { align: AlignmentType.CENTER, size: i === 5 ? 16 : 18 }))
})];

for (let day = 1; day <= 31; day++) {
  const dd = String(day).padStart(2, '0');
  const vals = [weekdays[day - 1], `${dd}.08.2026`, '', '', '', ''];
  rows.push(new TableRow({
    height: { value: 352, rule: HeightRule.EXACT },
    children: vals.map((v, i) => cell(v, widths[i], {
      align: i === 0 ? AlignmentType.CENTER : AlignmentType.LEFT,
      size: 18
    }))
  }));
}
const mainTable = fixedTable(rows, widths);

const bottomWidths = [6800, 1722, 2264];
const bottomTable = new Table({
  width: { size: usable, type: WidthType.DXA },
  columnWidths: bottomWidths,
  layout: 'fixed',
  rows: [new TableRow({ height: { value: 400, rule: HeightRule.EXACT }, children: [
    cell('Vorlage von Arbeitszeiterfassung.com', bottomWidths[0], { size: 16, borders: { top: none, bottom: none, left: none, right: none } }),
    cell('Summe:', bottomWidths[1], { align: AlignmentType.CENTER, size: 17, borders: { top: none, bottom: none, left: none, right: none } }),
    cell('', bottomWidths[2], { borders: { top: black, bottom: black, left: black, right: black } })
  ]})]
});

const doc = new Document({
  styles: {
    default: { document: { run: { font: 'Arial', size: 18 }, paragraph: { spacing: { before: 0, after: 0 } } } }
  },
  sections: [{
    properties: {
      page: {
        size: { width: A4_W, height: A4_H, orientation: PageOrientation.PORTRAIT },
        margin: { top: 500, right: margin, bottom: 430, left: margin, header: 0, footer: 120 }
      }
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 0 },
        children: [new TextRun({ text: 'Seite ', font: 'Arial', size: 14 }), new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 14 }), new TextRun({ text: '/1', font: 'Arial', size: 14 })]
      })] })
    },
    children: [
      new Paragraph({ spacing: { before: 0, after: 120 }, children: [] }),
      top,
      new Paragraph({ spacing: { before: 0, after: 180 }, children: [] }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 50, line: 430, lineRule: 'exact' },
        children: [new TextRun({ text: 'Name:__________________', font: 'Arial', size: 40 })]
      }),
      titleTable,
      new Paragraph({ spacing: { before: 0, after: 190 }, children: [] }),
      mainTable,
      bottomTable
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  process.stdout.write(outPath + '\n');
});
