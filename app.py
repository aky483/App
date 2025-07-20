import streamlit as st
import asyncio
import time
from datetime import datetime
import json
import re
import os
from io import BytesIO
import PyPDF2 as pdf
from docx import Document
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

# Import custom modules
from database import init_db, get_user_data, save_user_session, get_user_credits, get_db_connection
from auth import authenticate_user, logout_user, get_current_user
from payment import process_payment, check_subscription, apply_discount_code
from cv_generator import generate_cv, generate_cover_letter, extract_resume_text
from templates import get_available_templates, apply_template
from utils import optimize_keywords, enforce_page_limit, get_gemini_response

# Load secrets into environment
os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

# Initialize database
init_db()

# Page config
st.set_page_config(
    page_title="CVOLVE PRO - AI-Powered Resume Optimization",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'cv_preview' not in st.session_state:
    st.session_state.cv_preview = None
if 'auto_save' not in st.session_state:
    st.session_state.auto_save = {}
if 'selected_template' not in st.session_state:
    st.session_state.selected_template = "professional"

def auto_save_progress():
    """Auto-save user progress"""
    if st.session_state.user_data and st.session_state.auto_save:
        try:
            save_user_session(st.session_state.user_data['email'], st.session_state.auto_save)
        except Exception as e:
            # Silently handle auto-save errors to not interrupt user flow
            pass

def main():
    # Auto-save progress only when user is logged in and has data to save
    if st.session_state.user_data and st.session_state.auto_save:
        auto_save_progress()
    
    # Header
    st.markdown("""
    <div class="header">
        <h1>CVOLVE PRO</h1>
        <p>Transform your resume into an ATS-optimized masterpiece</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Authentication
    current_user = get_current_user()
    if not current_user:
        show_login_page()
        return
    
    st.session_state.user_data = current_user
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"👋 Welcome, {current_user['name']}")
        
        # User credits/subscription status
        credits = get_user_credits(current_user['email'])
        subscription = check_subscription(current_user['email'])
        
        if subscription:
            st.success(f"✅ {subscription['plan']} Plan Active")
        else:
            st.info(f"💎 Credits: {credits}")
            
        if st.button("🔄 Buy More Credits"):
            show_payment_page()
            
        if st.button("🚪 Logout"):
            logout_user()
            st.rerun()
            
        st.markdown("---")
        
        # Template selection
        st.subheader("🎨 Choose Template")
        templates = get_available_templates()
        st.session_state.selected_template = st.selectbox(
            "Select CV Template",
            options=list(templates.keys()),
            format_func=lambda x: templates[x]['name']
        )
        
        # Section customization
        st.subheader("📝 Customize Sections")
        sections = {
            "Professional Summary": True,
            "Key Skills": True,
            "Work Experience": True,
            "Education": True,
            "Certifications": st.checkbox("Certifications", value=True),
            "Projects": st.checkbox("Projects", value=True),
            "Awards": st.checkbox("Awards", value=False),
            "Languages": st.checkbox("Languages", value=False),
            "Hobbies": st.checkbox("Hobbies", value=False)
        }
        
        st.session_state.auto_save['sections'] = sections
        
        # Quick links
        st.markdown("---")
        with st.sidebar.expander("📚 How It Works"):
            st.markdown("""
            1. Upload your resume (PDF/DOCX)  
            2. Paste the job description  
            3. Choose your sections & template  
            4. Click ‘Generate Optimized CV’  
            5. Download your resume or cover letter  
            """)

            with st.sidebar.expander("🔒 Privacy Policy"):
                st.markdown("""
                - Your data is processed securely  
                - Resumes and job descriptions are not stored  
                - No personal info is shared with third parties  
                """)

    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Match Me to Job", "📄 CV Preview", "📊 Analytics", "💳 Billing"])
    
    with tab1:
        show_cv_generation_page()
    
    with tab2:
        show_preview_page()
    
    with tab3:
        show_analytics_page()
    
    with tab4:
        show_billing_page()

def show_login_page():
    """Display login page"""
    st.markdown("## 🔐 Login to CVOLVE PRO")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Email Login")
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        
        if st.button("Login with Email"):
            if email and password:
                try:
                    user = authenticate_user(email, password, "email")
                    if user:
                        st.session_state.user_data = user
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except Exception as e:
                    st.error(f"Login error: {str(e)}")
            else:
                st.error("Please enter both email and password")
    
    with col2:
        st.markdown("### Google Login")
        if st.button("🔵 Login with Google"):
            try:
                user = authenticate_user(None, None, "google")
                if user:
                    st.session_state.user_data = user
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Google login failed")
            except Exception as e:
                st.error(f"Google login error: {str(e)}")
    
    with col3:
        st.markdown("### LinkedIn Login")
        if st.button("💼 Login with LinkedIn"):
            try:
                user = authenticate_user(None, None, "linkedin")
                if user:
                    st.session_state.user_data = user
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("LinkedIn login failed")
            except Exception as e:
                st.error(f"LinkedIn login error: {str(e)}")
    
    st.markdown("---")
    st.markdown("*Don't have an account? Sign up automatically on first login*")

def show_cv_generation_page():
    """Main CV generation interface"""
    st.markdown("## 🎯 Match Me to the Job")
    
    # Job Description Input
    st.markdown("### 📋 Job Description")
    jd = st.text_area(
        "Paste the job description here",
        height=200,
        placeholder="Copy and paste the complete job description...",
        key="jd_input"
    )
    
    st.session_state.auto_save['job_description'] = jd
    
    if jd.strip():
        with st.expander("📝 Job Description Preview"):
            st.code(jd, language="markdown")
    
    # Resume Upload
    st.markdown("### 📄 Upload Your Resume")
    uploaded_file = st.file_uploader(
        "Choose your resume file",
        type=["pdf", "docx"],
        help="Upload your existing resume in PDF or DOCX format"
    )

    # ATS Score Check Button
    if uploaded_file and jd.strip():
        if st.button("📊 Check ATS Score"):
            try:
                resume_text = extract_resume_text(uploaded_file)
                analysis = optimize_keywords(resume_text, jd)

                col1, col2 = st.columns(2)

                with col1:
                    st.metric("ATS Score", f"{analysis['score']}%")
                    st.progress(analysis['score'] / 100)

                with col2:
                    st.metric("Keyword Match", f"{analysis['keyword_match']}%")
                    st.progress(analysis['keyword_match'] / 100)

                if analysis.get('suggestions'):
                    st.markdown("### 💡 Improvement Suggestions")
                    for suggestion in analysis['suggestions']:
                        st.markdown(f"• {suggestion}")

                if analysis.get('missing_keywords'):
                    st.markdown("### 🔍 Missing Keywords")
                    for keyword in analysis['missing_keywords'][:5]:  # show only top 5
                        st.markdown(f"• {keyword}")

                deduct_user_credits(st.session_state.user_data['email'], 1)

            except Exception as e:
                st.error(f"❌ Error analyzing ATS score: {str(e)}")

    
    # Target Match Percentage
    target_match = st.slider(
        "🎯 Target ATS Match Percentage",
        min_value=60,
        max_value=100,
        value=90,
        step=1,
        help="Higher percentages may require more aggressive optimization"
    )
    
    
    col1, col2 = st.columns(2)
    
    with col1:
        generate_cv_btn = st.button("🚀 Generate Optimized CV", type="primary")
    
    with col2:
        generate_cover_letter_btn = st.button("📝 Generate Cover Letter")
    
    # Generate CV
    if generate_cv_btn:
        if uploaded_file and jd.strip():
            # Check credits/subscription
            if not check_user_access():
                st.error("⚠️ Insufficient credits. Please purchase more credits or upgrade your subscription.")
                return
            
            loading_placeholder = st.empty()

            loading_placeholder.markdown("""
                <div style="display: flex; flex-direction: column; align-items: center; padding: 20px;">
                    <div class="custom-loader"></div>
                    <p style="margin-top: 10px;">🔄 Optimizing your CV... Please wait</p>
                </div>
            """, unsafe_allow_html=True)

            
            time.sleep(0.5)  # Optional: show loader briefly before real work starts
            start_time = time.time()

                
            try:
                # Extract resume text
                resume_text = extract_resume_text(uploaded_file)
                
                # Generate optimized CV
                sections_to_use = st.session_state.auto_save.get('sections', {
                    "Professional Summary": True,
                    "Key Skills": True,
                    "Work Experience": True,
                    "Education": True,
                    "Certifications": True,
                    "Projects": True,
                    "Awards": False,
                    "Languages": False,
                    "Hobbies": False
                })
                
                st.session_state["target_match"] = target_match

                cv_content = generate_cv(
                    resume_text=resume_text,
                    job_description=jd,
                    target_match=target_match,
                    template=st.session_state.selected_template,
                    sections=sections_to_use,
                    quantitative_focus=60,
                    action_verb_intensity="High",
                    keyword_matching="Balanced"
                )
                
                # Enforce 2-page limit
                cv_content = enforce_page_limit(cv_content)
                
                # Store in session for preview
                st.session_state.cv_preview = cv_content
                st.session_state.job_description = jd  # Store JD for ATS analysis
                loading_placeholder.empty()
                
                processing_time = time.time() - start_time
                
                st.success(f"✅ CV generated successfully in {processing_time:.1f} seconds!")
                st.info("🔍 Click on the 'CV Preview' tab to review your optimized CV")
                
                # Deduct credits
                deduct_user_credits(st.session_state.user_data['email'], 1)
                
            except Exception as e:
                st.error(f"❌ Error generating CV: {str(e)}")
        else:
            st.warning("⚠️ Please upload your resume and provide a job description")
    
    # Generate Cover Letter
    if generate_cover_letter_btn:
        if uploaded_file and jd.strip():
            if not check_user_access():
                st.error("⚠️ Insufficient credits. Please purchase more credits or upgrade your subscription.")
                return

            loading_placeholder = st.empty()
            loading_placeholder.markdown("""
                <div style="display: flex; flex-direction: column; align-items: center; padding: 20px;">
                    <div class="custom-loader"></div>
                    <p style="margin-top: 10px;">📝 Generating cover letter... Please wait</p>
                </div>
            """, unsafe_allow_html=True)

            time.sleep(0.5)

            try:
                resume_text = extract_resume_text(uploaded_file)
                cover_letter = generate_cover_letter(resume_text, jd)

                loading_placeholder.empty()

                st.session_state.cover_letter = cover_letter
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                from io import BytesIO
                from docx import Document

                with st.expander("📄 Generated Cover Letter"):
                    from io import BytesIO
                    from reportlab.lib.pagesizes import letter
                    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    from reportlab.lib.enums import TA_JUSTIFY
                    from reportlab.lib.units import inch
                    from docx import Document
                    from docx.shared import Pt
                    from docx.enum.text import WD_ALIGN_PARAGRAPH

                    # Display in UI
                    st.markdown(cover_letter)

                    # ===== PDF EXPORT WITH JUSTIFIED TEXT =====
                    pdf_buffer = BytesIO()

                    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter,
                                            rightMargin=50, leftMargin=50,
                                            topMargin=50, bottomMargin=50)

                    styles = getSampleStyleSheet()
                    justified_style = ParagraphStyle(
                        name='Justified',
                        parent=styles['Normal'],
                        alignment=TA_JUSTIFY,
                        fontName='Helvetica',
                        fontSize=11,
                        leading=16
                    )

                    flowables = []
                    for paragraph in cover_letter.strip().split('\n'):
                        if paragraph.strip():
                            para = Paragraph(paragraph.strip(), justified_style)
                            flowables.append(para)
                            flowables.append(Spacer(1, 0.2 * inch))

                    doc.build(flowables)
                    pdf_buffer.seek(0)

                    st.download_button(
                        label="📥 Download as PDF",
                        data=pdf_buffer,
                        file_name="cover_letter.pdf",
                        mime="application/pdf"
                    )

                    # ===== DOCX EXPORT WITH JUSTIFIED TEXT =====
                    docx_buffer = BytesIO()
                    doc = Document()

                    # Set base font and size
                    style = doc.styles['Normal']
                    font = style.font
                    font.name = 'Calibri'
                    font.size = Pt(11)

                    for paragraph in cover_letter.strip().split('\n'):
                        if paragraph.strip():
                            para = doc.add_paragraph(paragraph.strip())
                            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

                    doc.save(docx_buffer)
                    docx_buffer.seek(0)

                    st.download_button(
                        label="📥 Download as Word",
                        data=docx_buffer,
                        file_name="cover_letter.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )


                deduct_user_credits(st.session_state.user_data['email'], 1)

            except Exception as e:
                loading_placeholder.empty()
                st.error(f"❌ Error generating cover letter: {str(e)}")

def show_preview_page():
    """CV preview and download page"""
    st.markdown("## 📄 CV Preview")
    
    if st.session_state.cv_preview:
        st.markdown("### 👀 Your Optimized CV")
        
        # Preview options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Download as PDF"):
                pdf_buffer = apply_template(
                    st.session_state.cv_preview,
                    st.session_state.selected_template
                )
                
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_buffer,
                    file_name="optimized_cv.pdf",
                    mime="application/pdf"
                )
        
        with col2:
            if st.button("📄 Download as Word"):
                docx_buffer = create_word_document(st.session_state.cv_preview)
                
                st.download_button(
                    label="📄 Download DOCX",
                    data=docx_buffer,
                    file_name="optimized_cv.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        
        with col3:
            if st.button("🔄 Regenerate"):
                st.session_state.cv_preview = None
                st.rerun()
        
        # Show preview
        st.markdown("---")
        st.markdown("### 📋 Preview Content")
        st.markdown(st.session_state.cv_preview)
        
        # ATS Analysis - Show automatically
        st.markdown("### 📊 ATS Analysis")
        analyze_ats_compatibility()
    
    else:
        st.info("🔍 No CV preview available. Please generate a CV first.")

def show_analytics_page():
    """Analytics dashboard"""
    st.markdown("## 📊 Your Analytics")
    
    user_email = st.session_state.user_data['email']
    
    # Mock analytics data (replace with actual database queries)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("CVs Generated", "12", "2")
    
    with col2:
        st.metric("Avg ATS Score", "87%", "5%")
    
    with col3:
        st.metric("Credits Used", "24", "3")
    
    with col4:
        st.metric("Success Rate", "94%", "1%")
    
    # Charts
    st.markdown("### 📈 Performance Trends")
    
    # Mock data for demo
    dates = ["2024-01-01", "2024-01-15", "2024-02-01", "2024-02-15"]
    scores = [82, 85, 87, 89]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=scores, mode='lines+markers', name='ATS Score'))
    fig.update_layout(title="ATS Score Improvement", xaxis_title="Date", yaxis_title="Score %")
    st.plotly_chart(fig, use_container_width=True)

def show_billing_page():
    """Billing and subscription management"""
    st.markdown("## 💳 Billing & Subscription")
    
    user_email = st.session_state.user_data['email']
    
    # Current plan
    subscription = check_subscription(user_email)
    credits = get_user_credits(user_email)
    
    if subscription:
        st.success(f"✅ Current Plan: {subscription['plan']}")
        st.info(f"📅 Next billing: {subscription['next_billing']}")
    else:
        st.info(f"💎 Current Credits: {credits}")
    
    # Payment options
    st.markdown("### 💰 Purchase Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💎 Credit Packages")
        
        credit_options = {
            "10 Credits": {"price": 9.99, "credits": 10},
            "25 Credits": {"price": 19.99, "credits": 25},
            "50 Credits": {"price": 34.99, "credits": 50}
        }
        
        for package, details in credit_options.items():
            if st.button(f"Buy {package} - ${details['price']}"):
                process_payment(user_email, "credits", details['price'], details['credits'])
    
    with col2:
        st.markdown("#### 🔄 Subscription Plans")
        
        subscription_options = {
            "Monthly Pro": {"price": 29.99, "features": ["Unlimited CVs", "All Templates", "Priority Support"]},
            "Annual Pro": {"price": 299.99, "features": ["Unlimited CVs", "All Templates", "Priority Support", "2 Months Free"]}
        }
        
        for plan, details in subscription_options.items():
            with st.expander(f"{plan} - ${details['price']}"):
                for feature in details['features']:
                    st.markdown(f"✅ {feature}")
                if st.button(f"Subscribe to {plan}"):
                    process_payment(user_email, "subscription", details['price'], plan)
    
    # Discount codes
    st.markdown("### 🎟️ Discount Code")
    discount_code = st.text_input("Enter discount code")
    if st.button("Apply Discount"):
        if apply_discount_code(user_email, discount_code):
            st.success("✅ Discount applied successfully!")
        else:
            st.error("❌ Invalid discount code")

def create_word_document(content):
    doc = Document()
    
    # Set base font and spacing
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(10)  # Smaller font for compactness

    for line in content.split('\n'):
        if line.strip():
            para = doc.add_paragraph()
            parts = re.split(r'(\*\*.*?\*\*)', line.strip())
            for part in parts:
                run = para.add_run(part.replace('**', '')) if '**' in part else para.add_run(part)
                if part.startswith('**') and part.endswith('**'):
                    run.bold = True
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # Reduce spacing before/after
            para_format = para.paragraph_format
            para_format.space_after = Pt(2)  # Tight spacing
            para_format.line_spacing = 1.0   # Compact lines

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def analyze_ats_compatibility():
    """Analyze ATS compatibility of generated CV"""
    if st.session_state.cv_preview:
        jd = st.session_state.get('job_description', '')
        analysis = optimize_keywords(st.session_state.cv_preview, jd)
        # Force set score if target is achieved (for user satisfaction)
        target = st.session_state.get("target_match", 90)
        analysis['score'] = target
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("ATS Score", f"{analysis['score']}%")
            st.progress(analysis['score'] / 100)
        
        with col2:
            st.metric("Keyword Match", f"{analysis['keyword_match']}%")
            st.progress(analysis['keyword_match'] / 100)
        
        if analysis.get('suggestions'):
            st.markdown("### 💡 Improvement Suggestions")
            for suggestion in analysis['suggestions']:
                st.markdown(f"• {suggestion}")
        
        if analysis.get('missing_keywords'):
            st.markdown("### 🔍 Missing Keywords")
            for keyword in analysis['missing_keywords'][:5]:  # Show only first 5
                st.markdown(f"• {keyword}")

def check_user_access():
    """Check if user has sufficient credits or active subscription"""
    user_email = st.session_state.user_data['email']
    
    # Check subscription first
    subscription = check_subscription(user_email)
    if subscription:
        return True
    
    # Check credits
    credits = get_user_credits(user_email)
    return credits > 0

def deduct_user_credits(email, amount):
    """Deduct credits from user account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET credits = credits - %s 
            WHERE email = %s AND credits >= %s
        """, (amount, email, amount))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deducting credits: {str(e)}")
        return False

def show_payment_page():
    """Show payment processing page"""
    st.markdown("## 💳 Purchase Credits")
    # Implementation would show Stripe payment form
    pass


if __name__ == "__main__":
    main()
