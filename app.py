import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import pdfkit
import tempfile
import json 
import os
import base64
from datetime import datetime
from docx import Document
from dotenv import load_dotenv
import re


# Set page config FIRST
st.set_page_config(
    page_title="AI Career Assistant",
    layout="wide",
    page_icon="📄"
)

# Load environment variables
load_dotenv()

# Configure PDFKit path
WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH) if os.path.exists(WKHTMLTOPDF_PATH) else None

# Configuration
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
LANGUAGES = ["English", "Spanish", "French", "German", "Chinese"]
TEMPLATE_OPTIONS = ["Chronological", "Functional", "Combined"]

# Initialize session state
if "resume_data" not in st.session_state:
    st.session_state.resume_data = {}
if "cover_letter" not in st.session_state:
    st.session_state.cover_letter = ""
if "reference_letters" not in st.session_state:
    st.session_state.reference_letters = []
if "interview_prep" not in st.session_state:
    st.session_state.interview_prep = {}

def init_groq_chain():
    """Initialize Groq model"""
    return ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-specdec",
        temperature=0.4,
        max_tokens=4000
    )

def linkedin_import(url: str):
    """Improved LinkedIn profile import with proper template escaping"""
    try:
        # Validate LinkedIn URL format
        if not url.startswith("https://www.linkedin.com/in/"):
            raise ValueError("Invalid LinkedIn profile URL format")

        # Use proper escaping for JSON template
        system_prompt = (
            'Extract professional details from LinkedIn profile in strict JSON format: \n'
            '{{\n'
            '    "name": "Full Name",\n'
            '    "experience": ["Position1 at Company1", "Position2 at Company2"],\n'
            '    "education": ["Degree1 at School1", "Degree2 at School2"],\n'
            '    "skills": ["Skill1", "Skill2", "Skill3"]\n'
            '}}'
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Profile URL: {url}")
        ])
        
        chain = prompt | init_groq_chain() | StrOutputParser()
        response = chain.invoke({"url": url})
        
        # Extract and validate JSON
        json_str = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_str:
            raise ValueError("No valid JSON found in response")
            
        parsed_data = json.loads(json_str.group())
        
        # Validate required fields
        required_fields = ["name", "experience", "education", "skills"]
        if not all(field in parsed_data for field in required_fields):
            raise ValueError("Missing required fields in parsed data")
            
        return parsed_data
        
    except Exception as e:
        st.error(f"LinkedIn import error: {str(e)}")
        return {}

def generate_localized_content(prompt_template: str, language: str, context: dict):
    """Generate content in specified language"""
    # Merge language into context
    full_context = {**context, "language": language}
    localized_prompt = f"{prompt_template} \nRespond in {language} language"
    chain = ChatPromptTemplate.from_template(localized_prompt) | init_groq_chain() | StrOutputParser()
    return chain.invoke(full_context)

# Salary Negotiation Functions
def salary_guide(context: dict):
    prompt = """Generate salary negotiation advice for:
    Industry: {industry}
    Experience: {experience} years
    Location: {location}
    Current Salary: {current_salary}
    Include: Market rates, negotiation strategies, benefits considerations"""
    return generate_localized_content(prompt, context['language'], context)

# Interview Preparation Functions  
def interview_preparation(context: dict):
    prompt = """Generate interview preparation guide for:
    Position: {position}
    Company Type: {company_type}
    Technical Skills: {skills}
    Include: Common questions, STAR method examples, technical tests preparation"""
    return generate_localized_content(prompt, context['language'], context)

# Reference Letter Generator
def generate_reference_letter(context: dict):
    prompt = """Write professional reference letter from:
    Referee: {referee_name}
    Relationship: {relationship}
    Duration: {duration}
    Key achievements: {achievements}
    Contact: {contact_info}"""
    return generate_localized_content(prompt, context['language'], context)

def create_download_link(content, format_type, filename):
    """Generate download links with proper file handling"""
    try:
        # Create temporary file path
        temp_path = os.path.join(tempfile.gettempdir(), f"{filename}.{format_type}")
        
        # Generate file content
        if format_type == "pdf":
            if config is None:
                raise RuntimeError("PDF export requires wkhtmltopdf installation")
            pdfkit.from_string(content, temp_path, configuration=config)
        elif format_type == "docx":
            doc = Document()
            doc.add_paragraph(content)
            doc.save(temp_path)
        else:  # txt
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
        
        # Read generated file
        with open(temp_path, "rb") as f:
            data = f.read()
        
        # Create download link
        b64 = base64.b64encode(data).decode()
        download_link = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}.{format_type}">Download {format_type.upper()}</a>'
        
        return download_link
    except Exception as e:
        st.error(f"Error generating {format_type}: {str(e)}")
        return ""
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as cleanup_error:
            st.error(f"Error cleaning up files: {str(cleanup_error)}")

def main():
    # PDF instructions moved inside main()
    st.sidebar.markdown("""
    **PDF Export Requirements:**
    1. [Download wkhtmltopdf](https://wkhtmltopdf.org/downloads.html)
    2. Install with default settings
    3. Restart this application
    """)
    
    st.title("AI-Powered Career Toolkit")
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("Configuration")
        st.session_state.language = st.selectbox("Language", LANGUAGES)
        export_format = st.selectbox("Export Format", ["PDF", "DOCX", "TXT"])
        
        st.divider()
        st.header("LinkedIn Import")
        linkedin_url = st.text_input("Paste LinkedIn Profile URL")
        if st.button("Import Profile"):
            if linkedin_url:
                try:
                    imported_data = linkedin_import(linkedin_url)
                    if imported_data:
                        st.session_state.resume_data.update({
                        "name": imported_data.get("name", ""),
                        "experience": "\n".join(imported_data.get("experience", [])),
                        "education": "\n".join(imported_data.get("education", [])),
                        "skills": ", ".join(imported_data.get("skills", []))
                         })
                    st.success("Profile imported successfully!")
                except Exception as e:
                    st.error(f"Failed to process LinkedIn profile: {str(e)}")

        
    # Main Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Resume Builder", 
        "Cover Letters", 
        "Interview Prep", 
        "Salary Guide", 
        "References"
    ])

    with tab1:  # Resume Builder
        with st.form("resume_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Personal Information")
                st.session_state.resume_data["name"] = st.text_input("Full Name")
                st.session_state.resume_data["email"] = st.text_input("Email")
                st.session_state.resume_data["phone"] = st.text_input("Phone")
                
                st.subheader("Education")
                st.session_state.resume_data["education"] = st.text_area("Education Details", height=150)
                
            with col2:
                st.subheader("Professional Details")
                st.session_state.resume_data["experience"] = st.text_area("Work Experience", height=200)
                st.session_state.resume_data["skills"] = st.text_area("Skills (comma-separated)", height=100)
                st.session_state.resume_data["job_description"] = st.text_area("Target Job Description", height=150)
            
            if st.form_submit_button("Generate Resume"):
                resume_content = generate_localized_content(
                    """Create {language} resume with template: {template}
                    ATS-friendly, include: {sections}""",
                    st.session_state.language,
                    {
                        "template": "Chronological",
                        "sections": str(st.session_state.resume_data)
                    }
                )
                st.session_state.resume_content = resume_content

        if "resume_content" in st.session_state:
            st.markdown(st.session_state.resume_content, unsafe_allow_html=True)
            st.markdown(create_download_link(
                st.session_state.resume_content, 
                export_format.lower(),
                "resume"
            ), unsafe_allow_html=True)

    with tab2:  # Cover Letters
        if st.button("Generate Cover Letter"):
            st.session_state.cover_letter = generate_localized_content(
                """Write {language} cover letter for:
                Resume: {resume}
                Job: {job_desc}""",
                st.session_state.language,
                {
                    "resume": str(st.session_state.resume_data),
                    "job_desc": st.session_state.resume_data.get("job_description", "")
                }
            )
        
        if st.session_state.cover_letter:
            st.markdown(st.session_state.cover_letter, unsafe_allow_html=True)
            st.markdown(create_download_link(
                st.session_state.cover_letter,
                export_format.lower(),
                "cover_letter"
            ), unsafe_allow_html=True)

    with tab3:  # Interview Prep
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Interview Preparation")
            st.session_state.interview_prep["company_type"] = st.selectbox(
                "Company Type", ["Startup", "Corporate", "Non-Profit", "Government"])
            st.session_state.interview_prep["technical_skills"] = st.text_input("Technical Skills Required")
            
            if st.button("Generate Prep Guide"):
                st.session_state.interview_guide = interview_preparation({
                    "language": st.session_state.language,
                    "position": st.session_state.resume_data.get("job_description", ""),
                    "company_type": st.session_state.interview_prep["company_type"],
                    "skills": st.session_state.interview_prep["technical_skills"]
                })
        
        with col2:
            if "interview_guide" in st.session_state:
                st.markdown(st.session_state.interview_guide)

    with tab4:  # Salary Guide
        st.subheader("Salary Negotiation Assistant")
        with st.form("salary_form"):
            col1, col2 = st.columns(2)
            with col1:
                industry = st.text_input("Industry")
                experience = st.number_input("Years of Experience", min_value=0)
            with col2:
                location = st.text_input("Location")
                current_salary = st.number_input("Current Salary", min_value=0)
            
            if st.form_submit_button("Generate Guide"):
                st.session_state.salary_guide = salary_guide({
                    "language": st.session_state.language,
                    "industry": industry,
                    "experience": experience,
                    "location": location,
                    "current_salary": current_salary
                })
        
        if "salary_guide" in st.session_state:
            st.markdown(st.session_state.salary_guide)

    with tab5:  # References
        st.subheader("Reference Letter Generator")
        with st.form("reference_form"):
            ref_name = st.text_input("Referee Name")
            ref_title = st.text_input("Referee Position")
            relationship = st.text_input("Your Relationship")
            duration = st.text_input("Working Duration")
            
            if st.form_submit_button("Generate Letter"):
                st.session_state.reference_letter = generate_reference_letter({
                    "language": st.session_state.language,
                    "referee_name": ref_name,
                    "relationship": relationship,
                    "duration": duration,
                    "achievements": st.session_state.resume_data.get("experience", ""),
                    "contact_info": f"{ref_title}"
                })
        
        if "reference_letter" in st.session_state:
            st.markdown(st.session_state.reference_letter)
            st.markdown(create_download_link(
                st.session_state.reference_letter,
                export_format.lower(),
                "reference_letter"
            ), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
