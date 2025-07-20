import os
import re
import json
from datetime import datetime
import steamlit as st
import PyPDF2 as pdf
from docx import Document
import google.generativeai as genai
from google.generativeai import types
from pydantic import BaseModel
from utils import optimize_keywords, enforce_page_limit

os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

# Initialize Gemini client
try:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client = None

class CVOptimization(BaseModel):
    """CV optimization response model"""
    ats_score: int
    missing_keywords: list
    optimized_content: str
    suggestions: list

def extract_resume_text(uploaded_file):
    """Extract text from uploaded resume file"""
    if uploaded_file.name.endswith(".pdf"):
        reader = pdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    elif uploaded_file.name.endswith(".docx"):
        doc = Document(uploaded_file)
        return '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
    else:
        return ""

def generate_cv(resume_text, job_description, target_match, template, sections, quantitative_focus, action_verb_intensity, keyword_matching):
    """Generate optimized CV using Gemini AI"""
    
    # Build sections string
    sections_list = [section for section, include in sections.items() if include]
    sections_string = ", ".join(sections_list)
    
    # Adjust prompt based on settings
    intensity_mapping = {
        "Moderate": "moderate use of action verbs",
        "High": "strong emphasis on action verbs",
        "Very High": "maximum use of powerful action verbs"
    }
    
    matching_mapping = {
        "Conservative": "maintain authenticity while incorporating key terms",
        "Balanced": "strategically integrate job description keywords",
        "Aggressive": "maximize keyword density and exact phrase matching"
    }
    
    # Direct prompt for CV output only
    prompt = f"""
    You are a professional resume writer and an expert in ATS optimization and role alignment.

    Your job is to:
    1. Parse the candidate's resume and extract **real experience**.
    2. Analyze the job description to extract **critical keywords, tools, titles, skills, certifications, and action verbs**.
    3. Identify mismatches between the resume and JD (especially job titles like "Data Analyst" vs. "Data Engineer").
    4. Reframe the resume to match the **job role in the JD**, especially:
    - Modify job titles to **align with the JD role** where reasonable (e.g., change "Data Analyst" to "Data Engineer" if tools/skills match).
    - Rewrite bullet points to highlight experience relevant to the **target role**, using the JD's vocabulary.
    - Emphasize **tools, platforms, pipelines, databases, programming, and architecture** relevant to the target role.
    - Add **measurable outcomes and business impact** wherever possible.

    Fabricate work experience to better align with the JD with quantitive ATS keywords.
    ✅ You may upgrade job titles if the responsibilities/tools used justify it.

    Your goal is to improve this resume to achieve a **{target_match}% ATS match** with the JD.

    Generate the resume in this exact plain text format with these headers:

    NAME:
    PROFESSIONAL SUMMARY:
    

    KEY SKILLS:
    Skill 1, Skill 2.....

    WORK EXPERIENCE:(Contains 22 bullet points inlcuding all the experiences mixed with JD and resume and bullet point should be unique.)
    Company | Role | Dates
    • Bullet 1
    • Bullet 2

    EDUCATION:
    • Degree | Institution | Year

    PROJECTS:
    Project Name 1
    • Bullet 1
    • Bullet 2
    
    Project Name 2
    • Bullet 1
    • Bullet 2

    Resume Content:
    {resume_text}

    Job Description:
    {job_description}
    """

    
    try:
        if not client:
            raise Exception("Gemini AI client not initialized")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="text/plain",
                temperature=0.2  # Lower temperature for more focused output
            )
        )
        
        # Handle different response conditions
        if not response:
            raise Exception("No response received from AI")
        
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.finish_reason.name == 'MAX_TOKENS':
                # Try to get partial content
                if candidate.content and candidate.content.parts:
                    partial_text = ""
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            partial_text += part.text
                    if partial_text:
                        optimized_cv = partial_text
                    else:
                        raise Exception("MAX_TOKENS reached and no partial content available")
                else:
                    raise Exception("MAX_TOKENS reached and no content available")
            elif not response.text:
                raise Exception("AI response was empty")
            else:
                optimized_cv = response.text
        else:
            raise Exception("No candidates in response")
        

        
        # Clean up the response
        optimized_cv = clean_cv_content(optimized_cv)
        optimized_cv = enforce_page_limit(optimized_cv)

        from utils import extract_keywords_from_text

        jd_keywords = extract_keywords_from_text(job_description)

        def bold_keywords_in_work_exp(cv_text, keywords):
            if "WORK EXPERIENCE:" not in cv_text:
                return cv_text

            parts = cv_text.split("WORK EXPERIENCE:")
            before = parts[0]
            after = parts[1]

            lines = after.split('\n')
            bolded_lines = []
            for line in lines:
                if line.startswith("•") or "|" in line:
                    for kw in keywords:
                        pattern = r'\b(' + re.escape(kw) + r')\b'
                        line = re.sub(pattern, r'**\1**', line, flags=re.IGNORECASE)
                bolded_lines.append(line)

            return before + "WORK EXPERIENCE:\n" + '\n'.join(bolded_lines)

        optimized_cv = bold_keywords_in_work_exp(optimized_cv, jd_keywords)

        return optimized_cv.strip()
        
    except Exception as e:
        raise Exception(f"Failed to generate CV: {str(e)}")

def generate_cover_letter(resume_text, job_description):
    """Generate cover letter using Gemini AI"""
    
    prompt = f"""
    You are a professional cover letter writer.

    Create a compelling cover letter that:
    1. Addresses the specific job requirements
    2. Highlights relevant experience from the resume
    3. Shows enthusiasm for the role and company
    4. Maintains professional tone
    5. Is concise (3-4 paragraphs)
    6. Includes a strong opening and closing

    Use this structure:
    - Start with: "Dear [Hiring Manager/Job Title],"
    - Middle: Showcase 2-3 accomplishments aligned to the JD
    - Close with: request for interview and polite sign-off
    - After the sign-off, include the applicant's **email and phone number** (extract from resume)

    Resume:
    {resume_text}

    Job Description:
    {job_description}

    Generate a professional cover letter in plain text format.
    """

    
    try:
        if not client:
            raise Exception("Gemini AI client not initialized")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        if not response or not response.text:
            raise Exception("AI response was empty or None")
        
        return response.text
        
    except Exception as e:
        raise Exception(f"Failed to generate cover letter: {str(e)}")

def clean_cv_content(content):
    """Clean and format CV content"""
    if not content:
        return "Error: No content received from AI"
    
    # Remove markdown formatting
    content = re.sub(r'\*\*', '', content)
    content = re.sub(r'__', '', content)
    
    # Remove excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove any hidden markers
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    # Ensure proper section formatting
    content = re.sub(r'^([A-Z][A-Z\s]+):', r'\n\1:', content, flags=re.MULTILINE)
    
    return content.strip()

def analyze_cv_ats_score(cv_content, job_description):
    """Analyze CV ATS compatibility score"""
    
    prompt = f"""
    You are an ATS analysis expert.
    
    Analyze the CV against the job description and provide:
    1. ATS compatibility score (0-100)
    2. Keyword match percentage
    3. Missing critical keywords
    4. Specific improvement suggestions
    
    Return JSON format:
    {{
        "ats_score": number,
        "keyword_match": number,
        "missing_keywords": [list],
        "suggestions": [list]
    }}
    
    CV Content:
    {cv_content}
    
    Job Description:
    {job_description}
    """
    
    try:
        if not client:
            raise Exception("Gemini AI client not initialized")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        if not response or not response.text:
            raise Exception("AI response was empty or None")
        
        return json.loads(response.text)
        
    except Exception as e:
        return {
            "ats_score": 0,
            "keyword_match": 0,
            "missing_keywords": [],
            "suggestions": ["Error analyzing CV"]
        }

def extract_key_metrics(cv_content):
    """Extract quantifiable metrics from CV"""
    # Pattern to find numbers and percentages
    metrics_pattern = r'(\d+(?:\.\d+)?(?:%|K|M|B|k|m|b|\+|,\d+)*)'
    
    metrics = re.findall(metrics_pattern, cv_content)
    
    return {
        'total_metrics': len(metrics),
        'metrics_found': metrics,
        'quantification_score': min(100, len(metrics) * 5)  # 5 points per metric, max 100
    }

def enhance_action_verbs(content, intensity="High"):
    """Enhance action verbs in CV content"""
    
    action_verbs = {
        "Moderate": [
            "managed", "developed", "created", "implemented", "led", "coordinated",
            "designed", "analyzed", "improved", "organized", "planned", "supervised"
        ],
        "High": [
            "spearheaded", "orchestrated", "revolutionized", "transformed", "pioneered",
            "architected", "optimized", "streamlined", "accelerated", "amplified"
        ],
        "Very High": [
            "catapulted", "revolutionized", "masterminded", "propelled", "dominated",
            "commanded", "conquered", "devastated", "obliterated", "annihilated"
        ]
    }
    
    # This would be implemented with more sophisticated text processing
    # For now, return the content as-is
    return content
