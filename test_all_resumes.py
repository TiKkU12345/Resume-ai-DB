from resume_parser import ResumeParser
import os

# Initialize parser
parser = ResumeParser()

# Get all resume files from resumes folder
resume_folder = "resumes"
resume_files = []

# List all files in resumes folder
for filename in os.listdir(resume_folder):
    if filename.endswith('.pdf') or filename.endswith('.docx'):
        resume_files.append(filename)

print(f"📁 Found {len(resume_files)} resume(s) to parse\n")
print("="*70)

all_parsed_data = []

# Parse each resume
for i, filename in enumerate(resume_files, 1):
    print(f"\n[{i}/{len(resume_files)}] 📄 Parsing: {filename}")
    print("-"*70)
    
    try:
        file_path = os.path.join(resume_folder, filename)    
        resume_data = parser.parse_resume(file_path)
        all_parsed_data.append(resume_data)
        
        # Display summary
        print(f"✅ SUCCESS!")
        print(f"   👤 Name: {resume_data['contact']['name']}")
        print(f"   📧 Email: {resume_data['contact']['email']}")
        print(f"   📱 Phone: {resume_data['contact']['phone']}")
        print(f"   ⏱️  Experience: {resume_data['total_experience_years']} years")
        
        # Count skills
        total_skills = sum(len(v) for v in resume_data['skills'].values())
        print(f"   🛠️  Skills: {total_skills} found")
        
        # Show top skills
        if resume_data['skills']:
            print(f"   Top Skills: ", end="")
            all_skills = []
            for category, skills in resume_data['skills'].items():
                all_skills.extend(skills)
            print(", ".join(all_skills[:5]))
        
        print(f"   📚 Education: {len(resume_data['education'])} entry/entries")
        print(f"   💼 Jobs: {len(resume_data['experience'])} entry/entries")
        
        # Save individual JSON
        output_filename = f"output/{filename.replace('.pdf', '').replace('.docx', '')}_parsed.json"
        parser.save_to_json(resume_data, output_filename)
        print(f"   💾 Saved to: {output_filename}")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "="*70)
print(f"\n🎉 Parsing Complete!")
print(f"✅ Successfully parsed: {len(all_parsed_data)}/{len(resume_files)} resumes")

# Save summary CSV
if all_parsed_data:
    parser.save_to_csv(all_parsed_data, "output/all_resumes_summary.csv")
    print(f"📊 Summary saved to: output/all_resumes_summary.csv")
    
    # Print comparison table
    print("\n" + "="*70)
    print("📊 COMPARISON TABLE")
    print("="*70)
    print(f"{'Name':<25} {'Experience':<12} {'Skills':<10} {'Education':<10}")
    print("-"*70)
    
    for data in all_parsed_data:
        name = data['contact']['name'][:24]
        exp = f"{data['total_experience_years']} yrs"
        skills_count = sum(len(v) for v in data['skills'].values())
        edu_count = len(data['education'])
        
        print(f"{name:<25} {exp:<12} {skills_count:<10} {edu_count:<10}")
    
    print("="*70)
    
    # Find best candidate
    print("\n🏆 QUICK ANALYSIS:")
    
    # Most experienced
    most_exp = max(all_parsed_data, key=lambda x: x['total_experience_years'])
    print(f"   Most Experienced: {most_exp['contact']['name']} ({most_exp['total_experience_years']} years)")
    
    # Most skills
    most_skilled = max(all_parsed_data, key=lambda x: sum(len(v) for v in x['skills'].values()))
    skills_count = sum(len(v) for v in most_skilled['skills'].values())
    print(f"   Most Skills: {most_skilled['contact']['name']} ({skills_count} skills)")

print("\n✨ All done! Check the 'output' folder for detailed results.")