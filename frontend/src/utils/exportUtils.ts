import * as XLSX from 'xlsx';

/**
 * Descarga un array de objetos como archivo CSV (UTF-8 con BOM para Excel).
 */
export function exportToCSV(data: Record<string, unknown>[], filename: string): void {
  if (!data.length) return;

  const headers = Object.keys(data[0]);
  const csvRows = [
    headers.join(';'),
    ...data.map((row) =>
      headers
        .map((h) => {
          const val = row[h] ?? '';
          const str = String(val).replace(/"/g, '""');
          return `"${str}"`;
        })
        .join(';')
    ),
  ];

  // UTF-8 BOM so Excel opens it correctly
  const bom = '\uFEFF';
  const blob = new Blob([bom + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  triggerDownload(blob, `${filename}.csv`);
}

/**
 * Descarga un array de objetos como archivo Excel (.xlsx).
 */
export function exportToExcel(data: Record<string, unknown>[], filename: string): void {
  if (!data.length) return;

  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Datos');

  // Auto-width columns
  const cols = Object.keys(data[0]).map((key) => ({
    wch: Math.max(key.length, ...data.map((r) => String(r[key] ?? '').length)) + 2,
  }));
  worksheet['!cols'] = cols;

  XLSX.writeFile(workbook, `${filename}.xlsx`);
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── PDF ─────────────────────────────────────────────────────────────────────

type PDFOptions = {
  title: string;
  subtitle?: string;
  filename: string;
  columns: { header: string; dataKey: string }[];
  data: Record<string, unknown>[];
};

export async function exportToPDF(opts: PDFOptions): Promise<void> {
  if (!opts.data.length) return;

  // Dynamic import to keep initial bundle small
  const { default: jsPDF } = await import('jspdf');
  const { default: autoTable } = await import('jspdf-autotable');

  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const now = new Date().toLocaleString('es-CO');

  // ── Header bar ────────────────────────────────────────────────────────────
  doc.setFillColor(67, 56, 202); // indigo-700
  doc.rect(0, 0, pageW, 22, 'F');

  // Platform name (left)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(255, 255, 255);
  doc.text('PLATAFORMA DETECCIÓN TEMPRANA DE CORRUPCIÓN', 10, 9);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.text('Datos Abiertos Públicos de Colombia', 10, 15);

  // Date (right)
  doc.setFontSize(8);
  doc.text(`Generado: ${now}`, pageW - 10, 9, { align: 'right' });
  doc.text(`Registros: ${opts.data.length.toLocaleString()}`, pageW - 10, 15, { align: 'right' });

  // ── Title ─────────────────────────────────────────────────────────────────
  doc.setTextColor(30, 27, 75); // indigo-950
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.text(opts.title, 10, 33);

  if (opts.subtitle) {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139); // slate-500
    doc.text(opts.subtitle, 10, 40);
  }

  // ── Table ─────────────────────────────────────────────────────────────────
  const rows = opts.data.map((row) =>
    opts.columns.map((col) => {
      const val = row[col.dataKey];
      return val != null ? String(val) : '';
    })
  );

  autoTable(doc, {
    startY: opts.subtitle ? 46 : 40,
    head: [opts.columns.map((c) => c.header)],
    body: rows,
    styles: {
      fontSize: 7.5,
      cellPadding: 2.5,
      overflow: 'linebreak',
    },
    headStyles: {
      fillColor: [67, 56, 202],
      textColor: 255,
      fontStyle: 'bold',
      halign: 'left',
    },
    alternateRowStyles: { fillColor: [241, 245, 249] }, // slate-100
    tableLineColor: [226, 232, 240], // slate-200
    tableLineWidth: 0.2,
    didDrawPage: (data) => {
      // Footer on every page
      const pg = doc.getCurrentPageInfo().pageNumber;
      const total = (doc as any).internal.getNumberOfPages();
      doc.setFontSize(7);
      doc.setTextColor(148, 163, 184); // slate-400
      doc.text(
        `Página ${pg} de ${total}  |  Plataforma Detección Temprana de Corrupción`,
        pageW / 2,
        pageH - 4,
        { align: 'center' }
      );
    },
  });

  doc.save(`${opts.filename}.pdf`);
}

