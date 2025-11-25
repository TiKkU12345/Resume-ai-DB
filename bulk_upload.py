"""
Bulk Resume Upload Feature
Upload and process multiple resumes from ZIP files
"""

import zipfile
import os
import tempfile
import streamlit as st
from pathlib import Path
from typing import List, Dict
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

class BulkResumeProcessor:
    """Handle bulk resume uploads and processing"""
    
    def __init__(self, parser):
        self.parser = parser
        self.supported_formats = ['.pdf', '.docx', '.doc']
        self.max_file_size = 10 * 1024 * 1024  # 10MB per file
    
    def extract_zip(self, zip_file) -> List[Path]:
        """Extract resume files from ZIP"""
        extracted_files = []
        
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            # Extract ZIP
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find all resume files
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    
                    # Check if supported format
                    if file_path.suffix.lower() in self.supported_formats:
                        # Check file size
                        if file_path.stat().st_size <= self.max_file_size:
                            extracted_files.append(file_path)
            
            return extracted_files, temp_dir
        
        except Exception as e:
            st.error(f"Failed to extract ZIP: {str(e)}")
            return [], None
    
    def parse_single_resume(self, file_path: Path) -> Dict:
        """Parse a single resume"""
        try:
            resume_data = self.parser.parse_resume(str(file_path))
            resume_data['filename'] = file_path.name
            resume_data['status'] = 'success'
            return resume_data
        except Exception as e:
            return {
                'filename': file_path.name,
                'status': 'failed',
                'error': str(e)
            }
    
    def parse_bulk_resumes(self, file_paths: List[Path], 
                          max_workers: int = 4) -> Dict:
        """Parse multiple resumes in parallel"""
        results = {
            'successful': [],
            'failed': [],
            'total': len(file_paths),
            'success_count': 0,
            'fail_count': 0
        }
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed = 0
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.parse_single_resume, fp): fp 
                for fp in file_paths
            }
            
            # Process completed tasks
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                processed += 1
                
                try:
                    result = future.result()
                    
                    if result['status'] == 'success':
                        results['successful'].append(result)
                        results['success_count'] += 1
                    else:
                        results['failed'].append(result)
                        results['fail_count'] += 1
                    
                    # Update progress
                    progress = processed / results['total']
                    progress_bar.progress(progress)
                    status_text.text(f"Processing: {processed}/{results['total']} resumes...")
                
                except Exception as e:
                    results['failed'].append({
                        'filename': file_path.name,
                        'status': 'failed',
                        'error': str(e)
                    })
                    results['fail_count'] += 1
        
        progress_bar.empty()
        status_text.empty()
        
        return results
    
    def cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary extracted files"""
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass


def render_bulk_upload_ui(parser, db_manager=None):
    """Render bulk upload interface"""
    
    st.header("📦 Bulk Resume Upload")
    
    st.markdown("""
    Upload a ZIP file containing multiple resumes for batch processing.
    
    **Supported Formats:** PDF, DOCX, DOC  
    **Max File Size:** 10MB per resume  
    **Recommended:** Up to 100 resumes per ZIP
    """)
    
    # File uploader
    uploaded_zip = st.file_uploader(
        "Choose ZIP file containing resumes",
        type=['zip'],
        help="Upload a ZIP file with multiple resume files"
    )
    
    if uploaded_zip:
        # Show file info
        file_size_mb = uploaded_zip.size / (1024 * 1024)
        st.info(f"📁 **File:** {uploaded_zip.name} ({file_size_mb:.2f} MB)")
        
        # Processing options
        col1, col2 = st.columns(2)
        
        with col1:
            max_workers = st.slider(
                "Parallel Processing Threads",
                min_value=1,
                max_value=8,
                value=4,
                help="More threads = faster processing (uses more CPU)"
            )
        
        with col2:
            save_to_db = st.checkbox(
                "Save to Database",
                value=True if db_manager else False,
                disabled=not db_manager,
                help="Automatically save parsed resumes to database"
            )
        
        # Process button
        if st.button("🚀 Process All Resumes", type="primary", use_container_width=True):
            process_bulk_resumes(uploaded_zip, parser, db_manager, max_workers, save_to_db)


def process_bulk_resumes(uploaded_zip, parser, db_manager, max_workers, save_to_db):
    """Process bulk resume upload"""
    
    processor = BulkResumeProcessor(parser)
    
    with st.spinner("Extracting ZIP file..."):
        file_paths, temp_dir = processor.extract_zip(uploaded_zip)
    
    if not file_paths:
        st.error("No valid resume files found in ZIP!")
        return
    
    st.success(f"✅ Found {len(file_paths)} resume file(s)")
    
    # Show file list
    with st.expander(f"📄 Files to process ({len(file_paths)})"):
        for fp in file_paths[:20]:  # Show first 20
            st.write(f"• {fp.name}")
        if len(file_paths) > 20:
            st.write(f"... and {len(file_paths) - 20} more")
    
    # Parse resumes
    st.markdown("---")
    st.markdown("### 🔄 Processing Resumes...")
    
    start_time = time.time()
    results = processor.parse_bulk_resumes(file_paths, max_workers)
    processing_time = time.time() - start_time
    
    # Show results
    st.markdown("---")
    st.markdown("### 📊 Processing Complete!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("✅ Successful", results['success_count'])
    
    with col2:
        st.metric("❌ Failed", results['fail_count'])
    
    with col3:
        st.metric("⏱️ Time Taken", f"{processing_time:.1f}s")
    
    # Success rate
    success_rate = (results['success_count'] / results['total']) * 100 if results['total'] > 0 else 0
    st.progress(success_rate / 100)
    st.write(f"**Success Rate:** {success_rate:.1f}%")
    
    # Save to database if enabled
    if save_to_db and db_manager and results['successful']:
        with st.spinner("Saving to database..."):
            saved_count = 0
            for resume_data in results['successful']:
                try:
                    db_manager.save_resume(resume_data['filename'], resume_data)
                    saved_count += 1
                except Exception as e:
                    st.warning(f"Failed to save {resume_data['filename']}: {e}")
            
            st.success(f"💾 Saved {saved_count} resumes to database!")
    
    # Add to session state
    if results['successful']:
        if 'parsed_resumes' not in st.session_state:
            st.session_state.parsed_resumes = []
        
        st.session_state.parsed_resumes.extend(results['successful'])
        st.success(f"✅ Added {len(results['successful'])} resumes to current session!")
    
    # Show detailed results
    tab1, tab2, tab3 = st.tabs(["✅ Successful", "❌ Failed", "📋 Summary"])
    
    with tab1:
        if results['successful']:
            st.markdown(f"**{len(results['successful'])} resumes parsed successfully**")
            
            for i, resume in enumerate(results['successful'][:10], 1):
                with st.expander(f"{i}. {resume['filename']}"):
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.write(f"**Name:** {resume['contact'].get('name', 'N/A')}")
                        st.write(f"**Email:** {resume['contact'].get('email', 'N/A')}")
                    
                    with col_b:
                        st.write(f"**Experience:** {resume.get('total_experience_years', 0)} years")
                        st.write(f"**Jobs:** {len(resume.get('experience', []))}")
                    
                    with col_c:
                        total_skills = sum(len(v) for v in resume.get('skills', {}).values())
                        st.write(f"**Skills:** {total_skills}")
                        st.write(f"**Education:** {len(resume.get('education', []))}")
            
            if len(results['successful']) > 10:
                st.info(f"Showing 10 of {len(results['successful'])} successful resumes")
        else:
            st.info("No resumes parsed successfully")
    
    with tab2:
        if results['failed']:
            st.markdown(f"**{len(results['failed'])} resumes failed to parse**")
            
            for i, failed in enumerate(results['failed'], 1):
                with st.expander(f"{i}. {failed['filename']} - ❌ Error"):
                    st.error(f"**Error:** {failed.get('error', 'Unknown error')}")
                    st.write(f"**File:** {failed['filename']}")
                    
                    # Troubleshooting tips
                    st.markdown("**💡 Possible Solutions:**")
                    st.markdown("""
                    - Check if file is corrupted
                    - Ensure it's a valid PDF/DOCX
                    - File might be password protected
                    - Try converting to a different format
                    """)
        else:
            st.success("All resumes parsed successfully!")
    
    with tab3:
        st.markdown("### Processing Summary")
        
        # Create summary DataFrame
        import pandas as pd
        
        summary_data = {
            'Metric': [
                'Total Files',
                'Successfully Parsed',
                'Failed to Parse',
                'Success Rate',
                'Processing Time',
                'Avg Time per Resume'
            ],
            'Value': [
                results['total'],
                results['success_count'],
                results['fail_count'],
                f"{success_rate:.1f}%",
                f"{processing_time:.2f}s",
                f"{processing_time/results['total']:.2f}s" if results['total'] > 0 else "N/A"
            ]
        }
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        
        # Experience distribution
        if results['successful']:
            st.markdown("### 📊 Quick Stats")
            
            experiences = [r.get('total_experience_years', 0) for r in results['successful']]
            avg_exp = sum(experiences) / len(experiences) if experiences else 0
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Avg Experience", f"{avg_exp:.1f} years")
            
            with col_b:
                total_skills = sum(
                    sum(len(v) for v in r.get('skills', {}).values()) 
                    for r in results['successful']
                )
                avg_skills = total_skills / len(results['successful']) if results['successful'] else 0
                st.metric("Avg Skills", f"{avg_skills:.0f}")
            
            with col_c:
                with_email = sum(1 for r in results['successful'] 
                               if r['contact'].get('email'))
                st.metric("With Email", f"{with_email}/{len(results['successful'])}")
    
    # Download options
    st.markdown("---")
    st.markdown("### 📥 Export Results")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if st.button("📊 Download Success Report (CSV)", use_container_width=True):
            if results['successful']:
                csv_data = create_csv_report(results['successful'])
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"bulk_upload_success_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    with col_exp2:
        if st.button("❌ Download Failed List (TXT)", use_container_width=True):
            if results['failed']:
                failed_text = "\n".join([
                    f"{f['filename']} - {f.get('error', 'Unknown error')}"
                    for f in results['failed']
                ])
                st.download_button(
                    label="Download TXT",
                    data=failed_text,
                    file_name=f"bulk_upload_failed_{time.strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
    
    # Cleanup
    processor.cleanup_temp_files(temp_dir)
    
    st.success("🎉 Bulk processing complete!")


def create_csv_report(resumes: List[Dict]) -> str:
    """Create CSV report from parsed resumes"""
    import pandas as pd
    import io
    
    data = []
    for resume in resumes:
        data.append({
            'Filename': resume.get('filename', 'N/A'),
            'Name': resume['contact'].get('name', 'N/A'),
            'Email': resume['contact'].get('email', 'N/A'),
            'Phone': resume['contact'].get('phone', 'N/A'),
            'Experience (years)': resume.get('total_experience_years', 0),
            'Num Jobs': len(resume.get('experience', [])),
            'Num Education': len(resume.get('education', [])),
            'Total Skills': sum(len(v) for v in resume.get('skills', {}).values()),
            'Top 3 Skills': ', '.join([
                skill for skills in resume.get('skills', {}).values() 
                for skill in skills
            ][:3])
        })
    
    df = pd.DataFrame(data)
    return df.to_csv(index=False)