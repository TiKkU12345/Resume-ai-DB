"""
Database Manager for Supabase
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime
from app_config import get_secret


class SupabaseManager:
    """Manages all Supabase database operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        try:
            url = get_secret("SUPABASE_URL")
            key = get_secret("SUPABASE_KEY")
            
            if not url or not key:
                raise ValueError("Missing Supabase configuration")
            
            self.client: Client = create_client(url, key)
        except Exception as e:
            raise ValueError(f"Failed to connect to Supabase: {e}")
    
    def save_resume(self, filename, parsed_data):
        """Save parsed resume to database"""
        try:
            data = {
                'filename': filename,
                'parsed_data': parsed_data,
                'upload_date': datetime.now().isoformat()
            }
            
            response = self.client.table('resumes').insert(data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            st.error(f"Failed to save resume: {str(e)}")
            return None
    
    def get_all_resumes(self):
        """Get all resumes"""
        try:
            response = self.client.table('resumes').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            st.warning(f"Could not fetch resumes: {str(e)}")
            return []
    
    def save_job_posting(self, title, description, job_data):
        """Save job posting"""
        try:
            data = {
                'job_title': title,
                'job_description': description,
                'required_skills': job_data.get('required_skills', []),
                'preferred_skills': job_data.get('preferred_skills', []),
                'min_experience': job_data.get('min_experience', 0),
                'job_data': job_data,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            response = self.client.table('job_postings').insert(data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            st.error(f"Failed to save job: {str(e)}")
            return None
    
    def get_all_job_postings(self):
        """Get all job postings"""
        try:
            response = self.client.table('job_postings').select('*').order('created_at', desc=True).execute()
            
            jobs = []
            for job in response.data:
                jobs.append({
                    'id': str(job['id']),
                    'title': job.get('job_title', 'Unknown'),
                    'description': job.get('job_description', ''),
                    'created_at': job.get('created_at', ''),
                    'required_skills': job.get('required_skills', []),
                    'preferred_skills': job.get('preferred_skills', [])
                })
            
            return jobs
        except Exception as e:
            st.warning(f"Could not fetch jobs: {str(e)}")
            return []
    
    def get_job_by_id(self, job_id):
        """Get specific job"""
        try:
            response = self.client.table('job_postings').select('*').eq('id', job_id).execute()
            
            if response.data:
                job = response.data[0]
                return {
                    'id': str(job['id']),
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
    
    def save_ranking(self, job_id, rankings):
        """Save candidate rankings"""
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
                    'created_at': datetime.now().isoformat()
                }
                records.append(record)
            
            self.client.table('rankings').delete().eq('job_posting_id', job_id).execute()
            
            if records:
                self.client.table('rankings').insert(records).execute()
            
            return True
        except Exception as e:
            st.error(f"Failed to save rankings: {str(e)}")
            return False
    
    def get_rankings_by_job(self, job_id):
        """Get rankings for job"""
        try:
            response = self.client.table('rankings').select('*').eq('job_posting_id', job_id).order('overall_score', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            st.warning(f"Could not fetch rankings: {str(e)}")
            return []
    
    def get_analytics_summary(self):
        """Get analytics"""
        try:
            resumes_response = self.client.table('resumes').select('id', count='exact').execute()
            jobs_response = self.client.table('job_postings').select('id', count='exact').execute()
            rankings_response = self.client.table('rankings').select('id', count='exact').execute()
            
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
