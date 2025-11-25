from resume_parser import ResumeParser
import json

# Initialize parser
parser = ResumeParser()

# Parse a resume
print("🔍 Parsing resume...")
try:
    # Change this to your resume file path
    resume_data = parser.parse_resume("resumes/resume1.pdf.pdf")
    
    # Display results
    print("\n" + "="*60)
    print("✅ RESUME PARSED SUCCESSFULLY!")
    print("="*60)
    
    print(f"\n👤 Name: {resume_data['contact']['name']}")
    print(f"📧 Email: {resume_data['contact']['email']}")
    print(f"📱 Phone: {resume_data['contact']['phone']}")
    print(f"💼 LinkedIn: {resume_data['contact']['linkedin']}")
    print(f"⏱️  Total Experience: {resume_data['total_experience_years']} years")
    
    print(f"\n🎓 EDUCATION ({len(resume_data['education'])} entries):")
    for edu in resume_data['education']:
        print(f"   • {edu['degree']} - {edu['institution']}")
        if edu['field_of_study']:
            print(f"     Field: {edu['field_of_study']}")
    
    print(f"\n💼 WORK EXPERIENCE ({len(resume_data['experience'])} entries):")
    for exp in resume_data['experience']:
        print(f"   • {exp['position']}")
        print(f"     Company: {exp['company']}")
        print(f"     Duration: {exp['duration']}")
    
    print(f"\n🛠️  SKILLS:")
    total_skills = 0
    for category, skills in resume_data['skills'].items():
        if skills:
            print(f"   {category.replace('_', ' ').title()}: {len(skills)} skills")
            print(f"     → {', '.join(skills[:5])}")
            total_skills += len(skills)
    print(f"   Total: {total_skills} skills found")
    
    if resume_data['projects']:
        print(f"\n📂 PROJECTS ({len(resume_data['projects'])} entries):")
        for proj in resume_data['projects']:
            print(f"   • {proj['title']}")
    
    if resume_data['certifications']:
        print(f"\n🏆 CERTIFICATIONS ({len(resume_data['certifications'])} entries):")
        for cert in resume_data['certifications']:
            print(f"   • {cert['name']}")
    
    # Save to JSON
    output_file = "output/parsed_resume.json"
    parser.save_to_json(resume_data, output_file)
    print(f"\n💾 Full data saved to: {output_file}")
    
    # Also print JSON preview
    print("\n📄 JSON Preview (first 500 chars):")
    json_str = json.dumps(resume_data, indent=2)
    print(json_str[:500] + "...")

except FileNotFoundError:
    print("❌ Error: Resume file not found!")
    print("Make sure you have a resume file in the 'resumes/' folder")
    print("Update the file path in test_parser.py")
except Exception as e:
    print(f"❌ Error occurred: {str(e)}")
    import traceback
    traceback.print_exc()