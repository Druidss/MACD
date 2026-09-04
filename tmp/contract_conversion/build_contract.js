const {
  Document, Packer, Paragraph, TextRun, AlignmentType, PageBreak, Header,
  TabStopType, TabStopPosition, BorderStyle, PageOrientation
} = require('/Users/adrian/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/docx');
const fs = require('fs');

const OUT = '/Users/adrian/Desktop/BA/MACD/output/contract';
fs.mkdirSync(OUT, { recursive: true });

const FONT = 'Arial';
const SIZE = 20; // 10 pt

function p(text = '', opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    pageBreakBefore: !!opts.pageBreakBefore,
    indent: { left: opts.left || 0, firstLine: opts.firstLine || 0, hanging: opts.hanging || 0 },
    spacing: {
      before: opts.before || 0,
      after: opts.after ?? 100,
      line: opts.line || 252,
      lineRule: 'auto'
    },
    border: opts.bottomBorder ? { bottom: { style: BorderStyle.SINGLE, size: 10, color: '000000', space: 1 } } : undefined,
    tabStops: opts.tabs || [],
    children: [new TextRun({
      text,
      font: FONT,
      size: opts.size || SIZE,
      bold: !!opts.bold,
      underline: opts.underline ? {} : undefined
    })]
  });
}

function sectionHeading(text, opts = {}) {
  return p(text, { bold: true, pageBreakBefore: !!opts.pageBreakBefore, left: opts.left ?? 520, before: opts.before ?? 110, after: opts.after ?? 90, size: 20 });
}

function clause(text, opts = {}) {
  return p(text, {
    left: opts.left ?? 1040,
    firstLine: opts.firstLine ?? 0,
    before: opts.before ?? 0,
    after: opts.after ?? 100,
    line: opts.line ?? 252,
    size: opts.size ?? 20,
    align: opts.align
  });
}

function companyHeader() {
  const lines = ['Hoshi Landsberg GmbH', 'Max-Planck-Str. 2', '86899 Landsberg am Lech', 'Tel.: 08191-9635781'];
  return new Header({ children: lines.map((text, index) => new Paragraph({
    alignment: AlignmentType.RIGHT,
    spacing: { before: 0, after: 0, line: 170, lineRule: 'exact' },
    border: index === lines.length - 1 ? { bottom: { style: BorderStyle.SINGLE, size: 6, color: '000000', space: 2 } } : undefined,
    children: [new TextRun({ text, font: FONT, size: 15 })]
  })) });
}

const children = [];

// Page 1
children.push(p('Arbeitsvertrag', { align: AlignmentType.CENTER, bold: true, underline: true, size: 28, before: 300, after: 520 }));
children.push(p('Vertragsparteien', { bold: true, before: 0, after: 230 }));
children.push(p('Arbeitgeber', { after: 210 }));
children.push(clause('Shaocao Hu\nHoshi Landsberg GmbH\nMax-Planck-Str. 2\n86899 Landsberg am Lech', { left: 900, line: 225, after: 230 }));
children.push(p('Arbeitnehmer', { after: 200 }));
children.push(clause('Bai Shaodong\nGeb. 08.01.1992\nNr. 77-1, Paozi Road, Paozi Village,\nHailin Town, Hailin City,\nHeilongjiang Province, P.R. China', { left: 900, line: 225, after: 300 }));
children.push(p('wird folgender Rahmenarbeitsvertrag für kurzfristig Beschäftigte geschlossen:', { after: 170 }));
children.push(sectionHeading('1.   Arbeitsverhältnisse'));
children.push(clause('Das Arbeitsverhältnis ist befristet für die zeit vom 01.11.2026 bis 30.06.2027', { after: 100 }));
children.push(sectionHeading('2.   Tätigkeit'));
children.push(clause('Der Arbeitnehmer wird als Küchenhilfe eingestellt.', { after: 100 }));
children.push(sectionHeading('3.   Arbeitszeit'));
children.push(clause('3.1 Die regelmäßige Arbeitszeit beträgt 33 Stunden wöchentlich.', { after: 90 }));
children.push(clause('3.2 Der Arbeitnehmer arbeitet wöchentlich an sechs Arbeitstagen.', { after: 90 }));
children.push(sectionHeading('4.   Vergütung / Sonstige Leistungen'));
children.push(clause('4.1 Der Stundenlohn beträgt Euro 14,00 brutto.', { after: 90 }));
children.push(clause('4.2 Die Zahlung des Gehaltes/ Lohns ist an dritten Tag des folgenden Monats fällig. Sie erfolgt\n     per Überweisung: der Arbeitnehmer hat ein Konto dafür zu errichten.', { after: 90 }));
children.push(clause('4.3 Die Zahlung von Gratifikationen, Tantiemen, Prämien und sonstigen Leistungen liegt im\n     freien Ermessen des Arbeitgebers und begründet keinen Rechtsanspruch, auch wenn die\n     Zahlung wiederholt ohne ausdrücklichen Vorbehalt der Freiwilligkeit erfolgte.', { after: 0 }));

// Page 2
const page1End = children.length;
children.push(sectionHeading('5.   Probezeit', { left: 520, before: 0, after: 90 }));
children.push(clause('5.1  Die ersten sechs Monate gelten als Probezeit. Während der Probezeit kann das\n       Arbeitsverhältnis arbeitgeberseitig mit einer Frist von zwei Wochen gekündigt werden.\n       Dieser Vertag wird auf die Dauer von sechs Monaten vom 01.10.2026 bis zum 31.03.2027\n       zur Probe abgeschlossen.', { after: 90 }));
children.push(sectionHeading('6.   Arbeitsverhinderung und Vergütungsfortzahlung im Krankheitsfall'));
children.push(clause('6.1 Der Arbeitnehmer ist verpflichtet, jede Arbeitsverhinderung und ihre voraussichtliche\n     Dauer unverzüglich dem Arbeitgeber mitzuteilen.', { after: 90 }));
children.push(clause('6.2 Im Falle der Arbeitsunfähigkeit von mehr als drei Kalendertagen infolge Krankheit ist der\n     Arbeitnehmer verpflichtet, vor Ablauf des darauffolgenden Arbeitstages eine ärztliche\n     Bescheinigung über die Arbeitsunfähigkeit sowie über deren voraussichtliche Dauer\n     vorzulegen. Bei über den angegebenen Zeitraum hinausgehender Erkrankung ist eine\n     Folgebescheinigung innerhalb weiterer drei Tage seit Ablauf der vorangehenden\n     einzureichen.', { after: 70 }));
children.push(p('Zu §6 Arbeitsverhinderung und Vergütungsfortzahlung im Krankheitsfall', { bold: true, left: 1040, after: 70 }));
children.push(clause('6.3   Ist der Arbeitnehmer an der Arbeitsleistung infolge auf unverschuldeter Krankheit\n        beruhender Arbeitsunfähigkeit verhindert, so leistet der Arbeitgeber\n        Vergütungsfortzahlung nach den Bestimmungen des Entgeltfortzahlungsgesetzes.', { after: 70 }));
children.push(sectionHeading('7.   Urlaub'));
children.push(clause('Der Arbeitnehmer erhält kalenderjährlich Urlaub in Höhe von 21 Werktagen. Der Urlaub hat\nwährend der Betriebsferien bzw. nach Absprache mit dem Arbeitgeber zu erfolgen.', { left: 520, after: 80 }));
children.push(sectionHeading('8.   Nebenbeschäftigung'));
children.push(clause('Während der Dauer des Arbeitsverhältnisses ist jede auf Erwerb gerichtete und das\nArbeitsverhältnis beeinträchtigende Nebenbeschäftigung nur mit Zustimmung des\nArbeitgebers zulässig.', { left: 520, align: AlignmentType.JUSTIFIED, after: 80 }));
children.push(sectionHeading('9.   Beendigung des Arbeitsverhältnisses'));
children.push(clause('9.1 Das Arbeitsverhältnis kann mit einer Kündigungsfrist von 4 Wochen\n     zum Fünfzehnten oder zum Ende eines Kalendermonats gekündigt werden.\n9.2 Die Kündigung muss schriftlich erfolgen.', { after: 160 }));
children.push(sectionHeading('10. Verschwiegenheitsverpflichtung'));
children.push(clause('10.1Der Arbeitnehmer verpflichtet sich, über alle ihm während seiner Tätigkeit\n      bekanntwerdenden Geschäfts- und Betriebsgeheimnisse, alle ihm bekannt gewordenen\n      Herstellungsverfahren und sonstigen geschäftlichen bzw. betrieblichen Tatsachen auch nach', { after: 0, align: AlignmentType.JUSTIFIED }));

// Page 3
const page2End = children.length;
children.push(p('Beendigung des Arbeitsverhältnisses stillschweigend zu bewahren.', { after: 760 }));
children.push(clause('10.2  Der Arbeitnehmer ist während der Dauer des Arbeitsverhältnisses auch verpflichtet über\n         den Inhalt dieses Vertrages Stillschweigen zu bewahren.', { after: 230 }));
children.push(sectionHeading('11. Nebenabreden und Vertragsänderungen', { left: 520, after: 180 }));
children.push(clause('Mündliche Nebenabreden bestehen nicht. Änderungen und Ergänzungen dieses Vertrages\nbedürfen zu ihrer Wirksamkeit der Schriftform.', { left: 520, align: AlignmentType.JUSTIFIED, after: 220 }));
children.push(sectionHeading('12. Teilnichtigkeit / Vertragsaushändigung', { left: 520, after: 180 }));
children.push(clause('12.1   Sind einzelne Bestimmungen dieses Vertrages unwirksam, so berührt dieses nicht die\n          Wirksamkeit der übrigen Regelungen des Vertrages.', { after: 180 }));
children.push(clause('12.2   Die Vertragsparteien bekennen, eine schriftliche Ausfertigung dieses Vertrages erhalten\n          zu haben.', { after: 1250 }));
children.push(p('Landsberg am Lech, den ..............................................', { after: 650 }));
children.push(p('......................................................                         ...................................................', { after: 0 }));
children.push(p('Geschäftsführer Hu Shaocao                     Mitarbeiter', { after: 0 }));

function makeSection(sectionChildren) {
  return {
    properties: {
      page: {
        size: { width: 11906, height: 16838, orientation: PageOrientation.PORTRAIT },
        margin: { top: 1150, right: 1130, bottom: 650, left: 1130, header: 260, footer: 0 }
      }
    },
    headers: { default: companyHeader() },
    children: sectionChildren
  };
}

const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: FONT, size: SIZE },
        paragraph: { spacing: { before: 0, after: 100, line: 252 } }
      }
    }
  },
  sections: [
    makeSection(children.slice(0, page1End)),
    makeSection(children.slice(page1End, page2End)),
    makeSection(children.slice(page2End))
  ]
});

Packer.toBuffer(doc).then(buf => {
  const file = `${OUT}/Arbeitsvertrag_Bai_Shaodong_editierbar.docx`;
  fs.writeFileSync(file, buf);
  process.stdout.write(file + '\n');
});
