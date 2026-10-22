"""Bounded tabular exports. Callers own filtering and authorization."""

import csv
from io import BytesIO, StringIO
from typing import Iterable, Sequence

from fastapi import HTTPException
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas


def safe_text(value: object) -> str:
    text = "" if value is None else str(value)
    if isinstance(value, str) and text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def safe_data_value(value: object) -> object:
    """Neutralize untrusted text while preserving native non-text values."""
    return safe_text(value) if isinstance(value, str) or value is None else value


def render_export(
    columns: Sequence[str],
    rows: Iterable[Sequence[object]],
    fmt: str,
    filename: str,
    title: str,
) -> Response:
    rows = list(rows)
    if fmt == "csv":
        stream = StringIO(newline="")
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(columns)
        writer.writerows([[safe_data_value(value) for value in row] for row in rows])
        content = ("\ufeff" + stream.getvalue()).encode("utf-8")
        media_type = "text/csv; charset=utf-8"
    elif fmt == "xlsx":
        stream = BytesIO()
        book = Workbook(write_only=True)
        sheet = book.create_sheet("Datos")
        sheet.append(list(columns))
        for row in rows:
            cells = []
            for value in row:
                safe_value = safe_data_value(value)
                cell = WriteOnlyCell(sheet, value=safe_value)
                if isinstance(safe_value, str):
                    cell.data_type = "s"
                cells.append(cell)
            sheet.append(cells)
        book.save(stream)
        content = stream.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt == "pdf":
        stream = BytesIO()
        pdf = canvas.Canvas(stream, pagesize=landscape(A4))
        width, height = landscape(A4)
        y = height - 40
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(36, y, title[:100])
        y -= 24
        pdf.setFont("Helvetica", 7)
        for row in (columns, *rows):
            if y < 35:
                pdf.showPage()
                pdf.setFont("Helvetica", 7)
                y = height - 40
            line = " | ".join(safe_text(value)[:45] for value in row)
            pdf.drawString(36, y, line[:190])
            y -= 11
        pdf.save()
        content = stream.getvalue()
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=422, detail="Formato de exportación inválido")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{fmt}"'},
    )
