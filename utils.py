import re
import os
import time
from typing import Dict, List, Any
import google.generativeai as genai
from google.generativeai import types
import streamlit as st
from dotenv import load_dotenv

# Load secrets into environment
os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

# Initialize Gemini client
try:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Error initializing Gemini client in utils: {e}")
    client = None

def get_gemini_response(prompt: str, model: str = "gemini-2.5-flash") -> str:
    """Get response from Gemini AI with error handling"""
    try:
        if not client:
            st.error("Gemini AI client not initialized")
            return ""
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=4096,
                temperature=0.7
            )
        )
        return response.text if response.text else ""
    except Exception as e:
        st.error(f"AI processing error: {str(e)}")
        return ""

def optimize_keywords(cv_content: str, job_description: str = None, target_match: int = None) -> Dict[str, Any]:
    """Deterministic ATS score checker based on real keyword overlap"""

    if not job_description:
        return get_default_analysis()

    # Normalize & extract keyword sets
    jd_keywords = set(re.findall(r'\b[a-zA-Z][a-zA-Z0-9\-]+\b', job_description.lower()))
    cv_keywords = set(re.findall(r'\b[a-zA-Z][a-zA-Z0-9\-]+\b', cv_content.lower()))

    common_keywords = jd_keywords.intersection(cv_keywords)
    keyword_match_pct = round(len(common_keywords) / len(jd_keywords) * 100) if jd_keywords else 0

    # Quantitative content check
    quantitative_pct = calculate_quantitative_percentage(cv_content)
    quantitative_score = min(int(quantitative_pct), 30)  # Cap at 30%

    # Formatting validation
    validation = validate_cv_format(cv_content)
    format_score = 20 if validation["valid"] else 10

    # Weighted score calculation
    base_score = min(50, keyword_match_pct)  # Cap keyword contribution to 50
    ats_score = base_score + quantitative_score + format_score
    ats_score = min(100, ats_score)

    # Auto-boost to target match if enabled and match is sufficient
    if target_match and keyword_match_pct >= target_match:
        ats_score = max(ats_score, target_match)

    # Missing keywords
    missing_keywords = list(jd_keywords - cv_keywords)
    top_missing = sorted(missing_keywords)[:10]

    # Optional: Gemini suggestions
    suggestions = []

    # Basic improvements (without calling optimize_keywords again)
    if quantitative_pct < 50:
        suggestions.append("Add more quantifiable achievements with specific numbers and percentages")

    if not validation["valid"]:
        suggestions.append("Fix formatting issues and add missing sections")

    if keyword_match_pct < 60:
        suggestions.append("Incorporate more exact keywords from the job description")


    return {
        "score": ats_score,
        "keyword_match": keyword_match_pct,
        "suggestions": suggestions,
        "missing_keywords": top_missing,
        "strengths": validation.get("strengths", ["Good structure", "Relevant experience"])
    }


def get_default_analysis():
    """Return default analysis when AI fails"""
    return {
        'score': 70,
        'keyword_match': 65,
        'suggestions': ['Enhance technical skills section', 'Add more quantifiable results'],
        'missing_keywords': ['industry-specific terms'],
        'strengths': ['Good structure', 'Clear formatting']
    }

def extract_keywords_from_text(text: str) -> List[str]:
    """Extract potential keywords from text"""
    # Remove common words and extract meaningful terms
    words = re.findall(r'\b[A-Za-z]{3,}\b', text.lower())
    
    # Filter out common words
    common_words = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'have', 'was', 'were', 'been', 'are', 'will', 'would', 'could', 'should'}
    keywords = [word for word in set(words) if word not in common_words]
    
    return keywords[:20]  # Return top 20 keywords

def enforce_page_limit(content: str, max_pages: int = 2) -> str:
    """Enforce page limit by trimming content intelligently"""
    
    if not content:
        return "Error: No content to limit"
    
    lines = content.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    # Estimate lines per page (approximately 50 lines per page)
    lines_per_page = 50
    max_lines = max_pages * lines_per_page
    
    if len(non_empty_lines) <= max_lines:
        return content
    
    # Parse into sections
    sections = parse_content_sections(content)
    
    # Priority order for sections
    priority_sections = [
        'professional summary',
        'key skills',
        'work experience',
        'education',
        'certifications',
        'projects',
        'awards',
        'languages',
        'hobbies'
    ]
    
    # Rebuild content with priority
    rebuilt_lines = []
    current_line_count = 0
    
    # Add name/header first
    name_section = get_name_section(sections)
    if name_section:
        rebuilt_lines.extend(name_section)
        current_line_count += len(name_section)
    
    # Add sections by priority
    for priority in priority_sections:
        if current_line_count >= max_lines:
            break
            
        section_content = get_section_by_priority(sections, priority)
        if section_content:
            available_lines = max_lines - current_line_count
            if available_lines > 0:
                # Trim section if necessary
                trimmed_section = trim_section_content(section_content, available_lines)
                rebuilt_lines.extend(trimmed_section)
                current_line_count += len(trimmed_section)
    
    return '\n'.join(rebuilt_lines)

def parse_content_sections(content: str) -> Dict[str, List[str]]:
    """Parse content into sections"""
    sections = {}
    current_section = None
    current_content = []
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a section header
        if line.endswith(':') and len(line) > 1 and line.isupper():
            # Save previous section
            if current_section:
                sections[current_section.lower()] = current_content
            
            # Start new section
            current_section = line[:-1]  # Remove colon
            current_content = []
        elif ':' in line and len(line.split(':')) == 2:
            # Alternative section header format
            if current_section:
                sections[current_section.lower()] = current_content
            
            current_section = line.split(':')[0].strip()
            current_content = [line.split(':')[1].strip()] if line.split(':')[1].strip() else []
        else:
            if current_section:
                current_content.append(line)
            else:
                # This might be the name or first line
                sections['header'] = sections.get('header', []) + [line]
    
    # Save last section
    if current_section:
        sections[current_section.lower()] = current_content
    
    return sections

def get_name_section(sections: Dict[str, List[str]]) -> List[str]:
    """Get name/header section"""
    if 'header' in sections:
        return sections['header']
    return []

def get_section_by_priority(sections: Dict[str, List[str]], priority: str) -> List[str]:
    """Get section content by priority keyword"""
    for section_name, content in sections.items():
        if priority in section_name.lower():
            return [f"{section_name.upper()}:"] + content
    return []

def trim_section_content(section_content: List[str], max_lines: int) -> List[str]:
    """Trim section content to fit within line limit"""
    if len(section_content) <= max_lines:
        return section_content
    
    # Keep header and trim content
    if section_content and section_content[0].endswith(':'):
        header = [section_content[0]]
        content = section_content[1:max_lines-1]
        return header + content
    else:
        return section_content[:max_lines]

def calculate_quantitative_percentage(content: str) -> float:
    """Calculate percentage of quantitative content"""
    lines = content.split('\n')
    quantitative_lines = 0
    total_content_lines = 0
    
    # Pattern to match numbers, percentages, and quantifiable metrics
    quantitative_pattern = r'(\d+(?:\.\d+)?(?:%|K|M|B|k|m|b|\+|,\d+)*|\$\d+|increased?|decreased?|improved?|reduced?|saved?|generated?|achieved?)'
    
    for line in lines:
        line = line.strip()
        if line and not line.endswith(':'):  # Skip empty lines and headers
            total_content_lines += 1
            if re.search(quantitative_pattern, line, re.IGNORECASE):
                quantitative_lines += 1
    
    if total_content_lines == 0:
        return 0.0
    
    return (quantitative_lines / total_content_lines) * 100

def enhance_with_action_verbs(content: str, intensity: str = "High") -> str:
    """Enhance content with action verbs"""
    
    action_verbs = {
        "Moderate": [
            "managed", "developed", "created", "implemented", "led", "coordinated",
            "designed", "analyzed", "improved", "organized", "planned", "supervised"
        ],
        "High": [
            "spearheaded", "orchestrated", "revolutionized", "transformed", "pioneered",
            "architected", "optimized", "streamlined", "accelerated", "amplified",
            "executed", "delivered", "achieved", "established", "initiated"
        ],
        "Very High": [
            "masterminded", "propelled", "catapulted", "dominated", "commanded",
            "conquered", "devastated", "obliterated", "revolutionized", "transformed",
            "pioneered", "trailblazed", "championed", "galvanized", "maximized"
        ]
    }
    
    # This is a simplified implementation
    # In practice, you'd use more sophisticated NLP to replace verbs contextually
    weak_verbs = ["worked", "did", "made", "helped", "was responsible for", "handled"]
    replacement_verbs = action_verbs.get(intensity, action_verbs["High"])
    
    enhanced_content = content
    for i, weak_verb in enumerate(weak_verbs):
        if i < len(replacement_verbs):
            enhanced_content = re.sub(
                r'\b' + weak_verb + r'\b',
                replacement_verbs[i],
                enhanced_content,
                flags=re.IGNORECASE
            )
    
    return enhanced_content

def validate_cv_format(content: str) -> Dict[str, Any]:
    """Validate CV format and structure"""
    issues = []
    suggestions = []
    
    # Check for essential sections
    essential_sections = ['professional summary', 'experience', 'skills', 'education']
    content_lower = content.lower()
    
    for section in essential_sections:
        if section not in content_lower:
            issues.append(f"Missing {section} section")
    
    # Check for contact information
    if not re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
        issues.append("Missing email address")
    
    # Check for phone number
    if not re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', content):
        issues.append("Missing phone number")
    
    # Check for quantifiable achievements
    quantitative_percent = calculate_quantitative_percentage(content)
    if quantitative_percent < 30:
        suggestions.append("Add more quantifiable achievements with numbers and percentages")
    
    # Check content length
    word_count = len(content.split())
    if word_count < 200:
        issues.append("CV content is too short")
    elif word_count > 800:
        suggestions.append("Consider condensing content for better readability")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'suggestions': suggestions,
        'quantitative_percentage': quantitative_percent,
        'word_count': word_count
    }

def format_processing_time(seconds: float) -> str:
    """Format processing time for display"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for download"""
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized

def estimate_reading_time(content: str) -> int:
    """Estimate reading time in seconds"""
    words = len(content.split())
    # Average reading speed: 200-250 words per minute
    reading_speed = 225  # words per minute
    return int((words / reading_speed) * 60)

def extract_contact_info(content: str) -> Dict[str, str]:
    """Extract contact information from CV"""
    contact_info = {}
    
    # Extract email
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
    if email_match:
        contact_info['email'] = email_match.group()
    
    # Extract phone
    phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', content)
    if phone_match:
        contact_info['phone'] = phone_match.group()
    
    # Extract LinkedIn
    linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', content, re.IGNORECASE)
    if linkedin_match:
        contact_info['linkedin'] = linkedin_match.group()
    
    return contact_info

def calculate_ats_score(cv_content: str, job_description: str) -> int:
    """Calculate ATS compatibility score"""
    try:
        # Use keyword analysis
        analysis = optimize_keywords(cv_content, job_description)
        return analysis.get('score', 75)
    except:
        # Fallback calculation
        jd_words = set(job_description.lower().split())
        cv_words = set(cv_content.lower().split())
        
        common_words = jd_words.intersection(cv_words)
        if len(jd_words) > 0:
            match_ratio = len(common_words) / len(jd_words)
            return min(100, int(match_ratio * 100) + 30)  # Add base score
        
        return 75  # Default score

def get_improvement_suggestions(cv_content: str, job_description: str) -> List[str]:
    """Get specific improvement suggestions"""
    suggestions = []
    
    # Check quantitative content
    quant_percent = calculate_quantitative_percentage(cv_content)
    if quant_percent < 50:
        suggestions.append("Add more quantifiable achievements with specific numbers and percentages")
    
    # Check for action verbs
    weak_verbs = ["worked", "did", "made", "helped", "was responsible for"]
    for verb in weak_verbs:
        if verb in cv_content.lower():
            suggestions.append(f"Replace weak verbs like '{verb}' with stronger action verbs")
            break
    
    # Check for job-specific keywords
    if job_description:
        analysis = optimize_keywords(cv_content, job_description)
        missing_keywords = analysis.get('missing_keywords', [])
        if missing_keywords:
            suggestions.append(f"Include these important keywords: {', '.join(missing_keywords[:3])}")
    
    # Check formatting
    validation = validate_cv_format(cv_content)
    suggestions.extend(validation['suggestions'])
    
    return suggestions[:5]  # Return top 5 suggestions
