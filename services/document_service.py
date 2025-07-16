import os
import logging
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    ListFlowable, ListItem, PageTemplate, Frame
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# ========== Header and Footer ==========
def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4

    # Header
    canvas.setFont('Helvetica-Bold', 10)
    canvas.setFillColor(colors.HexColor("#2E86AB"))
    canvas.drawString(72, height - 40, "SIRA - Rapport d'Évaluation Professionnelle")

    # Footer
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.gray)
    canvas.drawString(72, 30, f"Page {doc.page}")
    canvas.drawRightString(width - 72, 30, datetime.now().strftime('%d %B %Y'))

    canvas.restoreState()

# ========== Helper: Markdown Renderer ==========
def replace_markdown(text):
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    return text

# ========== Main PDF Function ==========
def generate_assessment_report(cv_analysis: dict, qa_pairs: list, summary: str, output_path: str) -> bool:
    try:
        logging.info(f"Starting PDF generation: {output_path}")

        # Document template with header/footer
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)

        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 20, id='normal')
        template = PageTemplate(id='template', frames=frame, onPage=header_footer)
        doc.addPageTemplates([template])

        # Styles
        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#2E86AB")

        title_style = ParagraphStyle(
            'TitleStyle',
            fontSize=22,
            leading=28,
            textColor=primary_color,
            alignment=TA_CENTER,
            spaceAfter=20
        )

        heading_style = ParagraphStyle(
            'HeadingStyle',
            fontSize=14,
            textColor=primary_color,
            spaceBefore=12,
            spaceAfter=8,
            leading=18
        )

        subheading_style = ParagraphStyle(
            'SubHeading',
            fontSize=12,
            textColor=primary_color,
            spaceBefore=6,
            spaceAfter=6,
            leading=16
        )

        body_style = ParagraphStyle(
            'BodyStyle',
            fontSize=10.5,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=8
        )

        story = []

        # ========== Title ==========
        story.append(Paragraph("Rapport d'Évaluation Professionnelle", title_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Généré le : {datetime.now().strftime('%d %B %Y')}", body_style))
        story.append(Spacer(1, 24))

        # ========== CV Analysis ==========
        story.append(Paragraph("Aperçu de l'Analyse du CV", heading_style))

        if cv_analysis.get('summary'):
            story.append(Paragraph(f"<b>Résumé Professionnel :</b> {cv_analysis['summary']}", body_style))

        if cv_analysis.get('career_stage'):
            story.append(Paragraph(f"<b>Niveau de Carrière :</b> {cv_analysis['career_stage']}", body_style))

        if cv_analysis.get('experience_years'):
            story.append(Paragraph(f"<b>Années d'Expérience :</b> {cv_analysis['experience_years']}", body_style))

        if cv_analysis.get('key_skills') and isinstance(cv_analysis['key_skills'], list):
            skills = ", ".join(cv_analysis['key_skills'][:10])
            story.append(Paragraph(f"<b>Compétences Clés :</b> {skills}", body_style))

        story.append(Spacer(1, 20))

        # ========== Summary Parser ==========
        if summary:
            story.append(Paragraph("Synthèse de l'Évaluation Professionnelle", heading_style))
            lines = summary.strip().split('\n')
            bullet_buffer = []

            def flush_bullets():
                if bullet_buffer:
                    items = [ListItem(Paragraph(replace_markdown(line.strip('* ')), body_style)) for line in bullet_buffer]
                    story.append(ListFlowable(items, bulletType='bullet', leftIndent=18))
                    bullet_buffer.clear()

            for line in lines:
                clean = line.strip()
                if not clean:
                    flush_bullets()
                    continue

                if clean.startswith("###"):
                    flush_bullets()
                    story.append(Paragraph(replace_markdown(clean[3:].strip()), subheading_style))
                elif clean.startswith("##"):
                    flush_bullets()
                    story.append(Spacer(1, 10))
                    story.append(Paragraph(replace_markdown(clean[2:].strip()), heading_style))
                elif clean.startswith("* "):
                    bullet_buffer.append(clean)
                elif clean.startswith("---"):
                    continue
                else:
                    flush_bullets()
                    story.append(Paragraph(replace_markdown(clean), body_style))

            flush_bullets()
            story.append(Spacer(1, 20))

        # ========== Q&A Section ==========
        story.append(Paragraph("Questions et Réponses d'Entretien", heading_style))

        for i, qa in enumerate(qa_pairs, 1):
            question = qa.get("question", "")
            answer = qa.get("answer", "")
            story.append(Paragraph(f"<b>Question {i}:</b> {replace_markdown(question)}", body_style))
            story.append(Paragraph(f"<b>Réponse:</b> {replace_markdown(answer)}", body_style))
            story.append(Spacer(1, 12))

        # ========== Build PDF ==========
        doc.build(story)
        logging.info("PDF successfully generated.")
        return True

    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        return False


# ========== Filename Generator ==========
def create_report_filename(session_id: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"assessment_report_{session_id}_{timestamp}.pdf"
