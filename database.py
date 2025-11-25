"""
Database Manager for Supabase
Handles all database operations with proper error handling
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import json


class SupabaseManager:
    """Manages all Supabase database operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            self.client: Client = create_client(url, key)
        except KeyError as e:
            raise ValueError(f"Missing Supabase configuration: {e}")
        except Exception as e:
            raise ValueError(f"Failed to connect to Supabase: {e}")
    
    # ==================== RESUME OPERATIONS ====================
    
    def save_resume(self, filename, parsed_data):
        """
        Save parsed resume to database
        
        Args:
            filename: Name of the resume file
            parsed_data: Dictionary of parsed resume data
        
        Returns:
            int: Resume ID
        """
        try:
            data = {
                'filename': filename,
                'parsed_data': parsed_data,
                'upload_date': datetime.now().isoformat()
            }
            
            response = self.client.table('resumes').insert(data).execute()
            
            if response.data:
                return response.data[0]['id']
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            st.error(f"Failed to save resume: {str(e)}")
            return None
    
    def get_all_resumes(self):
        """Get all resumes from database"""
        try:
            response = self.client.table('resumes').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            st.warning(f"Could not fetch resumes: {str(e)}")
            return []
    
    def search_candidates_by_skill(self, skill):
        """
        Search candidates by skill
        
        Args:
            skill: Skill to search for
        
        Returns:
            list: Matching resumes
        """
        try:
            # Search in parsed_data JSONB field
            response = self.client.table('resumes').select('*').execute()
            
            # Filter results by skill (case-insensitive)
            results = []
            for resume in response.data:
                parsed_data = resume.get('parsed_data', {})
                
                # Search in skills dictionary
                skills_dict = parsed_data.get('skills', {})
                all_skills = []
                
                for skill_list in skills_dict.values():
                    if isinstance(skill_list, list):
                        all_skills.extend(skill_list)
                
                # Check if skill matches
                if any(skill.lower() in s.lower() for s in all_skills):
                    results.append(resume)
            
            return results
            
        except Exception as e:
            st.warning(f"Search failed: {str(e)}")
            return []
    
    # ==================== JOB POSTING OPERATIONS ====================
    
    def save_job_posting(self, title, description, job_data):
        """
        Save job posting to database
        
        Args:
            title: Job title
            description: Job description text
            job_data: Parsed job data dictionary
        
        Returns:
            int: Job posting ID
        """
        try:
            data = {
                'job_title': title,
                'job_description': description,  # Changed from 'description' to 'job_description'
                'required_skills': job_data.get('required_skills', []),
                'preferred_skills': job_data.get('preferred_skills', []),
                'min_experience': job_data.get('min_experience', 0),
                'job_data': job_data,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            response = self.client.table('job_postings').insert(data).execute()
            
            if response.data:
                return response.data[0]['id']
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            st.error(f"Failed to save job posting: {str(e)}")
            return None
    
    def get_all_job_postings(self):
        """Get all job postings from database"""
        try:
            response = self.client.table('job_postings').select('*').order('created_at', desc=True).execute()
            
            # Format the response to match expected structure
            jobs = []
            for job in response.data:
                jobs.append({
                    'id': job['id'],
                    'title': job.get('job_title', 'Unknown'),
                    'description': job.get('job_description', ''),  # Map to 'description'
                    'created_at': job.get('created_at', ''),
                    'required_skills': job.get('required_skills', []),
                    'preferred_skills': job.get('preferred_skills', [])
                })
            
            return jobs
            
        except Exception as e:
            st.warning(f"Could not fetch job postings: {str(e)}")
            return []
    
    def get_job_by_id(self, job_id):
        """Get a specific job posting by ID"""
        try:
            response = self.client.table('job_postings').select('*').eq('id', job_id).execute()
            
            if response.data:
                job = response.data[0]
                return {
                    'id': job['id'],
                    'title': job.get('job_title', 'Unknown'),
                    'description': job.get('job_description', ''),
                    'created_at': job.get('created_at', ''),
                    'required_skills': job.get('required_skills', []),
                    'preferred_skills': job.get('preferred_skills', [])
                }
            return None
            
        except Exception as e:
            st.warning(f"Could not fetch job: {str(e)}")
            return None
    
    # ==================== RANKING OPERATIONS ====================
    
    def save_ranking(self, job_id, rankings):
        """
        Save candidate rankings to database
        
        Args:
            job_id: Job posting ID
            rankings: List of ranked candidates
        
        Returns:
            bool: Success status
        """
        try:
            records = []
            
            for i, candidate in enumerate(rankings, 1):
                record = {
                    'job_posting_id': job_id,
                    'candidate_name': candidate.get('name', 'Unknown'),
                    'candidate_email': candidate.get('email', ''),
                    'candidate_phone': candidate.get('phone', ''),
                    'overall_score': float(candidate.get('overall_score', 0)),
                    'skills_score': float(candidate.get('skills_score', 0)),
                    'experience_score': float(candidate.get('experience_score', 0)),
                    'education_score': float(candidate.get('education_score', 0)),
                    'ranking_position': i,
                    'matched_skills': candidate.get('matched_skills', []),
                    'missing_skills': candidate.get('missing_skills', []),
                    'total_experience': float(candidate.get('total_experience', 0)),
                    'explanation': candidate.get('explanation', {}),
                    'created_at': datetime.now().isoformat()  # Changed from 'ranked_at' to 'created_at'
                }
                records.append(record)
            
            # Delete old rankings for this job
            self.client.table('rankings').delete().eq('job_posting_id', job_id).execute()
            
            # Insert new rankings
            response = self.client.table('rankings').insert(records).execute()
            
            return True
            
        except Exception as e:
            st.error(f"Failed to save rankings: {str(e)}")
            return False
    
    def get_rankings_by_job(self, job_id):
        """Get all rankings for a specific job"""
        try:
            response = self.client.table('rankings').select('*').eq('job_posting_id', job_id).order('overall_score', desc=True).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            st.warning(f"Could not fetch rankings: {str(e)}")
            return []
    
    def get_all_rankings(self):
        """Get all rankings from database"""
        try:
            response = self.client.table('rankings').select('*').order('created_at', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            st.warning(f"Could not fetch rankings: {str(e)}")
            return []
    
    # ==================== ANALYTICS ====================
    
    def get_analytics_summary(self):
        """
        Get summary analytics
        
        Returns:
            dict: Analytics data
        """
        try:
            # Get counts
            resumes_response = self.client.table('resumes').select('id', count='exact').execute()
            jobs_response = self.client.table('job_postings').select('id', count='exact').execute()
            rankings_response = self.client.table('rankings').select('id', count='exact').execute()
            
            # Get average score
            rankings_data = self.client.table('rankings').select('overall_score').execute()
            
            avg_score = 0
            if rankings_data.data:
                scores = [r['overall_score'] for r in rankings_data.data]
                avg_score = sum(scores) / len(scores) if scores else 0
            
            return {
                'total_resumes': resumes_response.count if resumes_response.count else 0,
                'total_jobs': jobs_response.count if jobs_response.count else 0,
                'total_rankings': rankings_response.count if rankings_response.count else 0,
                'avg_score': round(avg_score, 2)
            }
            
        except Exception as e:
            st.warning(f"Could not fetch analytics: {str(e)}")
            return {
                'total_resumes': 0,
                'total_jobs': 0,
                'total_rankings': 0,
                'avg_score': 0
            }
    
    # ==================== ACTIVITY LOGS ====================
    
    def log_action(self, action_type, details=None):
        """
        Log user action
        
        Args:
            action_type: Type of action (e.g., 'resume_uploaded')
            details: Additional details dictionary
        """
        try:
            data = {
                'action_type': action_type,
                'details': details or {},
                'created_at': datetime.now().isoformat()
            }
            
            self.client.table('activity_logs').insert(data).execute()
            
        except Exception as e:
            # Don't show error to user for logging failures
            print(f"Logging failed: {str(e)}")
    
    def get_recent_activities(self, limit=10):
        """Get recent activity logs"""
        try:
            response = self.client.table('activity_logs').select('*').order('created_at', desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            return []
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def test_connection(self):
        """
        Test database connection
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Try a simple query
            response = self.client.table('resumes').select('id').limit(1).execute()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def get_table_info(self, table_name):
        """Get information about a table structure"""
        try:
            response = self.client.table(table_name).select('*').limit(1).execute()
            if response.data:
                return list(response.data[0].keys())
            return []
        except Exception as e:
            st.error(f"Could not get table info: {str(e)}")
            return []


# Helper function for testing
def test_database_connection():
    """Test the database connection and display results"""
    st.write("Testing database connection...")
    
    try:
        db = SupabaseManager()
        success, message = db.test_connection()
        
        if success:
            st.success(f"✅ {message}")
            
            # Show table structures
            st.write("**Table Structures:**")
            for table in ['resumes', 'job_postings', 'rankings']:
                cols = db.get_table_info(table)
                if cols:
                    st.write(f"- {table}: {', '.join(cols)}")
        else:
            st.error(f"❌ {message}")
            
    except Exception as e:
        st.error(f"❌ Database error: {str(e)}")


if __name__ == "__main__":
    test_database_connection()