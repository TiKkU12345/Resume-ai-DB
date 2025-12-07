"""
AI Resume Shortlisting - Web Interface using Streamlit
Beautiful, interactive dashboard for resume screening and ranking
FIXED VERSION - All errors resolved
"""

import streamlit as st

# Page configuration - ONLY ONCE!
st.set_page_config(
    page_title="AI Resume Shortlisting System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.user = None
    st.session_state.parsed_resumes = []
    st.session_state.ranked_candidates = []
    st.session_state.current_job_id = None
    st.session_state.page = 'Dashboard'

# Other imports
import pandas as pd
import json
import os
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from api_resume_parser import APIResumeParser as ResumeParser
from job_resume_matcher import CandidateRanker, JobDescriptionParser
from datetime import datetime

# Comment out missing modules for now
# from email_integration import EmailManager, render_email_panel
# from bulk_upload import render_bulk_upload_ui
# from interview_questions import render_question_generator_ui

from database import SupabaseManager
from admin_approval_auth import AdminApprovalAuth as AuthManager

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .candidate-card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
        background-color: #ffffff;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
    }
    .score-excellent {
        color: #10b981;
        font-weight: bold;
    }
    .score-good {
        color: #f59e0b;
        font-weight: bold;
    }
    .score-moderate {
        color: #ef4444;
        font-weight: bold;
    }
    h1 {
        color: #1e3a8a;
    }
    </style>
""", unsafe_allow_html=True)


class ResumeShortlistingApp:
    """Main application class for the web interface"""
    
    def __init__(self):
        self.parser = ResumeParser()
        self.ranker = CandidateRanker()
        self.job_parser = JobDescriptionParser()
        
        # Initialize database with error handling
        try:
            self.db = SupabaseManager()
            self.db_available = True
        except Exception as e:
            st.error(f"⚠️ Database connection failed: {str(e)}")
            st.info("The app will continue with limited functionality (no persistence).")
            self.db_available = False
            self.db = None

        
        # Initialize authentication
        try:
            self.auth_manager = AuthManager()
        except Exception as e:
            st.warning(f"Authentication initialization warning: {str(e)}")
            self.auth_manager = None
        
        # Initialize session state
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize all session state variables"""
        defaults = {
            'parsed_resumes': [],
            'ranked_candidates': [],
            'job_description': "",
            'current_job_id': None,
            'current_job_title': "",
            'page': 'Dashboard',
            'authenticated': False,
            'user_email': None
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def navigate_to(self, page_name):
        """Safe navigation helper"""
        st.session_state.page = page_name
        st.rerun()
    
    def run(self):
        """Main application runner"""
        
        # Check authentication first (if available)
        if self.auth_manager and not self.auth_manager.is_authenticated():
            render_auth_page()
            return

        # Header
        st.title("🎯 AI Resume Shortlisting System")
        st.markdown("**Intelligent Resume Screening powered by Machine Learning**")
        st.markdown("---")
        
        # Sidebar
        self.render_sidebar()
        if self.auth_manager:
            render_auth_sidebar()
        
        # Main content based on selected page
        page = st.session_state.get('page', 'Dashboard')

        # Route to appropriate page
        page_methods = {
            'Dashboard': self.page_dashboard,
            'Upload Resumes': self.page_upload_resumes,
            'Bulk Upload': self.page_bulk_upload,
            'Job Description': self.page_job_description,
            'Rankings': self.page_rankings,
            'Send Emails': self.page_send_emails,
            'Interview Questions': self.page_interview_questions,
            'Analytics': self.page_analytics,
            'History': self.page_history,
            'Search': self.page_search
        }
        
        page_method = page_methods.get(page, self.page_dashboard)
        page_method()
    
    def render_sidebar(self):
        """Render sidebar navigation"""
        with st.sidebar:
            # Logo - Fixed: removed use_container_width parameter
            st.image("https://via.placeholder.com/200x80/667eea/ffffff?text=AI+Recruiter", 
                    width=200)
            st.markdown("---")
            
            # Navigation using callback to avoid state modification error
            st.header("📋 Navigation")
            
            # Store current selection
            current_page = st.session_state.get('page', 'Dashboard')
            
            pages = [
                "Dashboard",
                "Upload Resumes",
                "Bulk Upload",
                "Job Description",
                "Rankings",
                "Send Emails",
                "Interview Questions",
                "Analytics",
                "History",
                "Search"
            ]
            
            # Use radio without modifying session_state in callback
            selected_page = st.radio(
                "Go to:",
                pages,
                index=pages.index(current_page) if current_page in pages else 0
            )
            
            # Update page if changed
            if selected_page != current_page:
                st.session_state.page = selected_page
                st.rerun()
            
            st.markdown("---")
            
            # Statistics
            st.header("📊 Statistics")
            st.metric("Resumes Uploaded", len(st.session_state.parsed_resumes))
            
            if st.session_state.ranked_candidates:
                excellent = sum(1 for c in st.session_state.ranked_candidates 
                              if c['overall_score'] >= 80)
                st.metric("Excellent Matches", excellent)
            
            st.markdown("---")
            
            # Clear data button with callback
            def clear_all_data():
                st.session_state.parsed_resumes = []
                st.session_state.ranked_candidates = []
                st.session_state.job_description = ""
                st.session_state.current_job_id = None
                st.session_state.current_job_title = ""
            
            if st.button("🗑️ Clear All Data", use_container_width=True, on_click=clear_all_data):
                st.success("Data cleared!")
                st.rerun()
    
    # ==================== NEW PAGES ====================
    
    def page_bulk_upload(self):
        """Bulk resume upload page"""
        try:
            render_bulk_upload_ui(self.parser, self.db if self.db_available else None)
        except Exception as e:
            st.error(f"Error in bulk upload: {str(e)}")
            st.info("Please check your parser configuration.")

    def page_send_emails(self):
        """Email sending page"""
        if not st.session_state.ranked_candidates:
            st.warning("⚠️ No candidates to email. Please rank candidates first!")
            if st.button("Go to Rankings"):
                self.navigate_to('Rankings')
            return
        
        try:
            render_email_panel(
                st.session_state.ranked_candidates,
                st.session_state.get('current_job_title', 'Open Position')
            )
        except Exception as e:
            st.error(f"Email functionality error: {str(e)}")
            st.info("""
            **Email Setup Required:**
            1. Enable 2-Factor Authentication on your Gmail account
            2. Generate an App Password: https://myaccount.google.com/apppasswords
            3. Update your email configuration with the 16-character app password
            
            **Note:** Regular Gmail passwords won't work due to security restrictions.
            """)

    def page_interview_questions(self):
        """Interview questions page"""
        st.header("🎯 Generate Interview Questions")
        
        if not st.session_state.ranked_candidates:
            st.warning("⚠️ No candidates available. Please rank candidates first!")
            if st.button("Go to Rankings"):
                self.navigate_to('Rankings')
            return
        
        # Select candidate
        st.markdown("### Select Candidate")
        
        candidate_names = [c['name'] for c in st.session_state.ranked_candidates]
        selected_name = st.selectbox("Choose candidate:", candidate_names)
        
        if selected_name:
            selected_candidate = next(
                c for c in st.session_state.ranked_candidates 
                if c['name'] == selected_name
            )
            
            job_title = st.text_input(
                "Job Title",
                value=st.session_state.get('current_job_title', 'Software Engineer')
            )
            
            if st.button("Generate Questions", type="primary"):
                try:
                    render_question_generator_ui(selected_candidate, job_title)
                except Exception as e:
                    st.error(f"Question generation error: {str(e)}")

    def page_dashboard(self):
        """Analytics dashboard"""
        st.header("📊 Dashboard")
        
        # Get stats from database if available, otherwise from session
        if self.db_available:
            try:
                stats = self.db.get_analytics_summary()
            except Exception as e:
                st.warning(f"Could not load database stats: {str(e)}")
                stats = {
                    'total_resumes': len(st.session_state.parsed_resumes),
                    'total_jobs': 0,
                    'total_rankings': len(st.session_state.ranked_candidates)
                }
        else:
            stats = {
                'total_resumes': len(st.session_state.parsed_resumes),
                'total_jobs': 0,
                'total_rankings': len(st.session_state.ranked_candidates)
            }
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📄 Total Resumes", stats.get('total_resumes', 0))
        
        with col2:
            st.metric("💼 Job Postings", stats.get('total_jobs', 0))
        
        with col3:
            st.metric("🎯 Rankings Done", stats.get('total_rankings', 0))
        
        st.markdown("---")
        st.markdown("### 📋 Recent Jobs")
        
        if self.db_available:
            try:
                jobs = self.db.get_all_job_postings()
                
                if jobs:
                    for job in jobs[:5]:
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.write(f"**{job['title']}**")
                        with col_b:
                            st.write(job['created_at'][:10])
                else:
                    st.info("No jobs yet! Go to Job Description tab to create one.")
            except Exception as e:
                st.warning(f"Database error: {str(e)}")
                st.info("Could not load job history. Database tables may need to be created.")
        else:
            st.info("Database not available. Job history requires database connection.")
    
    def page_history(self):
        """View past job postings and rankings"""
        st.header("📚 Ranking History")
        
        if not self.db_available:
            st.warning("⚠️ Database not available. History feature requires database connection.")
            st.info("Recent rankings are available in the Rankings tab.")
            if st.button("Go to Rankings"):
                self.navigate_to('Rankings')
            return
        
        try:
            jobs = self.db.get_all_job_postings()
        except Exception as e:
            st.error(f"Failed to load job history: {str(e)}")
            st.info("""
            **Database tables may be missing.** Please run this SQL to create them:
            
            ```sql
            CREATE TABLE IF NOT EXISTS public.job_postings (
                id SERIAL PRIMARY KEY,
                job_title VARCHAR(255) NOT NULL,
                job_description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ```
            """)
            return
        
        if not jobs:
            st.info("No history yet. Match some candidates first!")
            if st.button("Go to Job Description"):
                self.navigate_to('Job Description')
            return
        
        for job in jobs:
            with st.expander(f"📋 {job['title']} ({job['created_at'][:10]})"):
                st.markdown(f"**Job Description:**")
                st.text(job['description'][:300] + "...")
                
                try:
                    rankings = self.db.get_rankings_by_job(job['id'])
                except Exception as e:
                    st.warning(f"Could not load rankings: {str(e)}")
                    rankings = []
                
                if rankings:
                    st.markdown(f"**📊 {len(rankings)} Candidates Ranked**")
                    
                    sorted_rankings = sorted(rankings, 
                                           key=lambda x: x['overall_score'], 
                                           reverse=True)
                    
                    st.markdown("**Top 3:**")
                    for i, rank in enumerate(sorted_rankings[:3], 1):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{i}. Candidate #{i}")
                        with col2:
                            st.write(f"**{rank['overall_score']:.1f}%**")
                    
                    def load_results(job_id, rankings_data):
                        formatted_rankings = []
                        for idx, rank in enumerate(rankings_data, 1):
                            formatted_rankings.append({
                                'name': f"Candidate #{idx}",
                                'email': 'N/A',
                                'phone': 'N/A',
                                'overall_score': rank['overall_score'],
                                'skills_score': rank.get('skills_score', 0),
                                'experience_score': rank.get('experience_score', 0),
                                'education_score': rank.get('education_score', 0),
                                'total_experience': 0,
                                'matched_skills': rank.get('matched_skills', []),
                                'missing_skills': rank.get('missing_skills', []),
                                'explanation': rank.get('explanation', {})
                            })
                        st.session_state.ranked_candidates = formatted_rankings
                    
                    if st.button(f"📊 View Full Results", 
                               key=f"view_{job['id']}", 
                               use_container_width=True,
                               on_click=load_results,
                               args=(job['id'], sorted_rankings)):
                        st.success("Results loaded! Go to Rankings tab.")
                else:
                    st.info("No rankings for this job yet.")
    
    def page_search(self):
        """Search candidates by skills"""
        st.header("🔍 Search Candidates")
        
        if not self.db_available:
            st.warning("⚠️ Database not available. Search feature requires database connection.")
            st.info("You can view uploaded resumes in the 'Upload Resumes' tab.")
            if st.button("Go to Upload Resumes"):
                self.navigate_to('Upload Resumes')
            return
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_skill = st.text_input(
                "Enter skill to search",
                placeholder="e.g., Python, React, AWS, Machine Learning"
            )
        
        with col2:
            st.write("")
            st.write("")
            search_button = st.button("🔍 Search", use_container_width=True, type="primary")
        
        if search_button and search_skill:
            with st.spinner(f"Searching for '{search_skill}'..."):
                try:
                    results = self.db.search_candidates_by_skill(search_skill)
                except Exception as e:
                    st.error(f"Search failed: {str(e)}")
                    return
                
                if results:
                    st.success(f"Found {len(results)} candidates with '{search_skill}'")
                    
                    for resume in results:
                        data = resume['parsed_data']
                        name = data['contact'].get('name', 'Unknown')
                        
                        with st.expander(f"📄 {name}"):
                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                st.markdown("**Contact:**")
                                st.write(f"📧 {data['contact'].get('email', 'N/A')}")
                                st.write(f"📱 {data['contact'].get('phone', 'N/A')}")
                            
                            with col_b:
                                st.markdown("**Experience:**")
                                st.write(f"⏱️ {data.get('total_experience_years', 0)} years")
                                st.write(f"💼 {len(data.get('experience', []))} jobs")
                            
                            st.markdown("**Skills:**")
                            all_skills = []
                            for skills in data.get('skills', {}).values():
                                all_skills.extend(skills)
                            
                            if all_skills:
                                skills_text = ", ".join(all_skills[:15])
                                st.write(skills_text)
                                
                                if len(all_skills) > 15:
                                    st.caption(f"+{len(all_skills) - 15} more skills")
                            else:
                                st.write("No skills found")
                else:
                    st.warning(f"No candidates found with skill '{search_skill}'")
                    st.info("💡 Try searching for: Python, JavaScript, AWS, Machine Learning, React")
        
        elif search_button and not search_skill:
            st.error("Please enter a skill to search!")
    
    # ==================== EXISTING PAGES ====================
    
    def page_upload_resumes(self):
        """Resume upload and parsing page"""
        st.header("📤 Upload & Parse Resumes")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Upload Resume Files")
            st.markdown("Supported formats: **PDF, DOCX**")
            
            uploaded_files = st.file_uploader(
                "Choose resume files",
                type=['pdf', 'docx'],
                accept_multiple_files=True,
                help="Upload one or more resume files to parse"
            )
            
            if uploaded_files:
                if st.button("🔍 Parse All Resumes", type="primary", use_container_width=True):
                    self.parse_uploaded_files(uploaded_files)
        
        with col2:
            st.markdown("### Quick Stats")
            st.info(f"**Total Resumes:** {len(st.session_state.parsed_resumes)}")
            
            if st.session_state.parsed_resumes:
                avg_exp = sum(r.get('total_experience_years', 0) 
                            for r in st.session_state.parsed_resumes) / len(st.session_state.parsed_resumes)
                st.info(f"**Avg Experience:** {avg_exp:.1f} years")
        
        if st.session_state.parsed_resumes:
            st.markdown("---")
            st.markdown("### 📋 Parsed Resumes")
            self.display_parsed_resumes()
    
    def parse_uploaded_files(self, uploaded_files):
        """Parse uploaded resume files"""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        parsed_count = 0
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Parsing: {uploaded_file.name}")
            
            try:
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                resume_data = self.parser.parse_resume(temp_path)
                resume_data['filename'] = uploaded_file.name
                
                # Save to database if available
                if self.db_available:
                    try:
                        resume_id = self.db.save_resume(uploaded_file.name, resume_data)
                        resume_data['id'] = resume_id
                        self.db.log_action('resume_uploaded', {'filename': uploaded_file.name})
                    except Exception as e:
                        st.warning(f"Database save failed: {str(e)}")
                
                st.session_state.parsed_resumes.append(resume_data)
                parsed_count += 1
                
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
            except Exception as e:
                st.error(f"Failed to parse {uploaded_file.name}: {str(e)}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.empty()
        progress_bar.empty()
        
        st.success(f"✅ Successfully parsed {parsed_count}/{len(uploaded_files)} resumes!")
        st.rerun()
    
    def display_parsed_resumes(self):
        """Display list of parsed resumes"""
        for i, resume in enumerate(st.session_state.parsed_resumes):
            with st.expander(f"📄 {resume['contact'].get('name', 'Unknown')} - {resume.get('filename', '')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Contact Info**")
                    st.write(f"📧 {resume['contact'].get('email', 'N/A')}")
                    st.write(f"📱 {resume['contact'].get('phone', 'N/A')}")
                    st.write(f"💼 {resume['contact'].get('linkedin', 'N/A')}")
                
                with col2:
                    st.markdown("**Experience**")
                    st.write(f"⏱️ {resume.get('total_experience_years', 0)} years")
                    st.write(f"💼 {len(resume.get('experience', []))} jobs")
                    st.write(f"🎓 {len(resume.get('education', []))} degrees")
                
                with col3:
                    st.markdown("**Skills**")
                    total_skills = sum(len(v) for v in resume.get('skills', {}).values())
                    st.write(f"🛠️ {total_skills} skills")
                    
                    all_skills = []
                    for skills in resume.get('skills', {}).values():
                        all_skills.extend(skills)
                    if all_skills:
                        st.write(f"Top: {', '.join(all_skills[:3])}")
                
                def remove_resume(index):
                    st.session_state.parsed_resumes.pop(index)
                
                if st.button(f"🗑️ Remove", key=f"remove_{i}", on_click=remove_resume, args=(i,)):
                    st.rerun()
    
    def page_job_description(self):
        """Job description input page"""
        st.header("📝 Job Description")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Enter Job Requirements")
            
            job_description = st.text_area(
                "Paste the complete job description here:",
                value=st.session_state.job_description,
                height=400,
                placeholder="""Example:
Senior Python Developer

Requirements:
- 3-5 years of Python experience
- Machine Learning expertise
- AWS/Cloud experience
- Bachelor's in Computer Science

Must Have Skills:
- Python, TensorFlow, SQL, REST API

Nice to Have:
- Docker, Kubernetes, React
""",
                help="Include requirements, skills, experience, and responsibilities"
            )
            
            st.session_state.job_description = job_description
            
            col_btn1, col_btn2 = st.columns(2)
            
            def use_sample():
                st.session_state.job_description = self.get_sample_job_description()
            
            with col_btn1:
                if st.button("✨ Use Sample Job", use_container_width=True, on_click=use_sample):
                    st.rerun()
            
            with col_btn2:
                if st.button("🚀 Match Candidates", type="primary", use_container_width=True):
                    if not st.session_state.parsed_resumes:
                        st.error("Please upload resumes first!")
                    elif not job_description.strip():
                        st.error("Please enter a job description!")
                    else:
                        self.match_candidates(job_description)
        
        with col2:
            if job_description:
                st.markdown("### 🔍 Job Analysis")
                
                try:
                    job_data = self.job_parser.parse_job_description(job_description)
                    
                    st.info(f"**Position:** {job_data['title']}")
                    st.info(f"**Min Experience:** {job_data['min_experience']} years")
                    
                    if job_data['required_skills']:
                        with st.expander("Required Skills"):
                            for skill in job_data['required_skills'][:10]:
                                st.write(f"• {skill}")
                    
                    if job_data['preferred_skills']:
                        with st.expander("Preferred Skills"):
                            for skill in job_data['preferred_skills'][:10]:
                                st.write(f"• {skill}")
                except Exception as e:
                    st.warning(f"Job parsing error: {str(e)}")
    
    def match_candidates(self, job_description):
        """Match candidates with job description"""
        with st.spinner("🤖 AI is analyzing candidates..."):
            try:
                ranked = self.ranker.rank_candidates(
                    st.session_state.parsed_resumes,
                    job_description
                )
                st.session_state.ranked_candidates = ranked
                
                job_data = self.job_parser.parse_job_description(job_description)
                st.session_state.current_job_title = job_data['title']
                
                # Save to database if available
                if self.db_available:
                    try:
                        job_id = self.db.save_job_posting(
                            job_data['title'],
                            job_description,
                            job_data
                        )
                        st.session_state.current_job_id = job_id
                        
                        self.db.save_ranking(job_id, ranked)
                    except Exception as e:
                        st.warning(f"Could not save to database: {str(e)}")
                
                st.success(f"✅ Ranked {len(ranked)} candidates! Go to Rankings tab to view results.")
                
            except Exception as e:
                st.error(f"Matching failed: {str(e)}")
                st.info("Please check your ranking configuration and try again.")
    
    def page_rankings(self):
        """Display ranked candidates"""
        st.header("🏆 Candidate Rankings")
        
        if not st.session_state.ranked_candidates:
            st.warning("⚠️ No rankings yet! Please match candidates with a job description first.")
            if st.button("Go to Job Description"):
                self.navigate_to('Job Description')
            return
        
        self.display_ranking_metrics()
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_score = st.slider("Minimum Score", 0, 100, 0, 5)
        
        with col2:
            sort_by = st.selectbox("Sort By", ["Overall Score", "Skills Score", "Experience Score"])
        
        with col3:
            max_candidates = len(st.session_state.ranked_candidates)
            default_count = min(5, max_candidates)
            show_count = st.number_input("Show Top N", 1, max_candidates, default_count)
        
        filtered = [c for c in st.session_state.ranked_candidates if c['overall_score'] >= min_score]
        
        if sort_by == "Skills Score":
            filtered.sort(key=lambda x: x['skills_score'], reverse=True)
        elif sort_by == "Experience Score":
            filtered.sort(key=lambda x: x['experience_score'], reverse=True)
        
        filtered = filtered[:show_count]
        
        st.markdown(f"### Showing {len(filtered)} Candidates")
        
        for i, candidate in enumerate(filtered, 1):
            self.display_candidate_card(i, candidate)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Download Report (JSON)", use_container_width=True):
                self.download_json_report()
        
        with col2:
            if st.button("📊 Download Report (CSV)", use_container_width=True):
                self.download_csv_report()
    
    def display_ranking_metrics(self):
        """Display summary metrics for rankings"""
        col1, col2, col3, col4 = st.columns(4)
        
        candidates = st.session_state.ranked_candidates
        
        with col1:
            st.metric("Total Candidates", len(candidates))
        
        with col2:
            excellent = sum(1 for c in candidates if c['overall_score'] >= 80)
            st.metric("Excellent Match (80%+)", excellent)
        
        with col3:
            good = sum(1 for c in candidates if 60 <= c['overall_score'] < 80)
            st.metric("Good Match (60-79%)", good)
        
        with col4:
            if candidates:
                avg_score = sum(c['overall_score'] for c in candidates) / len(candidates)
                st.metric("Average Score", f"{avg_score:.1f}%")
    
    def display_candidate_card(self, rank, candidate):
        """Display individual candidate card"""
        score = candidate['overall_score']
        
        if score >= 80:
            score_class = "score-excellent"
            emoji = "🟢"
            status = "EXCELLENT MATCH"
        elif score >= 60:
            score_class = "score-good"
            emoji = "🟡"
            status = "GOOD MATCH"
        else:
            score_class = "score-moderate"
            emoji = "🟠"
            status = "MODERATE MATCH"
        
        with st.expander(f"{emoji} **RANK #{rank}: {candidate['name']}** - {score:.1f}% ({status})", expanded=(rank <= 3)):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**📧 Email:** {candidate['email']}")
                st.markdown(f"**📱 Phone:** {candidate['phone']}")
                st.markdown(f"**⏱️ Experience:** {candidate['total_experience']} years")
            
            with col2:
                st.markdown("**Overall Score**")
                st.markdown(f"<h1 class='{score_class}'>{score:.1f}%</h1>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 📊 Score Breakdown")
            
            scores_df = pd.DataFrame({
                'Category': ['Skills', 'Experience', 'Education'],
                'Score': [
                    candidate['skills_score'],
                    candidate['experience_score'],
                    candidate['education_score']
                ]
            })
            
            fig = px.bar(
                scores_df,
                x='Category',
                y='Score',
                color='Score',
                color_continuous_scale='RdYlGn',
                range_color=[0, 100]
            )
            fig.update_layout(height=250, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, key=f"score_chart_rank_{rank}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### ✅ Matched Skills")
                if candidate['matched_skills']:
                    for skill in candidate['matched_skills'][:10]:
                        st.markdown(f"✓ {skill}")
                    if len(candidate['matched_skills']) > 10:
                        st.markdown(f"*+{len(candidate['matched_skills']) - 10} more*")
                else:
                    st.markdown("*No exact skill matches*")
            
            with col2:
                st.markdown("### ❌ Missing Skills")
                if candidate['missing_skills']:
                    for skill in candidate['missing_skills'][:10]:
                        st.markdown(f"✗ {skill}")
                    if len(candidate['missing_skills']) > 10:
                        st.markdown(f"*+{len(candidate['missing_skills']) - 10} more*")
                else:
                    st.markdown("*All required skills present*")
            
            st.markdown("---")
            st.markdown("### 💡 Assessment")
            
            exp = candidate.get('explanation', {})
            if isinstance(exp, dict):
                st.info(exp.get('summary', 'No summary available'))
                
                if exp.get('strengths'):
                    st.markdown("**Strengths:**")
                    for strength in exp['strengths']:
                        st.markdown(f"• {strength}")
                
                if exp.get('weaknesses'):
                    st.markdown("**Weaknesses:**")
                    for weakness in exp['weaknesses']:
                        st.markdown(f"• {weakness}")
                
                if exp.get('recommendations'):
                    st.markdown("**Recommendation:**")
                    for rec in exp['recommendations']:
                        st.success(rec)

    def page_analytics(self):
        """Analytics and insights page"""
        st.header("📈 Analytics & Insights")
        
        if not st.session_state.ranked_candidates:
            st.warning("No data to analyze. Please rank candidates first!")
            if st.button("Go to Job Description"):
                self.navigate_to('Job Description')
            return
        
        candidates = st.session_state.ranked_candidates
        
        st.markdown("### Score Distribution")
        
        scores = [c['overall_score'] for c in candidates]
        fig = go.Figure(data=[go.Histogram(x=scores, nbinsx=10, marker_color='#667eea')])
        fig.update_layout(
            title="Candidate Score Distribution",
            xaxis_title="Overall Score",
            yaxis_title="Number of Candidates",
            height=350
        )
        st.plotly_chart(fig, use_container_width=True, key="score_distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Most Common Skills")
            all_matched_skills = []
            for c in candidates:
                all_matched_skills.extend(c.get('matched_skills', []))
            
            if all_matched_skills:
                skills_count = pd.Series(all_matched_skills).value_counts().head(10)
                fig = px.bar(
                    x=skills_count.values,
                    y=skills_count.index,
                    orientation='h',
                    labels={'x': 'Count', 'y': 'Skill'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True, key="common_skills")
            else:
                st.info("No matched skills data available")
        
        with col2:
            st.markdown("### Most Missing Skills")
            all_missing_skills = []
            for c in candidates:
                all_missing_skills.extend(c.get('missing_skills', []))
            
            if all_missing_skills:
                missing_count = pd.Series(all_missing_skills).value_counts().head(10)
                fig = px.bar(
                    x=missing_count.values,
                    y=missing_count.index,
                    orientation='h',
                    labels={'x': 'Count', 'y': 'Skill'},
                    color_discrete_sequence=['#ef4444']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True, key="missing_skills")
            else:
                st.info("No missing skills data available")
        
        st.markdown("### Experience vs Match Score")
        
        exp_data = pd.DataFrame({
            'Experience': [c.get('total_experience', 0) for c in candidates],
            'Score': [c['overall_score'] for c in candidates],
            'Name': [c['name'] for c in candidates]
        })
        
        fig = px.scatter(
            exp_data,
            x='Experience',
            y='Score',
            hover_data=['Name'],
            size=[10]*len(exp_data),
            color='Score',
            color_continuous_scale='RdYlGn'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True, key="exp_vs_score")
    
    def download_json_report(self):
        """Generate JSON report for download"""
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'total_candidates': len(st.session_state.ranked_candidates),
            'candidates': st.session_state.ranked_candidates
        }
        
        json_str = json.dumps(report_data, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"ranking_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    def download_csv_report(self):
        """Generate CSV report for download"""
        candidates = st.session_state.ranked_candidates
        
        csv_data = []
        for c in candidates:
            csv_data.append({
                'Name': c['name'],
                'Email': c['email'],
                'Phone': c['phone'],
                'Overall Score': c['overall_score'],
                'Skills Score': c['skills_score'],
                'Experience Score': c['experience_score'],
                'Education Score': c['education_score'],
                'Total Experience': c.get('total_experience', 0),
                'Matched Skills': ', '.join(c.get('matched_skills', [])[:5]),
                'Missing Skills': ', '.join(c.get('missing_skills', [])[:5])
            })
        
        df = pd.DataFrame(csv_data)
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="📊 Download CSV",
            data=csv,
            file_name=f"ranking_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    def get_sample_job_description(self):
        """Return sample job description"""
        return """Senior Python Developer

We are seeking an experienced Python Developer to join our AI/ML team.

Requirements:
- 3-5 years of professional Python development experience
- Strong experience with Machine Learning frameworks (TensorFlow, PyTorch)
- Experience with cloud platforms (AWS preferred)
- Bachelor's degree in Computer Science or related field

Must Have Skills:
- Python (expert level)
- Machine Learning & Deep Learning
- TensorFlow or PyTorch
- SQL databases (MySQL, PostgreSQL)
- REST API development
- Git version control

Nice to Have:
- AWS/Azure/GCP experience
- Docker and Kubernetes
- React or frontend experience
- Experience with NLP projects
- CI/CD pipelines

Responsibilities:
- Develop and deploy machine learning models
- Build scalable ML pipelines
- Collaborate with data scientists and engineers
- Write clean, maintainable, well-documented code
- Participate in code reviews
"""


# Main application entry point
if __name__ == "__main__":
    app = ResumeShortlistingApp()

    app.run()



