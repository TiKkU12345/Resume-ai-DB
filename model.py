# import streamlit as st
# from supabase import create_client
# import os
# from datetime import datetime
# import base64

# # --- Supabase Setup ---
# SUPABASE_URL = st.secrets["SUPABASE_URL"]
# SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# def upload_resume(file, user_id):

#     file_bytes = file.getvalue()
#     file_name = f"{user_id}_{datetime.now().timestamp()}.pdf"
#     path = f"{user_id}/{file_name}"

#     res = supabase.storage.from_("resume-files").upload(path, file_bytes)

#     if "error" in res:
#         return None
    
#     public_url = f"{SUPABASE_URL}/storage/v1/object/public/resume-files/{path}"

#     # Insert into DB
#     record = supabase.table("resumes").insert({
#         "user_id": user_id,
#         "filename": file_name,
#         "resume_url": public_url,
#         "job_role": st.session_state.get("job_role", "")
#     }).execute()

#     return record.data[0]["id"], public_url


# def save_evaluation(resume_id, score, strengths, weaknesses, decision):
#     supabase.table("evaluations").insert({
#         "resume_id": resume_id,
#         "score": score,
#         "strengths": strengths,
#         "weaknesses": weaknesses,
#         "final_decision": decision
#     }).execute()
