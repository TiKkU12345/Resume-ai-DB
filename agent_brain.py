"""
Agent Brain - Core Decision-Making Logic
This is what makes your system an AGENT instead of just a scorer
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np

class ConfidenceLevel(Enum):
    HIGH = "high"      # >= 0.75
    MEDIUM = "medium"  # 0.4 - 0.75
    LOW = "low"        # < 0.4

class AgentDecision(Enum):
    AUTO_SHORTLIST = "auto_shortlist"
    ASK_QUESTIONS = "ask_questions"
    AUTO_REJECT = "auto_reject"

@dataclass
class CandidateAnalysis:
    """Complete analysis result from the agent"""
    candidate_name: str
    candidate_email: str
    base_score: float
    confidence_score: float
    confidence_level: ConfidenceLevel
    decision: AgentDecision
    reasoning: List[str]
    missing_info: List[str]
    critical_gaps: List[str]
    matched_skills: List[str]
    missing_skills: List[str]

class AgentBrain:
    """
    The core decision-making component
    This is what transforms your system into an AI Agent
    """
    
    def __init__(self, job_data: Dict):
        self.job_data = job_data
        self.critical_skills = self._extract_critical_skills()
        self.confidence_threshold_high = 0.75
        self.confidence_threshold_low = 0.40
    
    def _extract_critical_skills(self) -> List[str]:
        """Identify which skills are absolutely critical"""
        # Get required skills (these are critical by default)
        critical = self.job_data.get('required_skills', [])
        
        # Also check must_have_skills
        must_have = self.job_data.get('must_have_skills', [])
        
        # Combine and deduplicate
        all_critical = list(set(critical + must_have))
        
        return all_critical
    
    def analyze_candidate(
        self, 
        candidate_data: Dict,
        match_scores: Dict
    ) -> CandidateAnalysis:
        """
        CORE AGENT FUNCTION: Analyze candidate and DECIDE what to do
        
        This is where the agent "thinks"
        
        Args:
            candidate_data: Parsed resume data
            match_scores: Scores from job_resume_matcher
        
        Returns:
            Complete analysis with decision
        """
        
        # Step 1: Get base scores
        base_score = match_scores['overall_score']
        skills_score = match_scores['skills_score']
        experience_score = match_scores['experience_score']
        matched_skills = match_scores.get('matched_skills', [])
        missing_skills = match_scores.get('missing_skills', [])
        
        # Step 2: Calculate CONFIDENCE (this is key for agent behavior)
        confidence_score = self._calculate_confidence(
            candidate_data,
            match_scores,
            matched_skills,
            missing_skills
        )
        
        # Step 3: Identify information gaps
        missing_info, critical_gaps = self._identify_gaps(
            candidate_data,
            matched_skills,
            missing_skills
        )
        
        # Step 4: Determine confidence level
        confidence_level = self._determine_confidence_level(confidence_score)
        
        # Step 5: MAKE DECISION (Agent behavior)
        decision = self._make_decision(
            confidence_level, 
            critical_gaps,
            base_score
        )
        
        # Step 6: Generate reasoning
        reasoning = self._generate_reasoning(
            base_score,
            confidence_score,
            missing_info,
            critical_gaps,
            decision
        )
        
        return CandidateAnalysis(
            candidate_name=candidate_data['contact'].get('name', 'Unknown'),
            candidate_email=candidate_data['contact'].get('email', ''),
            base_score=base_score,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            decision=decision,
            reasoning=reasoning,
            missing_info=missing_info,
            critical_gaps=critical_gaps,
            matched_skills=matched_skills,
            missing_skills=missing_skills
        )
    
    def _calculate_confidence(
        self,
        candidate_data: Dict,
        match_scores: Dict,
        matched_skills: List[str],
        missing_skills: List[str]
    ) -> float:
        """
        Calculate how CONFIDENT the agent is about its decision
        
        Confidence ≠ Match Score
        Confidence = information completeness + skill criticality + clarity
        """
        
        confidence_factors = []
        
        # Factor 1: Information completeness (0-1)
        required_fields = ['experience', 'skills', 'education']
        completeness = sum(
            1 for field in required_fields 
            if candidate_data.get(field) and len(candidate_data[field]) > 0
        ) / len(required_fields)
        confidence_factors.append(completeness)
        
        # Factor 2: Critical skill coverage (0-1)
        if self.critical_skills:
            matched_critical = [
                s for s in matched_skills 
                if any(crit.lower() in s.lower() for crit in self.critical_skills)
            ]
            critical_coverage = len(matched_critical) / len(self.critical_skills)
            confidence_factors.append(critical_coverage * 1.5)  # Weight this heavily
        else:
            confidence_factors.append(1.0)
        
        # Factor 3: Experience detail (0-1)
        experiences = candidate_data.get('experience', [])
        if experiences:
            total_description_length = sum(
                len(exp.get('description', '')) for exp in experiences
            )
            avg_detail = total_description_length / len(experiences)
            detail_score = min(1.0, avg_detail / 200)  # 200 chars = detailed
            confidence_factors.append(detail_score)
        else:
            confidence_factors.append(0.3)
        
        # Factor 4: Score consistency (0-1)
        # If all component scores are similar, we're more confident
        component_scores = [
            match_scores.get('skills_score', 0),
            match_scores.get('experience_score', 0),
            match_scores.get('education_score', 0)
        ]
        if len(component_scores) > 1:
            variance = np.std(component_scores)
            consistency = max(0, 1 - (variance / 50))  # Lower variance = more confident
            confidence_factors.append(consistency)
        
        # Combine factors
        confidence = np.mean(confidence_factors)
        
        return min(1.0, confidence)
    
    def _identify_gaps(
        self, 
        candidate_data: Dict,
        matched_skills: List[str],
        missing_skills: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Identify what information is missing or unclear
        
        Returns:
            (missing_info, critical_gaps)
        """
        missing_info = []
        critical_gaps = []
        
        # Check for missing critical skills
        for critical_skill in self.critical_skills:
            if not any(critical_skill.lower() in s.lower() for s in matched_skills):
                missing_info.append(f"No evidence of {critical_skill}")
                critical_gaps.append(critical_skill)
        
        # Check for vague or missing experience
        experiences = candidate_data.get('experience', [])
        if not experiences or len(experiences) == 0:
            missing_info.append("No work experience details")
            critical_gaps.append("work_experience")
        else:
            # Check if experience descriptions are too short (vague)
            vague_count = sum(
                1 for exp in experiences 
                if len(exp.get('description', '')) < 50
            )
            if vague_count > len(experiences) / 2:
                missing_info.append("Work experience lacks detail")
        
        # Check for missing projects (if job requires them)
        if self.job_data.get('min_experience', 0) < 2:  # Entry-level might need projects
            projects = candidate_data.get('projects', [])
            if not projects or len(projects) == 0:
                missing_info.append("No projects mentioned")
                if len(experiences) == 0:  # No exp AND no projects
                    critical_gaps.append("projects")
        
        return missing_info, critical_gaps
    
    def _determine_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Map confidence score to discrete level"""
        if confidence_score >= self.confidence_threshold_high:
            return ConfidenceLevel.HIGH
        elif confidence_score >= self.confidence_threshold_low:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _make_decision(
        self, 
        confidence_level: ConfidenceLevel,
        critical_gaps: List[str],
        base_score: float
    ) -> AgentDecision:
        """
        CORE AGENT LOGIC: Decide what action to take
        
        This is the "autonomous decision-making" that makes it an agent
        """
        
        if confidence_level == ConfidenceLevel.HIGH:
            # High confidence - auto shortlist
            return AgentDecision.AUTO_SHORTLIST
        
        elif confidence_level == ConfidenceLevel.MEDIUM:
            # Medium confidence - need more info
            if critical_gaps:
                # Critical gaps exist - ask questions
                return AgentDecision.ASK_QUESTIONS
            else:
                # No critical gaps, just low confidence
                # Shortlist with caution if base score is decent
                if base_score >= 60:
                    return AgentDecision.AUTO_SHORTLIST
                else:
                    return AgentDecision.ASK_QUESTIONS
        
        else:  # LOW confidence
            # Low confidence - reject unless gaps are clarifiable
            if len(critical_gaps) <= 2 and base_score >= 40:
                # Few gaps and decent base score - worth asking
                return AgentDecision.ASK_QUESTIONS
            else:
                # Too many gaps or very low score
                return AgentDecision.AUTO_REJECT
    
    def _generate_reasoning(
        self,
        base_score: float,
        confidence_score: float,
        missing_info: List[str],
        critical_gaps: List[str],
        decision: AgentDecision
    ) -> List[str]:
        """
        Generate human-readable reasoning for the decision
        """
        reasoning = []
        
        reasoning.append(f"Match score: {base_score:.1f}%")
        reasoning.append(f"Confidence: {confidence_score:.1f} ({self._confidence_label(confidence_score)})")
        
        if missing_info:
            reasoning.append(f"Missing information: {', '.join(missing_info[:3])}")
        
        if critical_gaps:
            reasoning.append(f"Critical gaps: {', '.join(critical_gaps[:3])}")
        
        # Decision explanation
        if decision == AgentDecision.AUTO_SHORTLIST:
            reasoning.append("✅ High confidence - automatically shortlisted")
        elif decision == AgentDecision.ASK_QUESTIONS:
            reasoning.append("❓ Medium confidence - follow-up questions needed")
        else:
            reasoning.append("❌ Low confidence - does not meet requirements")
        
        return reasoning
    
    def _confidence_label(self, score: float) -> str:
        """Convert confidence score to label"""
        if score >= 0.75:
            return "HIGH"
        elif score >= 0.40:
            return "MEDIUM"
        else:
            return "LOW"


def test_agent_brain():
    """Test the agent brain with sample data"""
    
    # Sample job data
    job_data = {
        'title': 'Senior Python Developer',
        'required_skills': ['Python', 'FastAPI', 'Docker'],
        'must_have_skills': ['Python', 'FastAPI'],
        'min_experience': 3
    }
    
    # Sample candidate data
    candidate_data = {
        'contact': {
            'name': 'Test Candidate',
            'email': 'test@example.com'
        },
        'experience': [
            {
                'title': 'Software Engineer',
                'description': 'Built REST APIs using Flask and deployed on AWS. Worked with microservices architecture.'
            }
        ],
        'skills': {
            'programming': ['Python', 'JavaScript'],
            'frameworks': ['Flask', 'React']
        },
        'projects': []
    }
    
    # Sample match scores
    match_scores = {
        'overall_score': 65.0,
        'skills_score': 60.0,
        'experience_score': 70.0,
        'education_score': 65.0,
        'matched_skills': ['Python', 'Flask'],
        'missing_skills': ['FastAPI', 'Docker']
    }
    
    # Create agent and analyze
    agent = AgentBrain(job_data)
    analysis = agent.analyze_candidate(candidate_data, match_scores)
    
    print("=" * 60)
    print("AGENT ANALYSIS TEST")
    print("=" * 60)
    print(f"Candidate: {analysis.candidate_name}")
    print(f"Base Score: {analysis.base_score:.1f}%")
    print(f"Confidence: {analysis.confidence_score:.2f} ({analysis.confidence_level.value})")
    print(f"Decision: {analysis.decision.value}")
    print(f"\nReasoning:")
    for reason in analysis.reasoning:
        print(f"  • {reason}")
    print(f"\nCritical Gaps: {', '.join(analysis.critical_gaps)}")
    print("=" * 60)


if __name__ == "__main__":
    test_agent_brain()