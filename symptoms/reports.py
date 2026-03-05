import io
from datetime import date, timedelta
from django.db.models import Avg, Count

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph,Spacer,Table,TableStyle,HRFlowable
    )
from reportlab.lib.enums import TA_CENTER,TA_LEFT,TA_RIGHT


#----Colour palette (matches meditrack theme)

BLUE=colors.HexColor('#2563EB')
CYAN=colors.HexColor('#0891B2')
LIGHT_BLUE=colors.HexColor('#EFF6FF')
SLATE_900=colors.HexColor('#0F172A')
SLATE_600=colors.HexColor('#475569')
SLATE_200=colors.HexColor('#E2E8F0')
WHITE=colors.white

SEV_GREEN=colors.HexColor('#DCFCE7')
SEV_YELLOW=colors.HexColor('#FEF9C3')
SEV_RED=colors.HexColor('#FEE2E2')
SEV_GREEN_TEXT=colors.HexColor('#166534')
SEV_YELLOW_TEXT=colors.HexColor('#854D0E')
SEV_RED_TEXT=colors.HexColor('#991B1B')

MOOD_LABELS={
    1:'Very Bad',
    2:'Bad',
    3:'Okay',
    4:'Good',
    5:'Very Good'
}

def _severity_colors(severity):
    """Return(background, text) colors for a severity value."""
    if severity<=3:
        return SEV_GREEN,SEV_GREEN_TEXT
    if severity<=6:
        return SEV_YELLOW,SEV_YELLOW_TEXT
    return SEV_RED,SEV_RED_TEXT

def _build_styles():
    base=getSampleStyleSheet()
    title_style=ParagraphStyle(
        'ReportTitle',
        parent=base['Title'],
        fontSize=26,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle_style=ParagraphStyle(
        'ReportSubtitle',
        fontSize=11,
        textColor=colors.HexColor('#BFDBFE'),
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    section_header=ParagraphStyle(
        'SectionHeader',
        parent=base['Heading2'],
        fontSize=13,
        textColor=BLUE,
        spaceBefore=18,
        spaceAfter=6,
        borderPad=0,
    )
    body=ParagraphStyle(
        'Body',
        parent=base['Normal'],
        fontSize=10,
        textColor=SLATE_600,
        spaceAfter=4,
    )
    small =ParagraphStyle(
        'Small',
        parent=base['Normal'],
        fontSize=8,
        textColor=SLATE_600,
        alignment=TA_CENTER,
    )
    disclaimer=ParagraphStyle(
        'Disclaimer',
        fontSize=8,
        textColor=colors.HexColor('#92400E'),
        backColor=colors.HexColor('#F59E0B'),
        borderWidth=1,
        borderPad=6,
        spaceAfter=6,
        spaceBefore=6,
    )
    return {
        'title':title_style,
        'subtitle':subtitle_style,
        'section':section_header,
        'body':body,
        'small':small,
        'disclaimer':disclaimer,
        'base':base,
    }

#------Section builders


def _header_block(user,start_date,end_date,styles):
    """Blue gradient header"""
    header_data=[[
        Paragraph(f'<b>MediTrack</b>',styles['title'],)
    ]]
    sub_data=[[
        Paragraph(
            f'Health Report &nbsp; {start_date.strftime("%B %d,%Y")}'
            f'{end_date.strftime("%B,%d,%Y")}',
            styles['subtitle']
        ),
    ]]
    user_data=[[
        Paragraph(
            f'<font color=#BFDBFE>Patient:</font> '
            f'<font color="white"><b>{user.get_full_name() or user.username}</b></font>'
            f'&nbsp;%nbsp;%nbsp;'
            f'<font color ="#BFDBFE">Generated:</font> '
            f'<font color="white">{date.today().strftime("%B %d,%Y")}</font>',
            styles['subtitle']
        ),
    ]]
    header_table= Table(header_data+sub_data+user_data,colWidths=[6.5 * inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),BLUE),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('TOPPADDING',(0,0),(-1,0),18),
        ('BOTTOMPADDING',(0,-1),(-1,-1),18),
        ('LEFTPADDING',(0,0),(-1,-1),12),
        ('RIGHTPADDING',(0,0),(-1,-1),12),
        ('ROUNDEDCORNERS',[8,8,8,8]),
    ]))
    return header_table

def _stats_block(stats, styles):
    """Three stat tiles in a row."""
    def tile(label, value, bg):
        return Table(
            [[Paragraph(f'<b><font size="22">{value}</font></b>', ParagraphStyle(
                'TileVal', parent=styles['base']['Normal'],
                fontSize=22, textColor=BLUE, alignment=TA_CENTER))],
             [Paragraph(label, ParagraphStyle(
                'TileLabel', parent=styles['base']['Normal'],
                fontSize=9, textColor=SLATE_600, alignment=TA_CENTER))]],
            colWidths=[1.9 * inch]
        )

    tiles = [
        tile('Active Medications', stats.get('active_medications', 0), LIGHT_BLUE),
        tile('Total Symptoms Logged', stats.get('total_symptoms_logged', 0), LIGHT_BLUE),
        tile('Symptoms This Period', stats.get('symptoms_this_period', 0), LIGHT_BLUE),
    ]

    row_table = Table([tiles], colWidths=[2.05 * inch, 2.05 * inch, 2.05 * inch])
    row_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BLUE),
        ('BOX',        (0, 0), (0, 0), 1, SLATE_200),
        ('BOX',        (1, 0), (1, 0), 1, SLATE_200),
        ('BOX',        (2, 0), (2, 0), 1, SLATE_200),
        ('TOPPADDING',    (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    return row_table


def _medications_table(medications, styles):
    """Table of active medications."""
    if not medications:
        return Paragraph('No active medications in this period.', styles['body'])

    col_widths = [2.1*inch, 1.1*inch, 1.4*inch, 1.0*inch, 0.9*inch]
    header_row = ['Medication', 'Dosage', 'Frequency', 'Start Date', 'End Date']
    data = [header_row]

    for med in medications:
        freq = med.frequency.replace('_', ' ').title()
        end  = str(med.end_date) if med.end_date else '—'
        data.append([med.name, med.dosage, freq, str(med.start_date), end])

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header
        ('BACKGROUND',  (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR',   (0, 0), (-1, 0), WHITE),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0), 9),
        ('ALIGN',       (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING',    (0, 0), (-1, 0), 8),
        # Body
        ('FONTSIZE',    (0, 1), (-1, -1), 9),
        ('TEXTCOLOR',   (0, 1), (-1, -1), SLATE_900),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('GRID',        (0, 0), (-1, -1), 0.5, SLATE_200),
    ]))
    return t


def _symptoms_table(symptoms, styles):
    """Table of symptom logs with severity colour coding."""
    if not symptoms:
        return Paragraph('No symptoms logged in this period.', styles['body'])

    col_widths = [1.5*inch, 0.9*inch, 1.1*inch, 3.0*inch]
    header_row = ['Symptom', 'Severity', 'Date', 'Notes']
    data = [header_row]
    row_styles = []

    for i, s in enumerate(symptoms, start=1):
        bg, fg = _severity_colors(s.severity)
        notes = (s.notes[:80] + '…') if len(s.notes) > 80 else (s.notes or '—')
        data.append([s.name, f'{s.severity}/10', str(s.date), notes])
        row_styles.append(('BACKGROUND', (1, i), (1, i), bg))
        row_styles.append(('TEXTCOLOR',  (1, i), (1, i), fg))

    t = Table(data, colWidths=col_widths, repeatRows=1)
    base_style = [
        ('BACKGROUND',  (0, 0), (-1, 0), CYAN),
        ('TEXTCOLOR',   (0, 0), (-1, 0), WHITE),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0), 9),
        ('ALIGN',       (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN',       (1, 1), (1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING',    (0, 0), (-1, 0), 8),
        ('FONTSIZE',    (0, 1), (-1, -1), 9),
        ('TEXTCOLOR',   (0, 1), (0, -1), SLATE_900),
        ('TEXTCOLOR',   (2, 1), (-1, -1), SLATE_600),
        ('ROWBACKGROUNDS', (0, 1), (0, -1), [WHITE, LIGHT_BLUE]),
        ('ROWBACKGROUNDS', (2, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('GRID',        (0, 0), (-1, -1), 0.5, SLATE_200),
        ('FONTNAME',    (1, 1), (1, -1), 'Helvetica-Bold'),
    ]
    t.setStyle(TableStyle(base_style + row_styles))
    return t


def _mood_summary_block(moods, styles):
    """Small mood summary paragraph."""
    if not moods:
        return Paragraph('No mood logs in this period.', styles['body'])

    avg = sum(m.mood for m in moods) / len(moods)
    avg_label = MOOD_LABELS.get(round(avg), 'Unknown')
    best  = max(moods, key=lambda m: m.mood)
    worst = min(moods, key=lambda m: m.mood)

    text = (
        f'<b>Total logs:</b> {len(moods)} &nbsp;|&nbsp; '
        f'<b>Average mood:</b> {avg:.1f}/5 ({avg_label}) &nbsp;|&nbsp; '
        f'<b>Best day:</b> {best.date} ({MOOD_LABELS[best.mood]}) &nbsp;|&nbsp; '
        f'<b>Lowest day:</b> {worst.date} ({MOOD_LABELS[worst.mood]})'
    )
    return Paragraph(text, styles['body'])


def _ai_insight_block(insight_text, styles):
    """Renders cached AI insight or a fallback message."""
    if not insight_text:
        return Paragraph(
            'No AI insight available. Visit the Insights page to generate one.',
            styles['body']
        )
    # Truncate very long insights for the PDF
    truncated = insight_text[:1200] + ('…' if len(insight_text) > 1200 else '')
    return Paragraph(truncated.replace('\n', '<br/>'), styles['body'])


# ── Public API ────────────────────────────────────────────────────────────────

def generate_health_report(user, days: int = 30) -> bytes:
    """
    Generate a PDF health report for *user* covering the last *days* days.
    Returns the PDF as raw bytes suitable for an HTTP response.
    """
    # Lazy imports to avoid circular dependencies
    from symptoms.models import Symptom, Moodlog
    from medications.models import Medication
    from django.core.cache import cache

    end_date   = date.today()
    start_date = end_date - timedelta(days=days)

    # ── Fetch data ────────────────────────────────────────────────────────
    medications = Medication.objects.filter(user=user, is_active=True)

    symptoms = Symptom.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date,
    ).order_by('-date')

    moods = Moodlog.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date,
    ).order_by('date')

    total_symptoms = Symptom.objects.filter(user=user).count()

    stats = {
        'active_medications':   medications.count(),
        'total_symptoms_logged': total_symptoms,
        'symptoms_this_period': symptoms.count(),
    }

    # Pull latest cached AI insight for this user (any window)
    ai_insight = None
    for window in [7, 14, 30]:
        latest_symptom = Symptom.objects.filter(user=user).order_by('-logged_at').first()
        latest_ts = latest_symptom.logged_at.timestamp() if latest_symptom else 0
        cached = cache.get(f'ai_insights_{user.id}_{window}_{latest_ts}')
        if cached and 'insight' in cached:
            ai_insight = cached['insight']
            break

    # ── Build PDF ─────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f'MediTrack Health Report – {user.username}',
        author='MediTrack',
    )

    styles = _build_styles()
    story  = []

    # Header
    story.append(_header_block(user, start_date, end_date, styles))
    story.append(Spacer(1, 16))

    # Disclaimer
    story.append(Paragraph(
        '⚠️  MediTrack AI provides observations only — it does not diagnose medical conditions. '
        'Always consult a qualified healthcare professional.',
        styles['disclaimer']
    ))
    story.append(Spacer(1, 6))

    # Stats
    story.append(Paragraph('Summary', styles['section']))
    story.append(_stats_block(stats, styles))
    story.append(Spacer(1, 12))

    # Medications
    story.append(HRFlowable(width='100%', thickness=1, color=SLATE_200))
    story.append(Paragraph('Active Medications', styles['section']))
    story.append(_medications_table(medications, styles))
    story.append(Spacer(1, 12))

    # Symptoms
    story.append(HRFlowable(width='100%', thickness=1, color=SLATE_200))
    story.append(Paragraph(f'Symptom Log  ({start_date} – {end_date})', styles['section']))
    story.append(_symptoms_table(symptoms, styles))
    story.append(Spacer(1, 12))

    # Mood
    story.append(HRFlowable(width='100%', thickness=1, color=SLATE_200))
    story.append(Paragraph('Mood Summary', styles['section']))
    story.append(_mood_summary_block(list(moods), styles))
    story.append(Spacer(1, 12))

    # AI Insight
    story.append(HRFlowable(width='100%', thickness=1, color=SLATE_200))
    story.append(Paragraph('AI Health Insight (Last Cached)', styles['section']))
    story.append(_ai_insight_block(ai_insight, styles))
    story.append(Spacer(1, 20))

    # Footer note
    story.append(HRFlowable(width='100%', thickness=0.5, color=SLATE_200))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f'Generated by MediTrack on {date.today().strftime("%B %d, %Y")} '
        f'for {user.get_full_name() or user.username}. '
        f'Report covers {days} days.',
        styles['small']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()