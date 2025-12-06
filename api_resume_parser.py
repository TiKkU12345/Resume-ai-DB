"""
API-Based Resume Parser
Uses OpenAI GPT for fast, accurate resume parsing
"""

import streamlit as st
import json
import re
from typing import Dict, Any
import PyPDF2
import docx
from io import BytesIO

# Import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class APIResumeParser:
    """Fast resume parser using OpenAI API"""
    
    def __init__(self):
        """Initialize parser with API key from secrets"""
        
        # Import get_secret helper
        try:
            from app_config import get_secret
        except ImportError:
            def get_secret(key, default=None):
                import os
                value = os.getenv(key)
                if value:
                    return value
                try:
                    return st.secrets.get(key, default)
                except:
                    return default
        
        # Get API key FIRST
        self.api_key = get_secret("OPENAI_API_KEY", None)
        
        # Initialize OpenAI client if available
        if self.api_key and OPENAI_AVAILABLE:
            try:
                self.client = OpenAI(api_key=self.api_key)
                self.use_api = True
            except Exception as e:
                print(f"OpenAI init error: {e}")
                self.client = None
                self.use_api = False
        else:
            self.client = None
            self.use_api = False
    
    def parse_resume(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse resume from file content"""
        
        # Extract text
        text = self._extract_text(file_content, filename)
        
        if not text or len(text.strip()) < 50:
            return self._get_empty_resume()
        
        # Parse using API or fallback
        if self.use_api:
            return self._parse_with_api(text, filename)
        else:
            return self._parse_basic(text, filename)
    
    def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from PDF or DOCX"""
        try:
            if filename.lower().endswith('.pdf'):
                return self._extract_pdf_text(file_content)
            elif filename.lower().endswith('.docx'):
                return self._extract_docx_text(file_content)
            else:
                return file_content.decode('utf-8', errors='ignore')
        except Exception as e:
            st.error(f"Text extraction error: {str(e)}")
            return ""
    
    def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            st.error(f"PDF extraction error: {str(e)}")
            return ""
    
    def _extract_docx_text(self, file_content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            doc_file = BytesIO(file_content)
            doc = docx.Document(doc_file)
            
            text = "\n".join([para.text for para in doc.paragraphs])
            return text.strip()
        except Exception as e:
            st.error(f"DOCX extraction error: {str(e)}")
            return ""
    
    def _parse_with_api(self, text: str, filename: str) -> Dict[str, Any]:
        """Parse resume using OpenAI API"""
        try:
            prompt = f"""Extract information from this resume in JSON format:

{{
  "name": "Full name",
  "email": "Email address",
  "phone": "Phone number",
  "location": "City, State",
  "summary": "Professional summary",
  "skills": {{
    "technical": ["skill1", "skill2"],
    "soft": ["skill1", "skill2"],
    "tools": ["tool1", "tool2"]
  }},
  "experience": [
    {{
      "title": "Job title",
      "company": "Company",
      "duration": "Start - End",
      "years": 2.5,
      "description": ["Achievement 1", "Achievement 2"]
    }}
  ],
  "education": [
    {{
      "degree": "Degree name",
      "institution": "University",
      "year": "Year",
      "gpa": "GPA"
    }}
  ],
  "certifications": ["Cert 1"],
  "projects": [
    {{
      "name": "Project name",
      "description": "Description",
      "technologies": ["Tech 1"]
    }}
  ],
  "languages": ["English"],
  "total_experience_years": 5
}}

Resume:
{text[:4000]}
"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Extract resume data. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean markdown
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            result_text = result_text.strip()
            parsed_data = json.loads(result_text)
            parsed_data['filename'] = filename
            parsed_data['parsing_method'] = 'openai_api'
            
            return parsed_data
            
        except Exception as e:
            st.warning(f"API parsing failed: {str(e)}. Using basic parser.")
            return self._parse_basic(text, filename)
    
    def _parse_basic(self, text: str, filename: str) -> Dict[str, Any]:
        """Basic regex-based parsing"""
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        email = emails[0] if emails else ""
        
        # Extract phone
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        phones = re.findall(phone_pattern, text)
        phone = phones[0] if phones else ""
        
        # Extract name (first line)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        name = lines[0] if lines else filename.replace('.pdf', '').replace('.docx', '')
        
        # Common skills
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'node', 'sql', 
            'html', 'css', 'aws', 'docker', 'git'
        ]
        
        found_skills = []
        text_lower = text.lower()
        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        # Experience
        exp_pattern = r'(\d+)\+?\s*(?:years?|yrs?)'
        exp_matches = re.findall(exp_pattern, text.lower())
        total_exp = max([int(e) for e in exp_matches], default=0)
        
        return {
            'filename': filename,
            'name': name,
            'email': email,
            'phone': phone,
            'location': '',
            'summary': text[:200] + '...',
            'skills': {
                'technical': found_skills,
                'soft': [],
                'tools': []
            },
            'experience': [],
            'education': [],
            'certifications': [],
            'projects': [],
            'languages': [],
            'total_experience_years': total_exp,
            'parsing_method': 'basic_regex'
        }
    
    def _get_empty_resume(self) -> Dict[str, Any]:
        """Return empty resume structure"""
        return {
            'filename': '',
            'name': '',
            'email': '',
            'phone': '',
            'location': '',
            'summary': '',
            'skills': {'technical': [], 'soft': [], 'tools': []},
            'experience': [],
            'education': [],
            'certifications': [],
            'projects': [],
            'languages': [],
            'total_experience_years': 0,
            'parsing_method': 'empty'
        }
