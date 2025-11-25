"""
Interview Questions Generator
Generates customized interview questions based on candidate profile and job role
"""

import streamlit as st
import json
from datetime import datetime


def generate_questions_for_candidate(candidate_data, job_title, num_questions=10):
    """
    Generate interview questions based on candidate profile
    
    Args:
        candidate_data: Dictionary containing candidate information
        job_title: Job position title
        num_questions: Number of questions to generate
    
    Returns:
        dict: Generated questions categorized by type
    """
    
    # Extract candidate information
    matched_skills = candidate_data.get('matched_skills', [])
    missing_skills = candidate_data.get('missing_skills', [])
    experience = candidate_data.get('total_experience', 0)
    
    questions = {
        'technical': [],
        'behavioral': [],
        'situational': [],
        'skills_based': []
    }
    
    # Technical Questions based on matched skills
    if matched_skills:
        for skill in matched_skills[:5]:
            questions['technical'].append(
                f"Can you explain your experience with {skill} and describe a challenging project where you used it?"
            )
            questions['technical'].append(
                f"What are the best practices you follow when working with {skill}?"
            )
    
    # Questions about missing skills
    if missing_skills:
        for skill in missing_skills[:3]:
            questions['technical'].append(
                f"Although you don't have {skill} listed, are you familiar with it? How quickly could you learn it?"
            )
    
    # Behavioral Questions
    questions['behavioral'] = [
        f"Tell me about a time when you had to learn a new technology quickly for a project.",
        f"Describe a situation where you disagreed with a team member. How did you handle it?",
        f"Can you share an example of a project that didn't go as planned? What did you learn?",
        f"Tell me about the most challenging technical problem you've solved in your career.",
        f"How do you stay updated with the latest trends and technologies in your field?"
    ]
    
    # Situational Questions
    questions['situational'] = [
        f"If you were assigned to a project with tight deadlines and limited resources, how would you approach it?",
        f"Suppose you discover a critical bug in production right before a major release. What would you do?",
        f"How would you handle a situation where stakeholders keep changing requirements mid-project?",
        f"If you had to explain a complex technical concept to a non-technical stakeholder, how would you do it?",
        f"What would you do if you disagreed with your manager's technical decision?"
    ]
    
    # Skills-based Questions
    if matched_skills:
        primary_skills = matched_skills[:3]
        questions['skills_based'] = [
            f"Rate your proficiency in {skill} on a scale of 1-10 and explain why." 
            for skill in primary_skills
        ]
        questions['skills_based'].append(
            f"Which of these skills ({', '.join(primary_skills)}) do you enjoy working with the most and why?"
        )
    
    # Experience-based Questions
    if experience > 0:
        questions['behavioral'].append(
            f"With {experience} years of experience, what do you think sets you apart from other candidates?"
        )
        questions['behavioral'].append(
            f"Looking back at your {experience} years in the field, what would you do differently?"
        )
    
    # Job-specific Questions
    questions['situational'].append(
        f"Why are you interested in this {job_title} position specifically?"
    )
    questions['situational'].append(
        f"Where do you see yourself in the next 3-5 years in your career as a {job_title}?"
    )
    
    return questions


def render_question_generator_ui(candidate_data, job_title):
    """
    Render the interview questions generator UI
    
    Args:
        candidate_data: Dictionary containing candidate information
        job_title: Job position title
    """
    
    st.markdown("---")
    
    # Generate Questions automatically (no button needed here)
    questions = generate_questions_for_candidate(candidate_data, job_title, num_questions=10)
    
    # Display Questions by Category
    st.markdown("### 📋 Generated Interview Questions")
    
    # Technical Questions
    with st.expander("💻 Technical Questions", expanded=True):
        st.markdown(f"*Based on candidate's skills: {', '.join(candidate_data.get('matched_skills', [])[:5])}*")
        st.markdown("")
        
        for i, question in enumerate(questions['technical'], 1):
            st.markdown(f"**{i}.** {question}")
            st.markdown("")
    
    # Behavioral Questions
    with st.expander("🧠 Behavioral Questions", expanded=True):
        st.markdown("*Assess soft skills, problem-solving, and past experiences*")
        st.markdown("")
        
        for i, question in enumerate(questions['behavioral'], 1):
            st.markdown(f"**{i}.** {question}")
            st.markdown("")
    
    # Situational Questions
    with st.expander("🎭 Situational Questions", expanded=True):
        st.markdown("*Evaluate decision-making and problem-solving approach*")
        st.markdown("")
        
        for i, question in enumerate(questions['situational'], 1):
            st.markdown(f"**{i}.** {question}")
            st.markdown("")
    
    # Skills-based Questions
    if questions['skills_based']:
        with st.expander("🛠️ Skills Assessment Questions"):
            st.markdown("*Deep dive into specific technical skills*")
            st.markdown("")
            
            for i, question in enumerate(questions['skills_based'], 1):
                st.markdown(f"**{i}.** {question}")
                st.markdown("")
    
    st.markdown("---")
    
    # Additional Suggestions
    st.markdown("### 💡 Interview Tips")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Strengths to Explore:**")
        matched_skills = candidate_data.get('matched_skills', [])
        if matched_skills:
            for skill in matched_skills[:5]:
                st.markdown(f"• {skill}")
        else:
            st.markdown("*No specific skills identified*")
    
    with col2:
        st.markdown("**⚠️ Areas to Assess:**")
        missing_skills = candidate_data.get('missing_skills', [])
        if missing_skills:
            for skill in missing_skills[:5]:
                st.markdown(f"• {skill}")
        else:
            st.markdown("*No gaps identified*")
    
    # Download Questions
    st.markdown("---")
    st.markdown("### 📥 Export Questions")
    
    col1, col2 = st.columns(2)
    
    # Prepare download data
    all_questions = []
    for category, q_list in questions.items():
        all_questions.append(f"\n{'='*60}")
        all_questions.append(f"{category.upper().replace('_', ' ')} QUESTIONS")
        all_questions.append(f"{'='*60}\n")
        
        for i, q in enumerate(q_list, 1):
            all_questions.append(f"{i}. {q}\n")
    
    download_text = f"""
INTERVIEW QUESTIONS FOR {candidate_data.get('name', 'Candidate')}
Position: {job_title}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Overall Score: {candidate_data.get('overall_score', 0):.1f}%

{''.join(all_questions)}

---
Candidate Summary:
- Email: {candidate_data.get('email', 'N/A')}
- Phone: {candidate_data.get('phone', 'N/A')}
- Experience: {candidate_data.get('total_experience', 0)} years
- Matched Skills: {', '.join(candidate_data.get('matched_skills', [])[:10])}
- Missing Skills: {', '.join(candidate_data.get('missing_skills', [])[:10])}
"""
    
    with col1:
        st.download_button(
            label="📄 Download as Text",
            data=download_text,
            file_name=f"interview_questions_{candidate_data.get('name', 'candidate').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col2:
        # JSON format
        json_data = {
            'candidate': {
                'name': candidate_data.get('name', 'Unknown'),
                'email': candidate_data.get('email', 'N/A'),
                'score': candidate_data.get('overall_score', 0),
                'experience': candidate_data.get('total_experience', 0)
            },
            'position': job_title,
            'generated_at': datetime.now().isoformat(),
            'questions': questions
        }
        
        st.download_button(
            label="📋 Download as JSON",
            data=json.dumps(json_data, indent=2),
            file_name=f"interview_questions_{candidate_data.get('name', 'candidate').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )


def get_general_questions(job_title):
    """
    Get general interview questions for a position
    
    Args:
        job_title: Job position title
    
    Returns:
        list: General interview questions
    """
    return [
        f"Why are you interested in the {job_title} position?",
        "What are your greatest strengths and weaknesses?",
        "Where do you see yourself in 5 years?",
        "Why should we hire you for this position?",
        "What is your expected salary range?",
        "When can you start?",
        "Do you have any questions for us?",
        "Tell me about yourself and your background.",
        "What motivates you in your work?",
        "How do you handle pressure and tight deadlines?"
    ]


def render_standalone_question_generator():
    """
    Render a standalone question generator (without candidate data)
    """
    st.header("🎯 Interview Question Generator")
    
    st.markdown("Generate interview questions for any position")
    
    job_title = st.text_input(
        "Job Title",
        placeholder="e.g., Senior Python Developer, Data Scientist, Product Manager"
    )
    
    skills = st.text_area(
        "Required Skills (one per line)",
        placeholder="Python\nMachine Learning\nAWS\nDocker",
        height=150
    )
    
    experience_level = st.selectbox(
        "Experience Level",
        ["Entry Level (0-2 years)", "Mid Level (3-5 years)", "Senior Level (6+ years)"]
    )
    
    if st.button("Generate Questions", type="primary"):
        if not job_title:
            st.error("Please enter a job title")
            return
        
        # Parse skills
        skill_list = [s.strip() for s in skills.split('\n') if s.strip()]
        
        # Create mock candidate data
        mock_candidate = {
            'name': 'General Candidate',
            'matched_skills': skill_list,
            'missing_skills': [],
            'total_experience': 3,
            'overall_score': 75
        }
        
        render_question_generator_ui(mock_candidate, job_title)


# For testing
if __name__ == "__main__":
    st.set_page_config(page_title="Interview Questions Generator", layout="wide")
    
    # Test with sample data
    sample_candidate = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '+1234567890',
        'overall_score': 85.5,
        'total_experience': 5,
        'matched_skills': ['Python', 'Machine Learning', 'TensorFlow', 'SQL', 'AWS'],
        'missing_skills': ['Docker', 'Kubernetes', 'React']
    }
    
    render_question_generator_ui(sample_candidate, "Senior Python Developer")