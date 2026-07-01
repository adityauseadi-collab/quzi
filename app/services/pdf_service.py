import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_result_pdf(result):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    story = []

    # Colors
    primary = colors.HexColor('#6366f1')
    success = colors.HexColor('#22c55e')
    danger = colors.HexColor('#ef4444')
    dark = colors.HexColor('#1e293b')
    light_gray = colors.HexColor('#f8fafc')

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                 fontSize=24, textColor=primary,
                                 spaceAfter=6, alignment=TA_CENTER)
    story.append(Paragraph('QuizMaster Pro', title_style))

    sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                               fontSize=12, textColor=dark,
                               spaceAfter=20, alignment=TA_CENTER)
    story.append(Paragraph('Quiz Result Report', sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=primary))
    story.append(Spacer(1, 0.5*cm))

    # Student Info
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=11, spaceAfter=4)
    story.append(Paragraph(f'<b>Student:</b> {result.student.full_name or result.student.username}', info_style))
    story.append(Paragraph(f'<b>Quiz:</b> {result.quiz.title}', info_style))
    story.append(Paragraph(f'<b>Date:</b> {result.submitted_at.strftime("%B %d, %Y at %I:%M %p")}', info_style))
    if result.time_taken:
        mins, secs = divmod(result.time_taken, 60)
        story.append(Paragraph(f'<b>Time Taken:</b> {mins}m {secs}s', info_style))
    story.append(Spacer(1, 0.5*cm))

    # Score Summary Table
    grade_color = success if result.percentage >= 50 else danger
    summary_data = [
        ['Metric', 'Value'],
        ['Total Questions', str(result.total_questions)],
        ['Correct Answers', str(result.correct_answers)],
        ['Wrong Answers', str(result.wrong_answers)],
        ['Marks Obtained', f'{result.marks_obtained}/{result.total_questions}'],
        ['Percentage', f'{result.percentage:.1f}%'],
        ['Grade', result.grade],
    ]
    summary_table = Table(summary_data, colWidths=[8*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [light_gray, colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, -1), (1, -1), grade_color),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.8*cm))

    # Answer Review
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1, 0.3*cm))
    section_style = ParagraphStyle('Section', parent=styles['Heading2'],
                                   textColor=primary, spaceAfter=10)
    story.append(Paragraph('Answer Review', section_style))

    answers = result.answers.all()
    q_style = ParagraphStyle('Q', parent=styles['Normal'], fontSize=10, spaceAfter=2)
    ans_style = ParagraphStyle('Ans', parent=styles['Normal'], fontSize=10, leftIndent=20, spaceAfter=8)

    for i, sa in enumerate(answers, 1):
        q = sa.question
        icon = '✓' if sa.is_correct else '✗'
        q_color = '#22c55e' if sa.is_correct else '#ef4444'
        story.append(Paragraph(
            f'<font color="{q_color}"><b>{icon}</b></font> <b>Q{i}.</b> {q.question_text}', q_style
        ))
        your_ans = q.get_options().get(sa.selected_answer, 'Not answered') if sa.selected_answer else 'Not answered'
        correct_ans = q.get_correct_option_text()
        story.append(Paragraph(f'Your Answer: <b>{sa.selected_answer or "—"}</b>. {your_ans}', ans_style))
        if not sa.is_correct:
            story.append(Paragraph(
                f'<font color="#22c55e">Correct Answer: <b>{q.correct_answer}</b>. {correct_ans}</font>', ans_style
            ))

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
                                  fontSize=9, textColor=colors.gray,
                                  alignment=TA_CENTER, spaceBefore=8)
    story.append(Paragraph(f'Generated by QuizMaster Pro • {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}', footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
