import streamlit as st
from email_integration import EmailManager

def test_email():
    """Test email configuration"""
    st.title("📧 Email Configuration Test")
    
    try:
        # Initialize email manager
        email_mgr = EmailManager()
        st.success("✅ Email manager initialized successfully")
        
        # Show configuration (hide password)
        st.info(f"""
        **Configuration:**
        - SMTP Server: {email_mgr.smtp_server}
        - SMTP Port: {email_mgr.smtp_port}
        - Sender Email: {email_mgr.sender_email}
        - Sender Name: {email_mgr.sender_name}
        """)
        
        # Test email form
        st.markdown("---")
        st.markdown("### Send Test Email")
        
        test_email_address = st.text_input(
            "Send test email to:",
            value=email_mgr.sender_email,
            help="Enter your email address to receive a test email"
        )
        
        if st.button("📤 Send Test Email", type="primary"):
            with st.spinner("Sending email..."):
                success, message = email_mgr.send_email(
                    to_email=test_email_address,
                    subject="✅ Test Email from AI Resume System",
                    body_html="""
                    <html>
                        <body>
                            <h1 style="color: #667eea;">Success!</h1>
                            <p>Your email configuration is working correctly.</p>
                            <p>You can now send emails to candidates from the AI Resume Shortlisting System.</p>
                            <br>
                            <p style="color: #666;">Sent from AI Resume Shortlisting System</p>
                        </body>
                    </html>
                    """,
                    body_text="Success! Your email configuration is working correctly."
                )
                
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                    st.info(f"Check your inbox: {test_email_address}")
                else:
                    st.error(f"❌ {message}")
        
    except ValueError as e:
        st.error(f"❌ Configuration Error: {str(e)}")
        st.info("""
        **Please update your `.streamlit/secrets.toml` file with:**
```toml
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        SENDER_EMAIL = "your-email@gmail.com"
        SENDER_PASSWORD = "your-app-password"
        SENDER_NAME = "HR Team"
```
        """)
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_email()