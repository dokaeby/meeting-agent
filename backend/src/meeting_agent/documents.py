from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def render_pdf(content: dict, settings) -> bytes:
    candidates = [
        settings.pdf_font,
        "C:/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    font = next((p for p in candidates if p and Path(p).is_file()), None)
    if font:
        name = "MeetingKorean"
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, font))
    else:
        name = "HYSMyeongJo-Medium"
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(name))
        if settings.environment == "production":
            raise ValueError("MA_PDF_FONT must reference an installed Korean font")
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, title=content["title"], rightMargin=42, leftMargin=42)
    body = ParagraphStyle("body", fontName=name, fontSize=10, leading=17, wordWrap="CJK")
    heading = ParagraphStyle(
        "heading",
        parent=body,
        fontSize=17,
        leading=24,
        textColor=colors.HexColor("#17243b"),
        spaceAfter=12,
    )
    story = [
        Paragraph(escape(content["title"]), heading),
        Paragraph("AI 생성 회의록 · 발송 전 정확성을 확인해 주세요.", body),
        Spacer(1, 12),
    ]
    sections = [
        ("요약", [content["overview"]]),
        ("논의", content["discussions"]),
        ("결정사항", content["decisions"]),
        ("담당 업무", content["actions"]),
    ]
    for title, items in sections:
        story.extend([Spacer(1, 12), Paragraph(title, heading)])
        for item in items:
            details = item["text"]
            if item.get("assignee_name"):
                details += f" / 담당: {item['assignee_name']}"
            if item.get("due_raw"):
                details += f" / 기한: {item['due_raw']}"
            details += " [근거: " + ", ".join(item["evidence_ids"]) + "]"
            story.append(Paragraph(escape(details).replace("\n", "<br/>"), body))
    for warning in content["warnings"]:
        story.append(Paragraph("확인 필요: " + escape(warning), body))
    doc.build(story)
    return stream.getvalue()
