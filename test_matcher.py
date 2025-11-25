"""
Test script for Job-Resume Matcher
Run this to see candidate rankings!
"""

import json
import os
from job_resume_matcher import CandidateRanker, JobDescriptionParser

# Sample Job Description
JOB_DESCRIPTION = """
Senior Python Developer

We are looking for an experienced Python Developer to join our AI team.

Requirements:
- 3-5 years of professional Python development experience
- Strong experience with Machine Learning frameworks (TensorFlow, PyTorch)
- Experience with cloud platforms (AWS preferred)
- Bachelor's degree in Computer Science or related field

Must Have Skills:
- Python (expert level)
- Machine Learning
- TensorFlow or PyTorch
- SQL databases
- REST API development

Nice to Have:
- AWS/Cloud experience
- Docker and Kubernetes
- React or frontend experience
- Experience with NLP projects

Responsibilities:
- Develop and deploy machine learning models
- Build scalable ML pipelines
- Collaborate with data scientists
- Write clean, maintainable code
"""

def load_parsed_resumes():
    """Load all parsed resumes from output folder"""
    resumes = []
    output_folder = "output"
    
    if not os.path.exists(output_folder):
        print("❌ Output folder not found!")
        print("Please run test_all_resumes.py first to parse resumes.")
        return resumes
    
    # Load all JSON files
    for filename in os.listdir(output_folder):
        if filename.endswith('_parsed.json'):
            filepath = os.path.join(output_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    resume_data = json.load(f)
                    resumes.append(resume_data)
                    print(f"✓ Loaded: {filename}")
            except Exception as e:
                print(f"✗ Failed to load {filename}: {e}")
    
    return resumes

def main():
    print("="*80)
    print("🎯 AI RESUME SHORTLISTING SYSTEM - JOB MATCHER")
    print("="*80)
    print()
    
    # Load parsed resumes
    print("📁 Loading parsed resumes...")
    resumes = load_parsed_resumes()
    
    if not resumes:
        print("\n❌ No resumes found!")
        print("Please place resume files in 'resumes/' folder and run:")
        print("   python test_all_resumes.py")
        return
    
    print(f"✅ Loaded {len(resumes)} resume(s)\n")
    
    # Initialize ranker
    print("🔧 Initializing AI matcher...")
    ranker = CandidateRanker()
    print("✅ Matcher ready!\n")
    
    # Show job description
    print("="*80)
    print("📋 JOB DESCRIPTION")
    print("="*80)
    print(JOB_DESCRIPTION)
    print()
    
    # Rank candidates
    print("="*80)
    print("🤖 ANALYZING CANDIDATES...")
    print("="*80)
    print()
    
    ranked_candidates = ranker.rank_candidates(resumes, JOB_DESCRIPTION)
    
    # Display results
    print("="*80)
    print("🏆 CANDIDATE RANKINGS")
    print("="*80)
    print()
    
    for i, candidate in enumerate(ranked_candidates, 1):
        score = candidate['overall_score']
        
        # Color coding based on score
        if score >= 80:
            emoji = "🟢"
            status = "EXCELLENT MATCH"
        elif score >= 60:
            emoji = "🟡"
            status = "GOOD MATCH"
        elif score >= 40:
            emoji = "🟠"
            status = "MODERATE MATCH"
        else:
            emoji = "🔴"
            status = "LOW MATCH"
        
        print(f"{emoji} RANK #{i}: {candidate['name']}")
        print(f"   Overall Score: {score}% - {status}")
        print(f"   Email: {candidate['email']}")
        print(f"   Experience: {candidate['total_experience']} years")
        print()
        
        # Score breakdown
        print(f"   📊 Score Breakdown:")
        print(f"      • Skills:     {candidate['skills_score']}%")
        print(f"      • Experience: {candidate['experience_score']}%")
        print(f"      • Education:  {candidate['education_score']}%")
        print()
        
        # Matched skills
        if candidate['matched_skills']:
            matched_count = len(candidate['matched_skills'])
            print(f"   ✅ Matched Skills ({matched_count}):")
            skills_display = ', '.join(candidate['matched_skills'][:8])
            if matched_count > 8:
                skills_display += f", +{matched_count - 8} more"
            print(f"      {skills_display}")
            print()
        
        # Missing skills
        if candidate['missing_skills']:
            missing_count = len(candidate['missing_skills'])
            print(f"   ❌ Missing Skills ({missing_count}):")
            missing_display = ', '.join(candidate['missing_skills'][:5])
            if missing_count > 5:
                missing_display += f", +{missing_count - 5} more"
            print(f"      {missing_display}")
            print()
        
        # Assessment
        print(f"   💡 Assessment: {candidate['explanation']['summary']}")
        print()
        
        # Recommendation
        if candidate['explanation']['recommendations']:
            print(f"   🎯 Recommendation: {candidate['explanation']['recommendations'][0]}")
        
        print("-" * 80)
        print()
    
    # Summary statistics
    print("="*80)
    print("📊 SUMMARY STATISTICS")
    print("="*80)
    print()
    
    excellent = sum(1 for c in ranked_candidates if c['overall_score'] >= 80)
    good = sum(1 for c in ranked_candidates if 60 <= c['overall_score'] < 80)
    moderate = sum(1 for c in ranked_candidates if 40 <= c['overall_score'] < 60)
    low = sum(1 for c in ranked_candidates if c['overall_score'] < 40)
    
    print(f"🟢 Excellent Match (80%+):  {excellent} candidates")
    print(f"🟡 Good Match (60-79%):     {good} candidates")
    print(f"🟠 Moderate Match (40-59%): {moderate} candidates")
    print(f"🔴 Low Match (<40%):        {low} candidates")
    print()
    
    # Shortlist recommendation
    shortlist = [c for c in ranked_candidates if c['overall_score'] >= 60]
    print(f"💼 Recommended for Interview: {len(shortlist)} candidate(s)")
    if shortlist:
        print(f"   Top picks: {', '.join([c['name'] for c in shortlist[:3]])}")
    print()
    
    # Generate detailed report
    print("="*80)
    print("📝 GENERATING DETAILED REPORT...")
    print("="*80)
    
    report_file = "output/ranking_report.txt"
    ranker.generate_report(ranked_candidates, JOB_DESCRIPTION, report_file)
    
    print(f"✅ Detailed report saved to: {report_file}")
    print()
    
    # Save JSON results
    json_file = "output/ranking_results.json"
    results_for_json = []
    for candidate in ranked_candidates:
        # Remove full resume data for cleaner JSON
        json_candidate = {
            'name': candidate['name'],
            'email': candidate['email'],
            'phone': candidate['phone'],
            'overall_score': candidate['overall_score'],
            'skills_score': candidate['skills_score'],
            'experience_score': candidate['experience_score'],
            'education_score': candidate['education_score'],
            'total_experience': candidate['total_experience'],
            'matched_skills': candidate['matched_skills'],
            'missing_skills': candidate['missing_skills'],
            'explanation': candidate['explanation']
        }
        results_for_json.append(json_candidate)
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results_for_json, f, indent=2)
    
    print(f"✅ JSON results saved to: {json_file}")
    print()
    
    # Next steps
    print("="*80)
    print("✨ NEXT STEPS")
    print("="*80)
    print("1. Review the detailed report in output/ranking_report.txt")
    print("2. Check JSON results in output/ranking_results.json")
    print("3. Contact top candidates for interviews!")
    print()
    print("💡 Want to test with a different job description?")
    print("   Edit the JOB_DESCRIPTION variable in this file and run again.")
    print()
    print("🎉 Shortlisting complete!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Make sure you have:")
        print("   1. Parsed resumes (run test_all_resumes.py first)")
        print("   2. Installed required packages: pip install scikit-learn")