"""
AI Resume Shortlisting - Web Interface using Streamlit
Beautiful, interactive dashboard for resume screening and ranking
"""

import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Import your backend logic
from resume_parser import ResumeParser
from job_resume_matcher import CandidateRanker, JobDescriptionParser


# -------------------- PAGE CONFIGURATION --------------------
st.set_page_config(
    page_title="AI Resume Shortlisting System",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- CUSTOM STYLING --------------------
st.markdown("""
    <style>
    .main { padding: 0rem 1rem; }
    .stAlert { margin-top: 1rem; }
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
    .score-excellent { color: #10b981; font-weight: bold; }
    .score-good { color: #f59e0b; font-weight: bold; }
    .score-moderate { color: #ef4444; font-weight: bold; }
    h1 { color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)


# -------------------- MAIN APPLICATION --------------------
class ResumeShortlistingApp:
    """Main application class for AI Resume Shortlisting"""

    def __init__(self):
        self.parser = ResumeParser()
        self.ranker = CandidateRanker()
        self.job_parser = JobDescriptionParser()

        # Initialize session state
        for key, default in {
            "parsed_resumes": [],
            "ranked_candidates": [],
            "job_description": "",
            "current_page": "Upload Resumes",
        }.items():
            if key not in st.session_state:
                st.session_state[key] = default

    # -------------------- MAIN RUN --------------------
    def run(self):
        st.title("🎯 AI Resume Shortlisting System")
        st.markdown("**Intelligent Resume Screening powered by Machine Learning**")
        st.markdown("---")

        self.render_sidebar()
        page = st.session_state["current_page"]

        if page == "Upload Resumes":
            self.page_upload_resumes()
        elif page == "Job Description":
            self.page_job_description()
        elif page == "Rankings":
            self.page_rankings()
        elif page == "Analytics":
            self.page_analytics()

    # -------------------- SIDEBAR --------------------
    def render_sidebar(self):
        with st.sidebar:
            st.image(
                "https://via.placeholder.com/200x80/667eea/ffffff?text=AI+Recruiter",
                use_container_width=True,
            )
            st.markdown("---")

            st.header("📋 Navigation")
            choice = st.radio(
                "Go to:",
                ["Upload Resumes", "Job Description", "Rankings", "Analytics"],
                key="sidebar_nav",
            )
            st.session_state["current_page"] = choice

            st.markdown("---")
            st.header("📊 Statistics")
            st.metric("Resumes Uploaded", len(st.session_state.parsed_resumes))
            if st.session_state.ranked_candidates:
                excellent = sum(
                    1 for c in st.session_state.ranked_candidates if c["overall_score"] >= 80
                )
                st.metric("Excellent Matches", excellent)

            st.markdown("---")
            if st.button("🗑️ Clear All Data", use_container_width=True):
                for key in ["parsed_resumes", "ranked_candidates", "job_description"]:
                    st.session_state[key] = []
                st.success("All data cleared successfully!")
                st.rerun()

    # -------------------- PAGE: UPLOAD --------------------
    def page_upload_resumes(self):
        st.header("📤 Upload & Parse Resumes")
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("### Upload Resume Files (PDF/DOCX)")
            uploaded_files = st.file_uploader(
                "Choose resume files",
                type=["pdf", "docx"],
                accept_multiple_files=True,
                help="Upload one or more resume files",
            )

            if uploaded_files and st.button("🔍 Parse All Resumes", type="primary"):
                self.parse_uploaded_files(uploaded_files)

        with col2:
            st.markdown("### Quick Stats")
            st.info(f"**Total Resumes:** {len(st.session_state.parsed_resumes)}")
            if st.session_state.parsed_resumes:
                avg_exp = sum(
                    r.get("total_experience_years", 0)
                    for r in st.session_state.parsed_resumes
                ) / len(st.session_state.parsed_resumes)
                st.info(f"**Avg Experience:** {avg_exp:.1f} years")

        if st.session_state.parsed_resumes:
            st.markdown("---")
            st.subheader("📋 Parsed Resumes")
            self.display_parsed_resumes()

    def parse_uploaded_files(self, uploaded_files):
        progress = st.progress(0)
        status = st.empty()
        parsed_count = 0

        for i, file in enumerate(uploaded_files):
            status.text(f"Parsing: {file.name}")
            try:
                temp_path = f"temp_{file.name}"
                with open(temp_path, "wb") as f:
                    f.write(file.getbuffer())

                data = self.parser.parse_resume(temp_path)
                data["filename"] = file.name
                st.session_state.parsed_resumes.append(data)
                parsed_count += 1
                os.remove(temp_path)
            except Exception as e:
                st.error(f"❌ Failed to parse {file.name}: {e}")

            progress.progress(int((i + 1) / len(uploaded_files) * 100))

        status.empty()
        progress.empty()
        st.success(f"✅ Parsed {parsed_count}/{len(uploaded_files)} resumes!")
        st.rerun()

    def display_parsed_resumes(self):
        for i, resume in enumerate(st.session_state.parsed_resumes):
            name = resume["contact"].get("name", "Unknown")
            with st.expander(f"📄 {name} ({resume.get('filename', '')})"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write("**📞 Contact Info**")
                    st.write(f"📧 {resume['contact'].get('email', 'N/A')}")
                    st.write(f"📱 {resume['contact'].get('phone', 'N/A')}")

                with col2:
                    st.write("**Experience**")
                    st.write(f"⏱️ {resume.get('total_experience_years', 0)} years")

                with col3:
                    st.write("**Skills**")
                    all_skills = sum(len(v) for v in resume.get("skills", {}).values())
                    st.write(f"🛠️ {all_skills} skills")

                if st.button("🗑️ Remove", key=f"remove_{i}"):
                    st.session_state.parsed_resumes.pop(i)
                    st.rerun()

    # -------------------- PAGE: JOB DESCRIPTION --------------------
    def page_job_description(self):
        st.header("📝 Job Description")
        col1, col2 = st.columns([2, 1])

        with col1:
            job_desc = st.text_area(
                "Paste complete job description:",
                value=st.session_state.job_description,
                height=400,
                placeholder="Paste or write the JD here...",
            )
            st.session_state.job_description = job_desc

            colb1, colb2 = st.columns(2)
            with colb1:
                if st.button("✨ Use Sample Job"):
                    st.session_state.job_description = self.get_sample_job_description()
                    st.rerun()

            with colb2:
                if st.button("🚀 Match Candidates", type="primary"):
                    if not st.session_state.parsed_resumes:
                        st.error("Please upload resumes first.")
                    elif not job_desc.strip():
                        st.error("Please enter a job description.")
                    else:
                        self.match_candidates(job_desc)

        with col2:
            if job_desc.strip():
                st.subheader("🔍 Job Analysis")
                job_data = self.job_parser.parse_job_description(job_desc)
                st.info(f"**Position:** {job_data['title']}")
                st.info(f"**Min Experience:** {job_data['min_experience']} years")

    # -------------------- MATCHING LOGIC --------------------
    def match_candidates(self, job_description):
        with st.spinner("🤖 Matching candidates..."):
            try:
                ranked = self.ranker.rank_candidates(
                    st.session_state.parsed_resumes, job_description
                )
                st.session_state.ranked_candidates = ranked
                st.success(f"✅ Ranked {len(ranked)} candidates!")
                st.session_state["current_page"] = "Rankings"
                st.rerun()
            except Exception as e:
                st.error(f"Matching failed: {e}")

    # -------------------- PAGE: RANKINGS --------------------
    def page_rankings(self):
        st.header("🏆 Candidate Rankings")
        if not st.session_state.ranked_candidates:
            st.warning("No rankings yet. Please match candidates first.")
            return

        self.display_ranking_metrics()
        st.markdown("---")

        candidates = st.session_state.ranked_candidates
        min_score = st.slider("Minimum Score", 0, 100, 0)
        sort_by = st.selectbox("Sort By", ["Overall", "Skills", "Experience"])
        show_count = st.number_input(
            "Show Top N", min_value=1, max_value=len(candidates), value=min(10, len(candidates))
        )

        filtered = [c for c in candidates if c["overall_score"] >= min_score]
        if sort_by == "Skills":
            filtered.sort(key=lambda x: x["skills_score"], reverse=True)
        elif sort_by == "Experience":
            filtered.sort(key=lambda x: x["experience_score"], reverse=True)
        filtered = filtered[:show_count]

        for i, c in enumerate(filtered, 1):
            self.display_candidate_card(i, c)

    def display_ranking_metrics(self):
        cands = st.session_state.ranked_candidates
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Candidates", len(cands))
        col2.metric("Excellent (80%+)", sum(1 for c in cands if c["overall_score"] >= 80))
        col3.metric("Good (60–79%)", sum(1 for c in cands if 60 <= c["overall_score"] < 80))
        avg = sum(c["overall_score"] for c in cands) / len(cands)
        col4.metric("Avg Score", f"{avg:.1f}%")

    def display_candidate_card(self, rank, c):
        score = c["overall_score"]
        color_class = (
            "score-excellent" if score >= 80 else "score-good" if score >= 60 else "score-moderate"
        )
        with st.expander(f"#{rank}: {c['name']} – {score:.1f}%", expanded=rank <= 3):
            st.markdown(f"<h3 class='{color_class}'>{score:.1f}% Match</h3>", unsafe_allow_html=True)
            st.write(f"**Email:** {c['email']}")
            st.write(f"**Experience:** {c['total_experience']} years")

    # -------------------- PAGE: ANALYTICS --------------------
    def page_analytics(self):
        st.header("📈 Analytics & Insights")
        if not st.session_state.ranked_candidates:
            st.warning("No data available. Please rank candidates first.")
            return

        cands = st.session_state.ranked_candidates
        scores = [c["overall_score"] for c in cands]
        fig = go.Figure(data=[go.Histogram(x=scores, nbinsx=10, marker_color="#667eea")])
        fig.update_layout(title="Score Distribution", height=350)
        st.plotly_chart(fig, use_container_width=True)

    # -------------------- SAMPLE JOB --------------------
    def get_sample_job_description(self):
        return """Senior Python Developer
Requirements:
- 3-5 years Python
- ML frameworks (TensorFlow, PyTorch)
- Cloud (AWS)
- Degree in CS
Skills: Python, TensorFlow, SQL, REST API, Docker, React
"""


# -------------------- ENTRY POINT --------------------
if __name__ == "__main__":
    ResumeShortlistingApp().run()
