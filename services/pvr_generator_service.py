# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
def generate_pvr_pdf(report_id, product_name, template, criteria):
    """
    Generate PVR PDF from report data
    """
    # ...existing code for the function, including all table rendering and logic...
    pass
        f"predetermined acceptance criteria. The process is validated and qualified for "
        f"commercial production.",
        body_style
    ))

    # Signatures (AI-extracted)
    if hasattr(template, 'signatures') and template.signatures:
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("SIGNATURES", heading_style))
        sig_table_data = [['Role', 'Name', 'Date']]
        for role in ['performed_by', 'checked_by', 'approved_by']:
            name = template.signatures.get(role, '')
            date = template.signatures.get('date', '')
            sig_table_data.append([role.replace('_', ' ').title(), name, date])
        sig_table = Table(sig_table_data, colWidths=[2*inch, 2.5*inch, 2*inch])
        sig_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a5298')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(sig_table)

    # Build PDF
    doc.build(story)

    print(f"✅ PVR PDF generated: {filepath}")
    return filepath