"""
Email Integration Module
Handles sending emails to candidates with Gmail SMTP
"""

import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time


class EmailManager:
    """Manages email sending functionality"""
    
    def __init__(self):
        """Initialize email manager with configuration from Streamlit secrets"""
        try:
            self.smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
            self.smtp_port = int(st.secrets.get("SMTP_PORT", 587))
            self.sender_email = st.secrets["SENDER_EMAIL"]
            self.sender_password = st.secrets["SENDER_PASSWORD"]
            self.sender_name = st.secrets.get("SENDER_NAME", "HR Team")
            self.company_name = st.secrets.get("COMPANY_NAME", "Our Company")
        except KeyError as e:
            raise ValueError(f"Missing email configuration in secrets: {e}")
    
    def validate_config(self):
        """Validate email configuration"""
        if not self.sender_email:
            return False, "Sender email not configured"
        if not self.sender_password:
            return False, "Sender password not configured"
        if len(self.sender_password) < 10:
            return False, "Password too short - use Gmail App Password (16 characters)"
        return True, "Configuration valid"
    
    def send_email(self, to_email, subject, body_html, body_text=None):
        """
        Send a single email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach body parts
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()  # Secure the connection
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            return True, "Email sent successfully"
            
        except smtplib.SMTPAuthenticationError as e:
            return False, f"Authentication failed: {str(e)}. Please check your App Password."
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {str(e)}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    def send_bulk_emails(self, recipients, subject_template, body_template_html, body_template_text=None, delay=1):
        """
        Send emails to multiple recipients
        
        Args:
            recipients: List of dicts with candidate info
            subject_template: Subject line (can include {name}, {position})
            body_template_html: HTML body template
            body_template_text: Plain text body template (optional)
            delay: Delay between emails in seconds
        
        Returns:
            list: Results for each email
        """
        results = []
        
        for i, recipient in enumerate(recipients):
            # Replace placeholders
            subject = subject_template.format(
                name=recipient.get('name', 'Candidate'),
                position=recipient.get('position', 'Position')
            )
            
            body_html = body_template_html.format(
                name=recipient.get('name', 'Candidate'),
                position=recipient.get('position', 'Position'),
                company=self.company_name
            )
            
            body_text = None
            if body_template_text:
                body_text = body_template_text.format(
                    name=recipient.get('name', 'Candidate'),
                    position=recipient.get('position', 'Position'),
                    company=self.company_name
                )
            
            # Send email
            success, message = self.send_email(
                recipient['email'],
                subject,
                body_html,
                body_text
            )
            
            results.append({
                'name': recipient.get('name', 'Unknown'),
                'email': recipient['email'],
                'success': success,
                'message': message
            })
            
            # Delay to avoid rate limiting
            if i < len(recipients) - 1:
                time.sleep(delay)
        
        return results


def render_email_panel(ranked_candidates, job_title="Position"):
    """
    Render the email sending interface in Streamlit
    
    Args:
        ranked_candidates: List of ranked candidate dictionaries
        job_title: Job position title
    """
    st.header("📧 Send Emails to Candidates")
    
    # Check email configuration
    try:
        email_mgr = EmailManager()
        is_valid, validation_msg = email_mgr.validate_config()
        
        if not is_valid:
            st.error(f"⚠️ Email not configured: {validation_msg}")
            st.info("""
            **Please add email credentials to `.streamlit/secrets.toml`:**
            
            ```toml
            SENDER_EMAIL = "your-email@gmail.com"
            SENDER_PASSWORD = "your-app-password"
            SENDER_NAME = "HR Team"
            COMPANY_NAME = "Your Company"
            SMTP_SERVER = "smtp.gmail.com"
            SMTP_PORT = 587
            ```
            
            **For Gmail, use App Password:** https://support.google.com/accounts/answer/185833
            """)
            return
        
        st.success("✅ Email configuration loaded successfully")
        
    except ValueError as e:
        st.error(f"⚠️ {str(e)}")
        st.info("Please add email credentials to `.streamlit/secrets.toml`")
        return
    
    st.markdown("---")
    
    # Email template selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        email_type = st.selectbox(
            "Email Type",
            ["Interview Invitation", "Rejection (Polite)", "Request for More Info", "Custom"]
        )
    
    with col2:
        st.metric("Recipients Available", len(ranked_candidates))
    
    # Filter candidates
    st.markdown("### Select Recipients")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        min_score = st.slider(
            "Minimum Score",
            0, 100, 70, 5,
            help="Only send to candidates above this score"
        )
    
    with col_b:
        max_recipients = st.number_input(
            "Max Recipients",
            1, len(ranked_candidates), 
            min(5, len(ranked_candidates)),
            help="Maximum number of emails to send"
        )
    
    # Filter candidates based on score
    filtered_candidates = [
        c for c in ranked_candidates 
        if c['overall_score'] >= min_score
    ][:max_recipients]
    
    if not filtered_candidates:
        st.warning(f"No candidates match the criteria (score >= {min_score})")
        return
    
    st.info(f"📨 Will send to {len(filtered_candidates)} candidate(s)")
    
    # Show selected candidates
    with st.expander(f"👥 View Selected Candidates ({len(filtered_candidates)})"):
        for i, candidate in enumerate(filtered_candidates, 1):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"{i}. {candidate['name']}")
            with col2:
                st.write(f"📧 {candidate['email']}")
            with col3:
                st.write(f"⭐ {candidate['overall_score']:.1f}%")
    
    st.markdown("---")
    
    # Email templates
    templates = get_email_templates()
    
    if email_type == "Custom":
        subject = st.text_input("Subject Line", "Regarding Your Application")
        
        body = st.text_area(
            "Email Body (HTML supported)",
            height=300,
            value=templates['custom']['html'],
            help="Use {name} for candidate name, {position} for job title, {company} for company name"
        )
    else:
        template_key = email_type.lower().replace(" ", "_").replace("(", "").replace(")", "")
        template = templates.get(template_key, templates['interview_invitation'])
        
        subject = st.text_input(
            "Subject Line",
            value=template['subject'].format(position=job_title)
        )
        
        st.markdown("### Email Preview")
        body = st.text_area(
            "Email Body",
            height=300,
            value=template['html'],
            help="You can edit the template"
        )
    
    # Preview
    with st.expander("👁️ Preview Email"):
        st.markdown("**Subject:** " + subject)
        st.markdown("---")
        preview_html = body.format(
            name="John Doe",
            position=job_title,
            company=email_mgr.company_name
        )
        st.markdown(preview_html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Send emails
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        send_button = st.button(
            f"📤 Send to {len(filtered_candidates)} Candidate(s)",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        delay = st.number_input("Delay (sec)", 1, 10, 2, help="Delay between emails")
    
    with col3:
        test_mode = st.checkbox("Test Mode", help="Send only to yourself")
    
    if send_button:
        if test_mode:
            st.info("🧪 Test Mode: Sending to yourself only")
            recipients = [{
                'name': 'Test User',
                'email': email_mgr.sender_email,
                'position': job_title
            }]
        else:
            recipients = [
                {
                    'name': c['name'],
                    'email': c['email'],
                    'position': job_title
                }
                for c in filtered_candidates
            ]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        
        for i, recipient in enumerate(recipients):
            status_text.text(f"Sending to {recipient['name']} ({recipient['email']})...")
            
            success, message = email_mgr.send_email(
                recipient['email'],
                subject.format(name=recipient['name'], position=job_title),
                body.format(name=recipient['name'], position=job_title, company=email_mgr.company_name)
            )
            
            results.append({
                'name': recipient['name'],
                'email': recipient['email'],
                'success': success,
                'message': message
            })
            
            progress_bar.progress((i + 1) / len(recipients))
            
            if i < len(recipients) - 1:
                time.sleep(delay)
        
        status_text.empty()
        progress_bar.empty()
        
        # Show results
        st.markdown("---")
        st.markdown("### 📊 Sending Results")
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ Successful", successful)
        with col2:
            st.metric("❌ Failed", failed)
        
        # Detailed results
        with st.expander("📋 Detailed Results"):
            for result in results:
                if result['success']:
                    st.success(f"✅ {result['name']} ({result['email']}): {result['message']}")
                else:
                    st.error(f"❌ {result['name']} ({result['email']}): {result['message']}")
        
        if successful == len(results):
            st.balloons()
            st.success(f"🎉 All {len(results)} emails sent successfully!")
        elif successful > 0:
            st.warning(f"⚠️ {successful}/{len(results)} emails sent. Check errors above.")
        else:
            st.error("❌ All emails failed to send. Please check your configuration.")


def get_email_templates():
    """Get predefined email templates"""
    return {
        'interview_invitation': {
            'subject': 'Interview Invitation - {position}',
            'html': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #667eea;">Interview Invitation</h2>
        
        <p>Dear {name},</p>
        
        <p>We are pleased to inform you that your application for the position of <strong>{position}</strong> 
        at {company} has been shortlisted.</p>
        
        <p>We would like to invite you for an interview to discuss your application further.</p>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p><strong>Interview Details:</strong></p>
            <ul>
                <li>Date: [To be confirmed]</li>
                <li>Time: [To be confirmed]</li>
                <li>Duration: 30-45 minutes</li>
                <li>Format: [Video Call / In-person]</li>
            </ul>
        </div>
        
        <p>Please reply to this email with your availability for the upcoming week.</p>
        
        <p>We look forward to speaking with you!</p>
        
        <p>Best regards,<br>
        <strong>{company} HR Team</strong></p>
    </div>
</body>
</html>
            """
        },
        'rejection_polite': {
            'subject': 'Update on Your Application - {position}',
            'html': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #667eea;">Application Update</h2>
        
        <p>Dear {name},</p>
        
        <p>Thank you for your interest in the <strong>{position}</strong> position at {company} 
        and for taking the time to apply.</p>
        
        <p>After careful consideration, we regret to inform you that we will not be moving forward 
        with your application at this time. We received many strong applications, and the competition 
        was very competitive.</p>
        
        <p>We appreciate your interest in {company} and encourage you to apply for future openings 
        that match your skills and experience.</p>
        
        <p>We wish you all the best in your job search and future professional endeavors.</p>
        
        <p>Best regards,<br>
        <strong>{company} HR Team</strong></p>
    </div>
</body>
</html>
            """
        },
        'request_for_more_info': {
            'subject': 'Additional Information Needed - {position}',
            'html': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #667eea;">Additional Information Required</h2>
        
        <p>Dear {name},</p>
        
        <p>Thank you for your application for the <strong>{position}</strong> position at {company}.</p>
        
        <p>We are reviewing your application and would like to request some additional information:</p>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <ul>
                <li>Portfolio or work samples (if applicable)</li>
                <li>References (2-3 professional references)</li>
                <li>Expected salary range</li>
                <li>Earliest start date</li>
            </ul>
        </div>
        
        <p>Please send the requested information at your earliest convenience.</p>
        
        <p>Thank you for your cooperation!</p>
        
        <p>Best regards,<br>
        <strong>{company} HR Team</strong></p>
    </div>
</body>
</html>
            """
        },
        'custom': {
            'subject': 'Regarding Your Application',
            'html': """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <p>Dear {name},</p>
        
        <p>Thank you for your application for the <strong>{position}</strong> position at {company}.</p>
        
        <p>[Your custom message here]</p>
        
        <p>Best regards,<br>
        <strong>{company} HR Team</strong></p>
    </div>
</body>
</html>
            """
        }
    }