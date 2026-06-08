from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import io
import csv
import json
import os
from datetime import datetime
from ...core.database import get_db
from ...models.contract import Contract
from ...models.company import Company
from ...models.institution import Institution
from ...core.config import settings

router = APIRouter(prefix="/export", tags=["Exportación"])


@router.get("/contracts/csv")
def export_contracts_csv(
    db: Session = Depends(get_db),
    institution_id: Optional[int] = None,
    monto_min: Optional[float] = None,
    limit: int = Query(5000, le=50000),
):
    q = db.query(Contract)
    if institution_id:
        q = q.filter(Contract.institution_id == institution_id)
    if monto_min:
        q = q.filter(Contract.monto_original >= monto_min)
    items = q.order_by(desc(Contract.monto_original)).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Número Contrato", "Institución ID", "Empresa ID",
        "Descripción", "Modalidad", "Estado", "Monto Original (DOP)",
        "Monto Actual (DOP)", "Fecha Firma", "Num Adendas",
        "Incremento %", "Financiado Préstamo", "Fuente",
    ])
    for c in items:
        writer.writerow([
            c.id, c.numero_contrato, c.institution_id, c.company_id,
            c.descripcion, c.modalidad, c.estado,
            c.monto_original, c.monto_actual or c.monto_original,
            c.fecha_firma.isoformat() if c.fecha_firma else "",
            c.num_adendas, c.incremento_porcentual,
            c.financiado_prestamo, c.fuente,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=contratos_{datetime.now().strftime('%Y%m%d')}.csv"},
    )


@router.get("/contracts/excel")
def export_contracts_excel(
    db: Session = Depends(get_db),
    institution_id: Optional[int] = None,
    monto_min: Optional[float] = None,
    limit: int = Query(5000, le=50000),
):
    try:
        import xlsxwriter
    except ImportError:
        from fastapi import HTTPException
        raise HTTPException(500, "xlsxwriter no instalado")

    q = db.query(Contract)
    if institution_id:
        q = q.filter(Contract.institution_id == institution_id)
    if monto_min:
        q = q.filter(Contract.monto_original >= monto_min)
    items = q.order_by(desc(Contract.monto_original)).limit(limit).all()

    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output)
    ws = wb.add_worksheet("Contratos")
    header_fmt = wb.add_format({"bold": True, "bg_color": "#1E3A5F", "font_color": "white"})
    money_fmt = wb.add_format({"num_format": "#,##0.00"})

    headers = ["ID", "Número", "Institución", "Empresa", "Descripción", "Modalidad",
               "Monto Original", "Monto Actual", "Adendas", "Incremento %", "Firma"]
    for col, h in enumerate(headers):
        ws.write(0, col, h, header_fmt)
        ws.set_column(col, col, 20)

    for row, c in enumerate(items, 1):
        ws.write(row, 0, c.id)
        ws.write(row, 1, c.numero_contrato)
        ws.write(row, 2, c.institution_id)
        ws.write(row, 3, c.company_id)
        ws.write(row, 4, c.descripcion or "")
        ws.write(row, 5, str(c.modalidad) if c.modalidad else "")
        ws.write(row, 6, c.monto_original, money_fmt)
        ws.write(row, 7, c.monto_actual or c.monto_original, money_fmt)
        ws.write(row, 8, c.num_adendas)
        ws.write(row, 9, c.incremento_porcentual)
        ws.write(row, 10, c.fecha_firma.isoformat() if c.fecha_firma else "")

    wb.close()
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=contratos_{datetime.now().strftime('%Y%m%d')}.xlsx"},
    )


@router.get("/report/institution/{institution_id}")
def export_institution_report(institution_id: int, db: Session = Depends(get_db)):
    """Genera informe PDF de una institución."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
    except ImportError:
        from fastapi import HTTPException
        raise HTTPException(500, "reportlab no instalado")

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        from fastapi import HTTPException
        raise HTTPException(404, "Institución no encontrada")

    contratos = db.query(Contract).filter(Contract.institution_id == institution_id)\
                  .order_by(desc(Contract.monto_original)).limit(20).all()

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Título
    title_style = ParagraphStyle("title", fontSize=18, fontName="Helvetica-Bold",
                                  textColor=HexColor("#1E3A5F"), spaceAfter=12)
    story.append(Paragraph(f"GovTracker RD — Informe Institucional", title_style))
    story.append(Paragraph(f"{inst.nombre}", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * inch))

    # Resumen
    story.append(Paragraph("Resumen Ejecutivo", styles["Heading3"]))
    summary_data = [
        ["Total Contratos", str(inst.total_contratos)],
        ["Monto Total Contratado", f"RD${inst.total_monto_contratos:,.0f}"],
        ["Tipo", str(inst.tipo)],
    ]
    t = Table(summary_data, colWidths=[2.5 * inch, 3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), HexColor("#F0F4F8")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3 * inch))

    # Top contratos
    story.append(Paragraph("Top 20 Contratos por Monto", styles["Heading3"]))
    tdata = [["#", "Número", "Monto (DOP)", "Empresa", "Modalidad"]]
    for i, c in enumerate(contratos, 1):
        tdata.append([
            str(i), c.numero_contrato or "S/N",
            f"RD${c.monto_original:,.0f}",
            str(c.company_id),
            str(c.modalidad) if c.modalidad else "—",
        ])
    ct = Table(tdata, colWidths=[0.3*inch, 1.5*inch, 1.5*inch, 2*inch, 1.5*inch])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), HexColor("#F8F9FA")]),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(ct)

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        f"Generado por GovTracker RD el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["Italic"],
    ))

    doc.build(story)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=informe_{inst.siglas or inst.id}.pdf"},
    )
