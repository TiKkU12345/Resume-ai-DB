"""
AI Resume Parser - Step 1 Implementation
Extracts structured data from PDF and DOCX resumes
"""

import re
import json
import PyPDF2
import docx
import spacy
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path
import phonenumbers
from email_validator import validate_email

# Load spaCy model for NLP processing
# Run: python -m spacy download en_core_web_sm
nlp = spacy.load("en_core_web_sm")

import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


class ResumeParser:
    """
    resume parser that extracts structured information
    from PDF and DOCX files
    """
    
    def __init__(self):
        # Common section headers in resumes
        self.section_patterns = {
            'contact': r'(contact|personal\s+information|contact\s+information)',
            'summary': r'(summary|objective|profile|about\s+me|professional\s+summary)',
            'experience': r'(experience|work\s+experience|employment|work\s+history|professional\s+experience)',
            'education': r'(education|academic|qualification|university|college)',
            'skills': r'(skills|technical\s+skills|core\s+competencies|expertise|proficiency)',
            'projects': r'(projects|personal\s+projects|academic\s+projects)',
            'certifications': r'(certification|certificates|licenses)',
            'achievements': r'(achievement|awards|honors|accomplishments)',
            'languages': r'(languages|language\s+proficiency)'
        }
        
        # Common skills keywords
        self.technical_skills = self._load_skills_database()
        
        # Date patterns
        self.date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',  # 01/2020, 01-2020
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]*\d{4})',  # Jan 2020
            r'(\d{4})',  # 2020
            r'(Present|Current|Now|Ongoing)',  # Present
        ]
    
    def _load_skills_database(self) -> Dict[str, List[str]]:
        """Load comprehensive skills database"""
        return {
            'programming': [
                'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'Go', 'Rust',
                'PHP', 'Swift', 'Kotlin', 'TypeScript', 'Scala', 'R', 'MATLAB'
            ],
            'web': [
                'HTML', 'CSS', 'React', 'Angular', 'Vue.js', 'Node.js', 'Express',
                'Django', 'Flask', 'FastAPI', 'Spring Boot', 'ASP.NET', 'jQuery'
            ],
            'database': [
                'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Cassandra',
                'Oracle', 'SQL Server', 'DynamoDB', 'Neo4j', 'Elasticsearch'
            ],
            'ml_ai': [
                'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Keras',
                'scikit-learn', 'NLP', 'Computer Vision', 'OpenCV', 'NLTK', 'spaCy'
            ],
            'cloud': [
                'AWS', 'Azure', 'Google Cloud', 'Docker', 'Kubernetes', 'Jenkins',
                'CI/CD', 'Terraform', 'Ansible', 'Git', 'GitHub', 'GitLab'
            ],
            'data_science': [
                'Data Analysis', 'Pandas', 'NumPy', 'Matplotlib', 'Seaborn', 
                'Tableau', 'Power BI', 'Apache Spark', 'Hadoop', 'ETL'
            ],
            'soft_skills': [
                'Leadership', 'Communication', 'Problem Solving', 'Team Work',
                'Project Management', 'Agile', 'Scrum', 'Critical Thinking'
            ]
        }
    
    def parse_resume(self, file_path: str) -> Dict:
        """
        Main method to parse resume from file
        
        Args:
            file_path: Path to resume file (PDF or DOCX)
            
        Returns:
            Dictionary containing structured resume data
        """
        file_path = Path(file_path)
        
        # Extract text based on file type
        if file_path.suffix.lower() == '.pdf':
            text = self._extract_text_from_pdf(file_path)
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            text = self._extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Parse the extracted text
        parsed_data = self._parse_text(text)
        parsed_data['file_name'] = file_path.name
        parsed_data['parsed_date'] = datetime.now().isoformat()
        
        return parsed_data
    
    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF: {e}")
            raise
        
        return text
    
    def _extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file"""
        text = ""
        try:
            doc = docx.Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            raise
        
        return text
    
    def _parse_text(self, text: str) -> Dict:
        """Parse extracted text and structure the data"""
        
        # Initialize result dictionary
        result = {
            'contact': {},
            'summary': '',
            'experience': [],
            'education': [],
            'skills': {},
            'projects': [],
            'certifications': [],
            'achievements': [],
            'languages': []
        }
        
        # Split text into sections
        sections = self._split_into_sections(text)
        
        # Extract contact information
        result['contact'] = self._extract_contact_info(text)
        
        # Extract each section
        for section_name, section_text in sections.items():
            if section_name == 'experience':
                result['experience'] = self._extract_experience(section_text)
            elif section_name == 'education':
                result['education'] = self._extract_education(section_text)
            elif section_name == 'skills':
                result['skills'] = self._extract_skills(section_text)
            elif section_name == 'summary':
                result['summary'] = self._extract_summary(section_text)
            elif section_name == 'projects':
                result['projects'] = self._extract_projects(section_text)
            elif section_name == 'certifications':
                result['certifications'] = self._extract_certifications(section_text)
        
        # Calculate total experience in years
        result['total_experience_years'] = self._calculate_total_experience(result['experience'])
        
        return result
    
    def _split_into_sections(self, text: str) -> Dict[str, str]:
        """Split resume text into sections based on headers"""
        sections = {}
        current_section = 'unknown'
        current_text = []
        
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if line is a section header
            section_found = False
            for section_name, pattern in self.section_patterns.items():
                if re.search(pattern, line_lower, re.IGNORECASE):
                    # Save previous section
                    if current_text:
                        sections[current_section] = '\n'.join(current_text)
                    
                    # Start new section
                    current_section = section_name
                    current_text = []
                    section_found = True
                    break
            
            if not section_found and line.strip():
                current_text.append(line)
        
        # Save last section
        if current_text:
            sections[current_section] = '\n'.join(current_text)
        
        return sections
    
    def _extract_contact_info(self, text: str) -> Dict:
        """Extract contact information (email, phone, LinkedIn, etc.)"""
        contact = {
            'name': '',
            'email': '',
            'phone': '',
            'linkedin': '',
            'github': '',
            'location': ''
        }
        
        # Extract email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            contact['email'] = emails[0]
        
        # Extract phone number
        phone_patterns = [
            r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}',
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                contact['phone'] = phones[0]
                break
        
        # Extract LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin:
            contact['linkedin'] = linkedin.group()
        
        # Extract GitHub
        github_pattern = r'github\.com/[\w-]+'
        github = re.search(github_pattern, text, re.IGNORECASE)
        if github:
            contact['github'] = github.group()
        
        # Extract name (usually first line or near email)
        name = self._extract_name(text)
        contact['name'] = name
        
        return contact
    
    def _extract_name(self, text: str) -> str:
        """Extract candidate name using NLP"""
        # Process first 5 lines where name usually appears
        lines = text.split('\n')[:5]
        
        for line in lines:
            line = line.strip()
            if len(line) > 3 and len(line) < 50:
                # Use spaCy NER to detect person names
                doc = nlp(line)
                for ent in doc.ents:
                    if ent.label_ == 'PERSON':
                        return ent.text
                
                # Fallback: check if line looks like a name
                words = line.split()
                if 2 <= len(words) <= 4 and all(word[0].isupper() for word in words):
                    return line
        
        return "Name Not Found"
    
    def _extract_experience(self, text: str) -> List[Dict]:
        """Extract work experience entries"""
        experiences = []
        
        # Split by common delimiters
        entries = re.split(r'\n(?=[A-Z])', text)
        
        for entry in entries:
            if len(entry.strip()) < 20:  # Skip very short entries
                continue
            
            exp = {
                'company': '',
                'position': '',
                'start_date': '',
                'end_date': '',
                'duration': '',
                'description': '',
                'location': ''
            }
            
            lines = entry.split('\n')
            
            # First line often contains position and company
            if lines:
                first_line = lines[0]
                # Try to parse position and company
                if '|' in first_line or '-' in first_line or 'at' in first_line.lower():
                    parts = re.split(r'\s*[\|\-]\s*|\s+at\s+', first_line, maxsplit=1)
                    if len(parts) >= 2:
                        exp['position'] = parts[0].strip()
                        exp['company'] = parts[1].strip()
                    else:
                        exp['position'] = first_line.strip()
                else:
                    exp['position'] = first_line.strip()
            
            # Extract dates
            dates = self._extract_dates(entry)
            if dates:
                if len(dates) >= 2:
                    exp['start_date'] = dates[0]
                    exp['end_date'] = dates[1]
                elif len(dates) == 1:
                    exp['start_date'] = dates[0]
                    exp['end_date'] = 'Present'
            
            # Extract description (bullet points or paragraphs)
            description_lines = []
            for line in lines[1:]:
                line = line.strip()
                if line and not self._is_date_line(line):
                    description_lines.append(line)
            
            exp['description'] = ' '.join(description_lines)
            
            # Calculate duration if dates available
            exp['duration'] = self._calculate_duration(exp['start_date'], exp['end_date'])
            
            if exp['position'] or exp['company']:
                experiences.append(exp)
        
        return experiences
    
    def _extract_education(self, text: str) -> List[Dict]:
        """Extract education entries"""
        education = []
        
        entries = re.split(r'\n(?=[A-Z])', text)
        
        for entry in entries:
            if len(entry.strip()) < 10:
                continue
            
            edu = {
                'degree': '',
                'institution': '',
                'field_of_study': '',
                'start_date': '',
                'end_date': '',
                'gpa': '',
                'location': ''
            }
            
            lines = entry.split('\n')
            
            # Extract degree and institution
            if lines:
                first_line = lines[0]
                
                # Common degree patterns
                degree_patterns = [
                    r'(Bachelor|Master|PhD|Ph\.D|B\.Tech|M\.Tech|B\.Sc|M\.Sc|MBA|BBA)',
                    r'(B\.E\.|M\.E\.|B\.S\.|M\.S\.)'
                ]
                
                for pattern in degree_patterns:
                    match = re.search(pattern, first_line, re.IGNORECASE)
                    if match:
                        edu['degree'] = match.group()
                        break
                
                # Extract institution (often after degree or on second line)
                if len(lines) > 1:
                    edu['institution'] = lines[1].strip()
                else:
                    # Try to extract from first line
                    parts = first_line.split(',')
                    if len(parts) > 1:
                        edu['institution'] = parts[-1].strip()
            
            # Extract field of study
            field_keywords = ['Computer Science', 'Engineering', 'Business', 'Mathematics', 
                            'Physics', 'Chemistry', 'Biology', 'Economics']
            for line in lines:
                for field in field_keywords:
                    if field.lower() in line.lower():
                        edu['field_of_study'] = field
                        break
            
            # Extract dates
            dates = self._extract_dates(entry)
            if dates:
                if len(dates) >= 2:
                    edu['start_date'] = dates[0]
                    edu['end_date'] = dates[1]
                elif len(dates) == 1:
                    edu['end_date'] = dates[0]
            
            # Extract GPA
            gpa_pattern = r'GPA[:\s]*([0-9]\.[0-9]{1,2})|([0-9]\.[0-9]{1,2})\s*/\s*[0-9]'
            gpa_match = re.search(gpa_pattern, entry, re.IGNORECASE)
            if gpa_match:
                edu['gpa'] = gpa_match.group().strip()
            
            if edu['degree'] or edu['institution']:
                education.append(edu)
        
        return education
    
    def _extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract skills categorized by type"""
        skills = {
            'programming': [],
            'web': [],
            'database': [],
            'ml_ai': [],
            'cloud': [],
            'data_science': [],
            'soft_skills': [],
            'other': []
        }
        
        text_lower = text.lower()
        
        # Match skills from database
        for category, skill_list in self.technical_skills.items():
            for skill in skill_list:
                # Look for exact match or variations
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    if skill not in skills[category]:
                        skills[category].append(skill)
        
        # Remove empty categories
        skills = {k: v for k, v in skills.items() if v}
        
        return skills
    
    def _extract_summary(self, text: str) -> str:
        """Extract professional summary/objective"""
        # Clean and return the summary text
        summary = text.strip()
        return summary if len(summary) > 20 else ""
    
    def _extract_projects(self, text: str) -> List[Dict]:
        """Extract project details"""
        projects = []
        
        entries = re.split(r'\n(?=[A-Z])', text)
        
        for entry in entries:
            if len(entry.strip()) < 15:
                continue
            
            project = {
                'title': '',
                'description': '',
                'technologies': [],
                'link': ''
            }
            
            lines = entry.split('\n')
            if lines:
                project['title'] = lines[0].strip()
                project['description'] = ' '.join([l.strip() for l in lines[1:] if l.strip()])
            
            # Extract URLs
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, entry)
            if urls:
                project['link'] = urls[0]
            
            if project['title']:
                projects.append(project)
        
        return projects
    
    def _extract_certifications(self, text: str) -> List[Dict]:
        """Extract certifications"""
        certifications = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 5:
                cert = {
                    'name': line,
                    'issuer': '',
                    'date': ''
                }
                
                # Try to extract date
                dates = self._extract_dates(line)
                if dates:
                    cert['date'] = dates[0]
                
                certifications.append(cert)
        
        return certifications
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        dates = []
        
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return dates
    
    def _is_date_line(self, line: str) -> bool:
        """Check if line primarily contains date information"""
        dates = self._extract_dates(line)
        return len(dates) > 0 and len(line.strip()) < 50
    
    def _calculate_duration(self, start_date: str, end_date: str) -> str:
        """Calculate duration between dates"""
        if not start_date:
            return ""
        
        # Simple estimation (you can make this more sophisticated)
        if end_date.lower() in ['present', 'current', 'now', 'ongoing']:
            return "Ongoing"
        
        try:
            # Extract years
            start_year = int(re.search(r'\d{4}', start_date).group())
            if 'present' in end_date.lower():
                end_year = datetime.now().year
            else:
                end_year = int(re.search(r'\d{4}', end_date).group())
            
            years = end_year - start_year
            return f"{years} years" if years > 1 else f"{years} year"
        except:
            return ""
    
    def _calculate_total_experience(self, experiences: List[Dict]) -> float:
        """Calculate total years of experience"""
        total_months = 0
        
        for exp in experiences:
            duration = exp.get('duration', '')
            if 'year' in duration.lower():
                years = int(re.search(r'\d+', duration).group())
                total_months += years * 12
        
        return round(total_months / 12, 1)
    
    def save_to_json(self, parsed_data: Dict, output_path: str):
        """Save parsed resume data to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2, ensure_ascii=False)
        print(f"Resume data saved to {output_path}")
    
    def save_to_csv(self, parsed_data_list: List[Dict], output_path: str):
        """Save multiple parsed resumes to CSV"""
        # Flatten nested dictionaries for CSV
        flattened_data = []
        for data in parsed_data_list:
            flat = {
                'name': data['contact'].get('name', ''),
                'email': data['contact'].get('email', ''),
                'phone': data['contact'].get('phone', ''),
                'linkedin': data['contact'].get('linkedin', ''),
                'total_experience': data.get('total_experience_years', 0),
                'num_experiences': len(data.get('experience', [])),
                'num_educations': len(data.get('education', [])),
                'total_skills': sum(len(v) for v in data.get('skills', {}).values()),
                'num_projects': len(data.get('projects', [])),
                'num_certifications': len(data.get('certifications', []))
            }
            flattened_data.append(flat)
        
        df = pd.DataFrame(flattened_data)
        df.to_csv(output_path, index=False)
        print(f"Resume summary saved to {output_path}")


# Example usage
if __name__ == "__main__":
    # Initialize parser
    parser = ResumeParser()
    
    # Parse a single resume
    try:
        resume_data = parser.parse_resume("sample_resume.pdf")
        
        # Print results
        print("=" * 60)
        print("PARSED RESUME DATA")
        print("=" * 60)
        print(f"\nName: {resume_data['contact']['name']}")
        print(f"Email: {resume_data['contact']['email']}")
        print(f"Phone: {resume_data['contact']['phone']}")
        print(f"Total Experience: {resume_data['total_experience_years']} years")
        
        print(f"\n📚 Education ({len(resume_data['education'])} entries):")
        for edu in resume_data['education']:
            print(f"  - {edu['degree']} at {edu['institution']}")
        
        print(f"\n💼 Experience ({len(resume_data['experience'])} entries):")
        for exp in resume_data['experience']:
            print(f"  - {exp['position']} at {exp['company']} ({exp['duration']})")
        
        print(f"\n🛠️ Skills:")
        for category, skills in resume_data['skills'].items():
            if skills:
                print(f"  {category.replace('_', ' ').title()}: {', '.join(skills[:5])}")
        
        # Save to JSON
        parser.save_to_json(resume_data, "parsed_resume.json")
        
        print("\n✅ Resume parsing completed successfully!")
        
    except FileNotFoundError:
        print("❌ Error: Please provide a valid resume file path")
        print("\nTo test this parser:")
        print("1. Place a resume PDF/DOCX in the same directory")
        print("2. Update the file path in the code")
        print("3. Run the script again")