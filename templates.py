from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black, darkblue, gray
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
import re

def get_available_templates():
    """Get available CV templates"""
    return {
        "professional": {
            "name": "Professional Classic",
            "description": "Clean, traditional layout perfect for corporate roles",
            "preview": "classic_preview.png"
        },
        "modern": {
            "name": "Modern Minimalist",
            "description": "Contemporary design with clean lines and modern typography",
            "preview": "modern_preview.png"
        },
        "creative": {
            "name": "Creative Design",
            "description": "Eye-catching layout for creative and design roles",
            "preview": "creative_preview.png"
        },
        "technical": {
            "name": "Technical Focus",
            "description": "Optimized for technical roles with emphasis on skills",
            "preview": "technical_preview.png"
        },
        "executive": {
            "name": "Executive Premium",
            "description": "Sophisticated design for senior-level positions",
            "preview": "executive_preview.png"
        }
    }

def apply_template(cv_content, template_name):
    """Apply selected template to CV content"""
    
    if template_name == "professional":
        return create_professional_template(cv_content)
    elif template_name == "modern":
        return create_modern_template(cv_content)
    elif template_name == "creative":
        return create_creative_template(cv_content)
    elif template_name == "technical":
        return create_technical_template(cv_content)
    elif template_name == "executive":
        return create_executive_template(cv_content)
    else:
        return create_professional_template(cv_content)

def create_professional_template(cv_content):
    """Create professional template PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=1*inch, bottomMargin=1*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        spaceBefore=12,
        textColor=darkblue
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=9,                 # Slightly smaller font
        spaceAfter=2,               # ↓ Reduce spacing between lines
        leading=11,                 # ↓ Tighten line height
        alignment=TA_JUSTIFY        # ✅ Justify text
    )
    
    # Parse CV content into sections
    sections = parse_cv_sections(cv_content)
    # ✅ Enforce 2-page line budget
    sections = trim_sections_to_fit(sections, max_lines=100)
    
    # Build story
    story = []
    
    # Add name (first line as title)
    if sections:
        first_section = list(sections.keys())[0]
        if not first_section.endswith(':'):
            # First line is likely the name
            story.append(Paragraph(first_section, title_style))
            story.append(Spacer(1, 12))
    
    # Add sections
    for section_name, section_content in sections.items():
        if section_name.endswith(':'):
            # This is a section header
            story.append(Paragraph(section_name, heading_style))
            
            # Add section content
            for line in section_content:
                if line.strip():
                    formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line.strip())
                    story.append(Paragraph(formatted, body_style))
            
            story.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_modern_template(cv_content):
    """Create modern minimalist template"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.8*inch, leftMargin=0.8*inch, topMargin=0.8*inch, bottomMargin=0.8*inch)
    
    styles = getSampleStyleSheet()
    
    # Modern styles with clean typography
    title_style = ParagraphStyle(
        'ModernTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=15,
        alignment=TA_LEFT,
        textColor=black
    )
    
    heading_style = ParagraphStyle(
        'ModernHeading',
        parent=styles['Heading2'],
        fontSize=11,
        spaceAfter=8,
        spaceBefore=15,
        textColor=black,
        borderWidth=0,
        borderColor=gray,
        borderPadding=5
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=9,                 # Slightly smaller font
        spaceAfter=2,               # ↓ Reduce spacing between lines
        leading=11,                 # ↓ Tighten line height
        alignment=TA_JUSTIFY        # ✅ Justify text
    )
    
    sections = parse_cv_sections(cv_content)
    story = []
    
    # Build modern layout
    for section_name, section_content in sections.items():
        if not section_name.endswith(':'):
            story.append(Paragraph(section_name, title_style))
            story.append(Spacer(1, 15))
        else:
            story.append(Paragraph(section_name, heading_style))
            for line in section_content:
                if line.strip():
                    story.append(Paragraph(f"• {line.strip()}", body_style))
            story.append(Spacer(1, 10))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_creative_template(cv_content):
    """Create creative design template"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.7*inch, leftMargin=0.7*inch, topMargin=0.9*inch, bottomMargin=0.9*inch)
    
    styles = getSampleStyleSheet()
    
    # Creative styles with more visual elements
    title_style = ParagraphStyle(
        'CreativeTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=darkblue
    )
    
    heading_style = ParagraphStyle(
        'CreativeHeading',
        parent=styles['Heading2'],
        fontSize=13,
        spaceAfter=10,
        spaceBefore=15,
        textColor=darkblue,
        borderWidth=1,
        borderColor=darkblue,
        borderPadding=8
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=9,                 # Slightly smaller font
        spaceAfter=2,               # ↓ Reduce spacing between lines
        leading=11,                 # ↓ Tighten line height
        alignment=TA_JUSTIFY        # ✅ Justify text
    )
    
    sections = parse_cv_sections(cv_content)
    story = []
    
    # Build creative layout
    for section_name, section_content in sections.items():
        if not section_name.endswith(':'):
            story.append(Paragraph(section_name, title_style))
            story.append(Spacer(1, 20))
        else:
            story.append(Paragraph(section_name, heading_style))
            for line in section_content:
                if line.strip():
                    story.append(Paragraph(f"◆ {line.strip()}", body_style))
            story.append(Spacer(1, 12))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_technical_template(cv_content):
    """Create technical focus template"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.85*inch, bottomMargin=0.85*inch)
    
    styles = getSampleStyleSheet()
    
    # Technical styles with emphasis on skills
    title_style = ParagraphStyle(
        'TechnicalTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=15,
        alignment=TA_LEFT,
        textColor=black
    )
    
    heading_style = ParagraphStyle(
        'TechnicalHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12,
        textColor=black
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=9,                 # Slightly smaller font
        spaceAfter=2,               # ↓ Reduce spacing between lines
        leading=11,                 # ↓ Tighten line height
        alignment=TA_JUSTIFY        # ✅ Justify text
    )
    
    sections = parse_cv_sections(cv_content)
    story = []
    
    # Build technical layout
    for section_name, section_content in sections.items():
        if not section_name.endswith(':'):
            story.append(Paragraph(section_name, title_style))
            story.append(Spacer(1, 15))
        else:
            story.append(Paragraph(section_name, heading_style))
            
            # Special handling for skills section
            if "skill" in section_name.lower():
                # Create table layout for skills
                skills_text = " | ".join([line.strip() for line in section_content if line.strip()])
                story.append(Paragraph(skills_text, body_style))
            else:
                for line in section_content:
                    if line.strip():
                        story.append(Paragraph(f"▪ {line.strip()}", body_style))
            
            story.append(Spacer(1, 10))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_executive_template(cv_content):
    """Create executive premium template"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.8*inch, leftMargin=0.8*inch, topMargin=1*inch, bottomMargin=1*inch)
    
    styles = getSampleStyleSheet()
    
    # Executive styles with sophisticated appearance
    title_style = ParagraphStyle(
        'ExecutiveTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=18,
        alignment=TA_CENTER,
        textColor=darkblue
    )
    
    heading_style = ParagraphStyle(
        'ExecutiveHeading',
        parent=styles['Heading2'],
        fontSize=13,
        spaceAfter=10,
        spaceBefore=15,
        textColor=darkblue,
        borderWidth=2,
        borderColor=darkblue,
        borderPadding=6
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=9,                 # Slightly smaller font
        spaceAfter=2,               # ↓ Reduce spacing between lines
        leading=11,                 # ↓ Tighten line height
        alignment=TA_JUSTIFY        # ✅ Justify text
    )
    
    sections = parse_cv_sections(cv_content)
    story = []
    
    # Build executive layout
    for section_name, section_content in sections.items():
        if not section_name.endswith(':'):
            story.append(Paragraph(section_name, title_style))
            story.append(Spacer(1, 18))
        else:
            story.append(Paragraph(section_name, heading_style))
            for line in section_content:
                if line.strip():
                    story.append(Paragraph(f"• {line.strip()}", body_style))
            story.append(Spacer(1, 12))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def parse_cv_sections(cv_content):
    """Parse CV content into sections"""
    sections = {}
    current_section = None
    current_content = []

    lines = cv_content.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Heuristic: detect headers (capitalized and short)
        if re.match(r'^[A-Z][A-Za-z ]{2,}:\s*$', line.strip()):
            if current_section:
                sections[current_section] = current_content
            current_section = line if line.endswith(':') else f"{line}:"
            current_content = []
        else:
            if current_section:
                current_content.append(line)
            else:
                sections[line] = []

    if current_section:
        sections[current_section] = current_content
    
    if 'Name:' not in sections and 'header' in sections:
        sections['Name:'] = sections.pop('header')

    return sections

def estimate_page_count(content):
    """Estimate page count for content"""
    # Rough estimation: 50 lines per page
    lines = content.split('\n')
    return max(1, len([line for line in lines if line.strip()]) // 50)

def trim_content_to_pages(content, max_pages=2):
    """Trim content to fit within page limit"""
    if estimate_page_count(content) <= max_pages:
        return content
    
    # Split into sections and prioritize
    sections = parse_cv_sections(content)
    
    # Priority order for sections
    priority_order = [
        "Professional Summary",
        "Key Skills",
        "Work Experience",
        "Education",
        "Certifications",
        "Projects",
        "Awards",
        "Languages",
        "Hobbies"
    ]
    
    # Rebuild content with priority sections
    rebuilt_content = []
    
    for section_name in priority_order:
        for key, value in sections.items():
            if section_name.lower() in key.lower():
                rebuilt_content.append(key)
                rebuilt_content.extend(value)
                break
    
    return '\n'.join(rebuilt_content)

def estimate_total_lines(sections):
    """Estimate total rendered lines based on content length"""
    total_lines = 0
    for section_content in sections.values():
        total_lines += len([line for line in section_content if line.strip()])
    return total_lines

def trim_sections_to_fit(sections, max_lines=100):
    """Trim content from long sections (like Projects or Work Experience) to fit page limit"""
    total_lines = estimate_total_lines(sections)

    if total_lines <= max_lines:
        return sections  # Already within limit

    # Priority list for trimming (most trim first)
    trim_order = ["Projects", "Work Experience", "Certifications", "Awards", "Languages", "Hobbies"]
    
    for section_key in trim_order:
        for key in list(sections.keys()):
            if section_key.lower() in key.lower():
                original = sections[key]
                if len(original) > 4:  # Only trim if content is long enough
                    trimmed = original[:len(original) - 2]  # Trim 2 lines
                    sections[key] = trimmed
                    total_lines = estimate_total_lines(sections)
                    if total_lines <= max_lines:
                        return sections  # Trimmed enough
    
    return sections  # Return best possible under max_lines

