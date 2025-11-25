"""
AI Job-Resume Matcher & Ranking Engine - Step 2
Intelligently matches resumes with job descriptions and ranks candidates
"""

import json
import re
from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from collections import Counter

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

class JobDescriptionParser:
    """Parse and extract key information from job descriptions"""
    
    def __init__(self):
        self.experience_patterns = [
            r'(\d+)\+?\s*(?:to|\-)?\s*(\d+)?\s*(?:years?|yrs?)',
            r'(\d+)\+\s*(?:years?|yrs?)',
        ]
        
        self.education_levels = {
            'phd': 5, 'ph.d': 5, 'doctorate': 5,
            'masters': 4, 'master': 4, 'm.tech': 4, 'm.sc': 4, 'mba': 4,
            'bachelors': 3, 'bachelor': 3, 'b.tech': 3, 'b.sc': 3, 'b.e': 3,
            'diploma': 2,
            'high school': 1
        }
    
    def parse_job_description(self, job_text: str) -> Dict:
        """
        Parse job description and extract structured information
        
        Args:
            job_text: Raw job description text
            
        Returns:
            Dictionary with parsed job requirements
        """
        job_data = {
            'raw_text': job_text,
            'title': '',
            'required_skills': [],
            'preferred_skills': [],
            'min_experience': 0,
            'max_experience': None,
            'education_required': '',
            'responsibilities': [],
            'keywords': [],
            'must_have_skills': [],
            'nice_to_have_skills': []
        }
        
        # Extract job title (usually first line or contains "position", "role")
        job_data['title'] = self._extract_job_title(job_text)
        
        # Extract experience requirements
        job_data['min_experience'], job_data['max_experience'] = self._extract_experience(job_text)
        
        # Extract skills
        job_data['required_skills'], job_data['preferred_skills'] = self._extract_skills(job_text)
        
        # Extract must-have vs nice-to-have
        job_data['must_have_skills'] = self._extract_must_have_skills(job_text)
        job_data['nice_to_have_skills'] = self._extract_nice_to_have_skills(job_text)
        
        # Extract education requirements
        job_data['education_required'] = self._extract_education(job_text)
        
        # Extract keywords using NLP
        job_data['keywords'] = self._extract_keywords(job_text)
        
        return job_data
    
    def _extract_job_title(self, text: str) -> str:
        """Extract job title from description"""
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) < 100:
                # Check for job title indicators
                if any(keyword in line.lower() for keyword in ['position', 'role', 'job title', 'hiring for']):
                    return line
                # First substantial line might be title
                if len(line.split()) <= 10 and len(line) > 10:
                    return line
        
        return "Position Not Specified"
    
    def _extract_experience(self, text: str) -> Tuple[int, int]:
        """Extract minimum and maximum experience requirements"""
        text_lower = text.lower()
        
        for pattern in self.experience_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                match = matches[0]
                if isinstance(match, tuple):
                    min_exp = int(match[0]) if match[0] else 0
                    max_exp = int(match[1]) if len(match) > 1 and match[1] else None
                    return min_exp, max_exp
                else:
                    return int(match), None
        
        # Check for "fresher" or "entry level"
        if any(term in text_lower for term in ['fresher', 'entry level', '0 years', 'no experience']):
            return 0, 2
        
        return 0, None
    
    def _extract_skills(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract required and preferred skills"""
        required_skills = []
        preferred_skills = []
        
        # Common skills database (you can expand this)
        all_skills = [
            'Python', 'Java', 'JavaScript', 'C++', 'C#', 'Ruby', 'Go', 'Rust', 'PHP',
            'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring',
            'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Cassandra',
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'CI/CD',
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'NLP',
            'Git', 'Agile', 'Scrum', 'REST API', 'GraphQL', 'Microservices',
            'HTML', 'CSS', 'TypeScript', 'Swift', 'Kotlin', 'Scala'
        ]
        
        text_lower = text.lower()
        
        for skill in all_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                # Determine if required or preferred
                # Look for context around the skill
                skill_index = text_lower.find(skill.lower())
                context = text_lower[max(0, skill_index-100):min(len(text_lower), skill_index+100)]
                
                if any(term in context for term in ['required', 'must have', 'mandatory', 'essential']):
                    required_skills.append(skill)
                elif any(term in context for term in ['preferred', 'nice to have', 'plus', 'bonus']):
                    preferred_skills.append(skill)
                else:
                    required_skills.append(skill)  # Default to required
        
        return required_skills, preferred_skills
    
    def _extract_must_have_skills(self, text: str) -> List[str]:
        """Extract must-have skills"""
        must_have = []
        text_lower = text.lower()
        
        # Look for sections with must-have indicators
        must_have_section = re.search(
            r'(?:must have|required|essential|mandatory)[\s\S]{0,500}',
            text_lower
        )
        
        if must_have_section:
            section_text = must_have_section.group()
            # Extract skills from this section
            skills = self._extract_skills(section_text)[0]
            must_have.extend(skills)
        
        return list(set(must_have))
    
    def _extract_nice_to_have_skills(self, text: str) -> List[str]:
        """Extract nice-to-have skills"""
        nice_to_have = []
        text_lower = text.lower()
        
        # Look for sections with nice-to-have indicators
        nice_section = re.search(
            r'(?:nice to have|preferred|plus|bonus|optional)[\s\S]{0,500}',
            text_lower
        )
        
        if nice_section:
            section_text = nice_section.group()
            skills = self._extract_skills(section_text)[1]
            nice_to_have.extend(skills)
        
        return list(set(nice_to_have))
    
    def _extract_education(self, text: str) -> str:
        """Extract education requirements"""
        text_lower = text.lower()
        
        highest_level = ''
        highest_score = 0
        
        for edu, score in self.education_levels.items():
            if edu in text_lower and score > highest_score:
                highest_level = edu
                highest_score = score
        
        return highest_level.title() if highest_level else 'Not Specified'
    
    def _extract_keywords(self, text: str, top_n=20) -> List[str]:
        """Extract important keywords using NLP"""
        doc = nlp(text.lower())
        
        # Extract nouns and proper nouns
        keywords = []
        for token in doc:
            if token.pos_ in ['NOUN', 'PROPN'] and not token.is_stop and len(token.text) > 2:
                keywords.append(token.text)
        
        # Count frequency
        keyword_freq = Counter(keywords)
        
        # Return top keywords
        return [word for word, _ in keyword_freq.most_common(top_n)]


class JobResumeMatcher:
    """Match resumes with job descriptions using multiple algorithms"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words='english'
        )
    
    def calculate_match_score(
        self, 
        resume_data: Dict, 
        job_data: Dict
    ) -> Dict:
        """
        Calculate comprehensive match score between resume and job
        
        Returns:
            Dictionary with overall score and breakdown
        """
        scores = {
            'overall_score': 0,
            'skills_score': 0,
            'experience_score': 0,
            'education_score': 0,
            'keywords_score': 0,
            'semantic_score': 0,
            'matched_skills': [],
            'missing_skills': [],
            'experience_gap': 0,
            'explanation': {}
        }
        
        # 1. Skills Matching (40% weight)
        scores['skills_score'], scores['matched_skills'], scores['missing_skills'] = \
            self._calculate_skills_score(resume_data, job_data)
        
        # 2. Experience Matching (30% weight)
        scores['experience_score'], scores['experience_gap'] = \
            self._calculate_experience_score(resume_data, job_data)
        
        # 3. Education Matching (15% weight)
        scores['education_score'] = self._calculate_education_score(resume_data, job_data)
        
        # 4. Keywords Matching (10% weight)
        scores['keywords_score'] = self._calculate_keywords_score(resume_data, job_data)
        
        # 5. Semantic Similarity (5% weight)
        scores['semantic_score'] = self._calculate_semantic_score(resume_data, job_data)
        
        # Calculate overall score
        scores['overall_score'] = (
            scores['skills_score'] * 0.40 +
            scores['experience_score'] * 0.30 +
            scores['education_score'] * 0.15 +
            scores['keywords_score'] * 0.10 +
            scores['semantic_score'] * 0.05
        )
        
        # Generate explanation
        scores['explanation'] = self._generate_explanation(scores, resume_data, job_data)
        
        return scores
    
    def _calculate_skills_score(
        self, 
        resume_data: Dict, 
        job_data: Dict
    ) -> Tuple[float, List[str], List[str]]:
        """Calculate skills match score"""
        # Get all resume skills
        resume_skills = []
        for category, skills in resume_data.get('skills', {}).items():
            resume_skills.extend([s.lower() for s in skills])
        resume_skills = set(resume_skills)
        
        # Get required job skills
        required_skills = set([s.lower() for s in job_data.get('required_skills', [])])
        preferred_skills = set([s.lower() for s in job_data.get('preferred_skills', [])])
        all_job_skills = required_skills.union(preferred_skills)
        
        if not all_job_skills:
            return 100.0, [], []
        
        # Calculate matches
        matched_required = resume_skills.intersection(required_skills)
        matched_preferred = resume_skills.intersection(preferred_skills)
        
        # Score calculation
        required_score = (len(matched_required) / len(required_skills) * 100) if required_skills else 100
        preferred_score = (len(matched_preferred) / len(preferred_skills) * 100) if preferred_skills else 0
        
        # Weighted average (required skills are more important)
        if required_skills:
            skills_score = (required_score * 0.8) + (preferred_score * 0.2)
        else:
            skills_score = preferred_score
        
        matched_skills = list(matched_required.union(matched_preferred))
        missing_skills = list(all_job_skills - resume_skills)
        
        return skills_score, matched_skills, missing_skills
    
    def _calculate_experience_score(
        self, 
        resume_data: Dict, 
        job_data: Dict
    ) -> Tuple[float, float]:
        """Calculate experience match score"""
        resume_exp = resume_data.get('total_experience_years', 0)
        required_exp = job_data.get('min_experience', 0)
        max_exp = job_data.get('max_experience')
        
        if required_exp == 0:
            return 100.0, 0  # No experience requirement
        
        # Calculate gap
        if resume_exp >= required_exp:
            # Candidate meets or exceeds requirement
            if max_exp and resume_exp > max_exp:
                # Overqualified
                excess = resume_exp - max_exp
                score = max(70, 100 - (excess * 5))  # Slight penalty for overqualification
            else:
                score = 100.0
            gap = 0
        else:
            # Candidate doesn't meet requirement
            gap = required_exp - resume_exp
            # Penalty based on gap
            score = max(0, 100 - (gap * 20))  # 20% penalty per year missing
        
        return score, gap
    
    def _calculate_education_score(
        self, 
        resume_data: Dict, 
        job_data: Dict
    ) -> float:
        """Calculate education match score"""
        education_levels = {
            'phd': 5, 'ph.d': 5, 'doctorate': 5,
            'masters': 4, 'master': 4, 'm.tech': 4, 'm.sc': 4, 'mba': 4,
            'bachelors': 3, 'bachelor': 3, 'b.tech': 3, 'b.sc': 3, 'b.e': 3,
            'diploma': 2,
            'high school': 1
        }
        
        # Get resume education level
        resume_edu = resume_data.get('education', [])
        resume_level = 0
        
        for edu in resume_edu:
            degree = edu.get('degree', '').lower()
            for key, level in education_levels.items():
                if key in degree:
                    resume_level = max(resume_level, level)
        
        # Get required education level
        required_edu = job_data.get('education_required', '').lower()
        required_level = education_levels.get(required_edu, 0)
        
        if required_level == 0:
            return 100.0  # No specific requirement
        
        if resume_level >= required_level:
            return 100.0
        elif resume_level == required_level - 1:
            return 80.0  # One level below
        else:
            return max(50.0, 100 - ((required_level - resume_level) * 20))
    
    def _calculate_keywords_score(
        self, 
        resume_data: Dict, 
        job_data: Dict
    ) -> float:
        """Calculate keyword match score"""
        # Get resume text (combine all text fields)
        resume_text = ' '.join([
            resume_data.get('summary', ''),
            ' '.join([exp.get('description', '') for exp in resume_data.get('experience', [])]),
            ' '.join([proj.get('description', '') for proj in resume_data.get('projects', [])])
        ]).lower()
        
        job_keywords = job_data.get('keywords', [])
        
        if not job_keywords:
            return 100.0
        
        # Count matching keywords
        matched_count = sum(1 for keyword in job_keywords if keyword in resume_text)
        
        score = (matched_count / len(job_keywords)) * 100
        
        return score
    
    def _calculate_semantic_score(
        self, 
        resume_data: Dict, 
        job_data: Dict
    ) -> float:
        """Calculate semantic similarity using TF-IDF"""
        try:
            # Prepare texts
            resume_text = ' '.join([
                resume_data.get('summary', ''),
                ' '.join([exp.get('description', '') for exp in resume_data.get('experience', [])]),
            ])
            
            job_text = job_data.get('raw_text', '')
            
            if not resume_text or not job_text:
                return 50.0
            
            # Calculate TF-IDF similarity
            vectors = self.vectorizer.fit_transform([job_text, resume_text])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            
            # Convert to percentage
            score = similarity * 100
            
            return score
        except:
            return 50.0  # Default score if calculation fails
    
    def _generate_explanation(
        self, 
        scores: Dict, 
        resume_data: Dict, 
        job_data: Dict
    ) -> Dict:
        """Generate human-readable explanation of the match"""
        explanation = {
            'summary': '',
            'strengths': [],
            'weaknesses': [],
            'recommendations': []
        }
        
        # Overall assessment
        overall = scores['overall_score']
        if overall >= 80:
            explanation['summary'] = "Excellent match! This candidate meets most requirements."
        elif overall >= 60:
            explanation['summary'] = "Good match. Candidate has relevant skills but may have some gaps."
        elif overall >= 40:
            explanation['summary'] = "Moderate match. Consider if willing to train or if skills are transferable."
        else:
            explanation['summary'] = "Low match. Significant gaps in required qualifications."
        
        # Strengths
        if scores['skills_score'] >= 70:
            explanation['strengths'].append(
                f"Strong skills match ({len(scores['matched_skills'])} matching skills)"
            )
        
        if scores['experience_score'] >= 80:
            exp_years = resume_data.get('total_experience_years', 0)
            explanation['strengths'].append(
                f"Meets experience requirement ({exp_years} years)"
            )
        
        if scores['education_score'] >= 90:
            explanation['strengths'].append("Meets education requirements")
        
        # Weaknesses
        if scores['skills_score'] < 60:
            missing_count = len(scores['missing_skills'])
            explanation['weaknesses'].append(
                f"Missing {missing_count} required skills"
            )
        
        if scores['experience_gap'] > 0:
            explanation['weaknesses'].append(
                f"Needs {scores['experience_gap']} more years of experience"
            )
        
        if scores['education_score'] < 70:
            explanation['weaknesses'].append("May not meet education requirements")
        
        # Recommendations
        if scores['overall_score'] >= 70:
            explanation['recommendations'].append("Recommend for interview")
        elif scores['overall_score'] >= 50:
            explanation['recommendations'].append("Consider for phone screen")
            if scores['missing_skills']:
                explanation['recommendations'].append(
                    f"Assess proficiency in: {', '.join(scores['missing_skills'][:3])}"
                )
        else:
            explanation['recommendations'].append("Consider other candidates first")
        
        return explanation


class CandidateRanker:
    """Rank and shortlist candidates based on match scores"""
    
    def __init__(self):
        self.matcher = JobResumeMatcher()
        self.job_parser = JobDescriptionParser()
    
    def rank_candidates(
        self, 
        resumes: List[Dict], 
        job_description: str,
        top_n: int = None
    ) -> List[Dict]:
        """
        Rank all candidates against job description
        
        Args:
            resumes: List of parsed resume dictionaries
            job_description: Raw job description text
            top_n: Return only top N candidates (None for all)
            
        Returns:
            List of ranked candidates with scores
        """
        # Parse job description
        job_data = self.job_parser.parse_job_description(job_description)
        
        ranked_candidates = []
        
        for resume in resumes:
            # Calculate match score
            scores = self.matcher.calculate_match_score(resume, job_data)
            
            # Create candidate profile
            candidate = {
                'name': resume['contact'].get('name', 'Unknown'),
                'email': resume['contact'].get('email', ''),
                'phone': resume['contact'].get('phone', ''),
                'overall_score': round(scores['overall_score'], 2),
                'skills_score': round(scores['skills_score'], 2),
                'experience_score': round(scores['experience_score'], 2),
                'education_score': round(scores['education_score'], 2),
                'total_experience': resume.get('total_experience_years', 0),
                'matched_skills': scores['matched_skills'],
                'missing_skills': scores['missing_skills'],
                'explanation': scores['explanation'],
                'resume_data': resume
            }
            
            ranked_candidates.append(candidate)
        
        # Sort by overall score
        ranked_candidates.sort(key=lambda x: x['overall_score'], reverse=True)
        
        # Return top N if specified
        if top_n:
            return ranked_candidates[:top_n]
        
        return ranked_candidates
    
    def generate_report(
        self, 
        ranked_candidates: List[Dict],
        job_description: str,
        output_file: str = "ranking_report.txt"
    ):
        """Generate detailed ranking report"""
        report = []
        report.append("=" * 80)
        report.append("CANDIDATE RANKING REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Job summary
        job_data = self.job_parser.parse_job_description(job_description)
        report.append(f"Position: {job_data['title']}")
        report.append(f"Required Experience: {job_data['min_experience']}+ years")
        report.append(f"Key Skills: {', '.join(job_data['required_skills'][:5])}")
        report.append("")
        report.append("=" * 80)
        report.append(f"Total Candidates Evaluated: {len(ranked_candidates)}")
        report.append("=" * 80)
        report.append("")
        
        # Individual candidate details
        for i, candidate in enumerate(ranked_candidates, 1):
            report.append(f"\n{'='*80}")
            report.append(f"RANK #{i}: {candidate['name']}")
            report.append(f"{'='*80}")
            report.append(f"Overall Match Score: {candidate['overall_score']}%")
            report.append(f"Email: {candidate['email']}")
            report.append(f"Phone: {candidate['phone']}")
            report.append(f"Total Experience: {candidate['total_experience']} years")
            report.append("")
            
            # Score breakdown
            report.append("Score Breakdown:")
            report.append(f"  • Skills Match: {candidate['skills_score']}%")
            report.append(f"  • Experience Match: {candidate['experience_score']}%")
            report.append(f"  • Education Match: {candidate['education_score']}%")
            report.append("")
            
            # Matched skills
            if candidate['matched_skills']:
                report.append(f"✓ Matched Skills ({len(candidate['matched_skills'])}): ")
                report.append(f"  {', '.join(candidate['matched_skills'][:10])}")
                report.append("")
            
            # Missing skills
            if candidate['missing_skills']:
                report.append(f"✗ Missing Skills ({len(candidate['missing_skills'])}): ")
                report.append(f"  {', '.join(candidate['missing_skills'][:10])}")
                report.append("")
            
            # Explanation
            exp = candidate['explanation']
            report.append(f"Assessment: {exp['summary']}")
            report.append("")
            
            if exp['strengths']:
                report.append("Strengths:")
                for strength in exp['strengths']:
                    report.append(f"  ✓ {strength}")
                report.append("")
            
            if exp['weaknesses']:
                report.append("Weaknesses:")
                for weakness in exp['weaknesses']:
                    report.append(f"  ✗ {weakness}")
                report.append("")
            
            if exp['recommendations']:
                report.append("Recommendation:")
                for rec in exp['recommendations']:
                    report.append(f"  → {rec}")
        
        # Write to file
        report_text = '\n'.join(report)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        return report_text


# Example usage and testing
if __name__ == "__main__":
    print("🚀 Job-Resume Matcher initialized!")
    print("This module provides:")
    print("  ✓ Job description parsing")
    print("  ✓ Resume-job matching with scores")
    print("  ✓ Candidate ranking")
    print("  ✓ Detailed explanations")
    print("\nUse test_matcher.py to run the complete matching system!")