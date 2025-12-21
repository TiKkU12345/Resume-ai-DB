"""
Question Generator - AI-Powered Follow-up Questions
This makes your agent INTERACTIVE
"""

import os
from typing import List, Dict
from openai import OpenAI
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class QuestionGenerator:
    """
    Generates intelligent follow-up questions using OpenAI
    This is what makes your agent interactive and adaptive
    """
    
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Cheaper and faster
    
    def generate_questions(
        self,
        job_data: Dict,
        candidate_data: Dict,
        critical_gaps: List[str],
        missing_info: List[str],
        confidence_score: float
    ) -> List[Dict[str, str]]:
        """
        Generate context-aware follow-up questions
        
        Returns list of questions with metadata:
        [
            {
                "question": "...",
                "gap_addressed": "...",
                "priority": "high|medium|low"
            }
        ]
        """
        
        prompt = self._build_question_prompt(
            job_data,
            candidate_data,
            critical_gaps,
            missing_info,
            confidence_score
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical recruiter. Generate targeted follow-up questions to clarify candidate fit."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temp for focused questions
                max_tokens=1000
            )
            
            questions_text = response.choices[0].message.content
            questions = self._parse_questions(questions_text)
            
            return questions
        
        except Exception as e:
            print(f"Error generating questions: {e}")
            # Fallback to template questions
            return self._generate_template_questions(critical_gaps, missing_info)
    
    def _build_question_prompt(
        self,
        job_data: Dict,
        candidate_data: Dict,
        critical_gaps: List[str],
        missing_info: List[str],
        confidence_score: float
    ) -> str:
        """Build prompt for question generation"""
        
        # Get candidate skills
        all_skills = []
        for skills in candidate_data.get('skills', {}).values():
            all_skills.extend(skills)
        
        prompt = f"""You are evaluating a candidate for: {job_data.get('title', 'a position')}

**Job Requirements:**
- Required Skills: {', '.join(job_data.get('required_skills', [])[:10])}
- Minimum Experience: {job_data.get('min_experience', 0)} years

**Candidate Profile:**
- Skills Mentioned: {', '.join(all_skills[:10])}
- Experience: {len(candidate_data.get('experience', []))} positions
- Projects: {len(candidate_data.get('projects', []))} projects

**Identified Gaps:**
- Critical gaps: {', '.join(critical_gaps)}
- Missing information: {', '.join(missing_info)}

**Current Confidence:** {confidence_score:.2f}

**Your Task:**
Generate 2-4 targeted follow-up questions to clarify the candidate's fit.

**Requirements:**
1. Each question should address a specific gap
2. Questions should be open-ended but focused
3. Ask for specific examples or projects
4. Avoid yes/no questions
5. Be professional and clear

**Output Format (JSON):**
[
  {{
    "question": "The actual question",
    "gap_addressed": "Which gap this addresses",
    "priority": "high|medium|low"
  }}
]

Generate the questions now as valid JSON:"""
        
        return prompt
    
    def _parse_questions(self, response_text: str) -> List[Dict[str, str]]:
        """Parse AI response into structured questions"""
        try:
            # Try to extract JSON from response
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            questions = json.loads(json_str)
            
            # Validate structure
            if not isinstance(questions, list):
                raise ValueError("Response is not a list")
            
            return questions
        
        except Exception as e:
            print(f"Error parsing questions: {e}")
            # Fallback: treat entire response as single question
            return [{
                "question": response_text.strip(),
                "gap_addressed": "general",
                "priority": "medium"
            }]
    
    def _generate_template_questions(
        self, 
        critical_gaps: List[str],
        missing_info: List[str]
    ) -> List[Dict[str, str]]:
        """Fallback template-based questions"""
        questions = []
        
        for gap in critical_gaps[:3]:  # Limit to 3 questions
            if gap == "work_experience":
                questions.append({
                    "question": "Could you provide details about your work experience? Include company names, roles, duration, and key responsibilities.",
                    "gap_addressed": "work_experience",
                    "priority": "high"
                })
            elif gap == "projects":
                questions.append({
                    "question": "Could you describe 1-2 relevant projects you've worked on? Include technologies used and your specific contributions.",
                    "gap_addressed": "projects",
                    "priority": "high"
                })
            else:
                # It's a skill gap
                questions.append({
                    "question": f"The job requires {gap}. Do you have experience with {gap}? If yes, please describe one project where you used it.",
                    "gap_addressed": gap,
                    "priority": "high"
                })
        
        return questions


class AnswerEvaluator:
    """
    Evaluates candidate responses to questions
    Updates confidence based on answers
    """
    
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        gap_addressed: str,
        job_data: Dict
    ) -> Dict:
        """
        Evaluate how well the answer addresses the gap
        
        Returns:
        {
            "satisfactory": bool,
            "confidence_boost": float (-0.2 to +0.3),
            "reasoning": str,
            "follow_up_needed": bool
        }
        """
        
        prompt = f"""You are evaluating a candidate's response to a follow-up question.

**Original Question:** {question}
**Gap Being Addressed:** {gap_addressed}
**Job Requirements:** {json.dumps(job_data, indent=2)}

**Candidate's Answer:**
{answer}

**Your Task:**
Evaluate this answer and determine:
1. Does it satisfactorily address the gap? (yes/no)
2. How much should this boost/reduce confidence? (-0.2 to +0.3)
3. Brief reasoning for your evaluation
4. Is another follow-up needed?

**Evaluation Criteria:**
- Specific examples with details = excellent (+0.2 to +0.3)
- Vague claims without evidence = poor (-0.1 to 0)
- Relevant experience clearly described = good (+0.1 to +0.2)
- Irrelevant tangents = bad (-0.2)
- No answer or "I don't know" = very poor (-0.2)

**Output Format (JSON):**
{{
  "satisfactory": true/false,
  "confidence_boost": 0.15,
  "reasoning": "Brief explanation",
  "follow_up_needed": true/false
}}

Evaluate now as valid JSON:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical interviewer evaluating candidate responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = result_text.strip()
            
            result = json.loads(json_str)
            
            return result
        
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            # Fallback
            return {
                "satisfactory": False,
                "confidence_boost": 0.0,
                "reasoning": "Could not evaluate answer properly",
                "follow_up_needed": True
            }


# Test the generator
if __name__ == "__main__":
    print("Testing Question Generator...")
    
    job_data = {
        "title": "Backend Developer",
        "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
        "min_experience": 3
    }
    
    candidate_data = {
        "skills": {
            "programming": ["Python", "Flask"],
            "databases": ["MySQL"]
        },
        "experience": [
            {"description": "Built web apps with Flask"}
        ],
        "projects": []
    }
    
    critical_gaps = ["FastAPI", "Docker"]
    missing_info = ["No FastAPI experience", "No container experience"]
    
    try:
        generator = QuestionGenerator()
        questions = generator.generate_questions(
            job_data,
            candidate_data,
            critical_gaps,
            missing_info,
            0.55
        )
        
        print("\nGenerated Questions:")
        print(json.dumps(questions, indent=2))
        
    except Exception as e:
        print(f"Test failed: {e}")
        print("Make sure OPENAI_API_KEY is set in your .env file")