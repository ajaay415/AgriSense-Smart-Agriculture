"""Automated PDF Audit Report Generator for AgriSense Simulator.

Uses ReportLab to produce professional academic and technical project summaries,
including key statistics, threshold configurations, and cycle telemetry tables.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def make_pdf(
    username: str,
    df: pd.DataFrame,
    stats: Optional[Dict[str, Any]] = None,
    crop_info: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Generate a publication-grade PDF technical report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styling
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#124d35"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4a5568"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#124d35"),
        spaceBefore=8,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2d3748"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        alignment=TA_CENTER,
    )
    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.white,
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("🌿 AgriSense Smart Agriculture Report", title_style))
    story.append(
        Paragraph(
            "Embedded Systems Simulation & Automated Irrigation Monitoring System",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#124d35"), spaceBefore=2, spaceAfter=8))

    # Metadata & Session Summary
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_data = [
        [
            Paragraph(f"<b>Operator / Student:</b> {username}", meta_style),
            Paragraph(f"<b>Generated At:</b> {timestamp_str}", meta_style),
        ],
        [
            Paragraph("<b>System Type:</b> Software Simulation (Virtual ESP32 Target)", meta_style),
            Paragraph("<b>Target Architecture:</b> ESP32 SoC + Capacitive ADC & Relay", meta_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[90 * mm, 90 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    # Aggregate Statistics Overview
    if stats and stats.get("total_cycles", 0) > 0:
        story.append(Paragraph("📊 Simulation Summary & Key Metrics", section_heading))
        stats_data = [
            [
                "Total Cycles Logged",
                "Irrigation (Pump ON)",
                "Irrigation Duty Cycle",
                "Est. Water Consumed",
                "Avg Soil Moisture",
            ],
            [
                str(stats["total_cycles"]),
                str(stats["pump_on_cycles"]),
                f"{stats.get('irrigation_ratio', 0.0):.1f}%",
                f"{stats.get('total_water', 0.0):.1f} L",
                f"{stats.get('avg_moisture', 0.0):.1f}%",
            ],
        ]
        stats_table = Table(stats_data, colWidths=[36 * mm, 36 * mm, 36 * mm, 36 * mm, 36 * mm])
        stats_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2efe8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#124d35")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 1), (-1, 1), 9.5),
                ]
            )
        )
        story.append(stats_table)
        story.append(Spacer(1, 4 * mm))

    # Telemetry Log Table
    story.append(Paragraph("📋 Telemetry Log (Recent Cycles)", section_heading))
    if df is not None and not df.empty:
        # Use latest 35 records to keep report neat
        recent_df = df.tail(35).copy()

        headers = ["Timestamp", "Crop", "Soil %", "Temp °C", "Hum %", "Tank %", "Pump", "Safety / Status"]
        table_rows = [
            [Paragraph(h, table_header) for h in headers]
        ]

        for _, row in recent_df.iterrows():
            ts = str(row.get("created_at", ""))
            if len(ts) > 19:
                ts = ts[:19]
            crop = str(row.get("crop_type", "General"))[:12]
            soil = f"{float(row.get('soil_moisture', 0)):.1f}%"
            temp = f"{float(row.get('temperature', 0)):.1f}"
            hum = f"{float(row.get('humidity', 0)):.1f}"
            tank = f"{float(row.get('tank_level', 0)):.1f}%"
            pump = "ON" if row.get("pump_state") else "OFF"
            msg = str(row.get("message", "OK"))
            short_msg = "SAFETY LOCK" if "SAFETY" in msg else ("IRRIGATING" if pump == "ON" else "IDLE")

            table_rows.append(
                [
                    Paragraph(ts, table_cell),
                    Paragraph(crop, table_cell),
                    Paragraph(soil, table_cell),
                    Paragraph(temp, table_cell),
                    Paragraph(hum, table_cell),
                    Paragraph(tank, table_cell),
                    Paragraph(f"<b>{pump}</b>", table_cell),
                    Paragraph(short_msg, table_cell),
                ]
            )

        col_widths = [32 * mm, 24 * mm, 18 * mm, 16 * mm, 16 * mm, 18 * mm, 16 * mm, 40 * mm]
        log_table = Table(table_rows, repeatRows=1, colWidths=col_widths)
        log_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b5e3f")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#a0aec0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ]
            )
        )
        story.append(log_table)
    else:
        story.append(Paragraph("<i>No telemetry records captured yet. Execute simulation cycles to populate audit log.</i>", meta_style))

    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#a0aec0"), spaceBefore=4, spaceAfter=4))
    disclaimer = (
        "<b>Academic Disclaimer:</b> This document was generated automatically by the AgriSense Software Simulator. "
        "All telemetry metrics are produced via virtual sensor models and computational control logic without physical hardware actuation."
    )
    story.append(Paragraph(disclaimer, ParagraphStyle("Disc", parent=styles["Normal"], fontSize=7, leading=9, textColor=colors.HexColor("#718096"), alignment=TA_CENTER)))

    doc.build(story)
    return buffer.getvalue()
