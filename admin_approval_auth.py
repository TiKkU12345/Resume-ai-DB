"""
Admin Approval Authentication System with Email Notifications
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import hashlib
import re
import platform
import socket
from app_config import get_secret


class AdminApprovalAuth:
    """Authentication with admin approval and email notifications"""
    
    def __init__(self):
        # Supabase connection
        self.url = get_secret("SUPABASE_URL", "")
        self.key = get_secret("SUPABASE_KEY", "")
        
        if self.url and self.key:
            self.client: Client = create_client(self.url, self.key)
        else:
            self.client = None
            st.error("⚠️ Supabase credentials not configured")
        
        # Admin email
        self.admin_email = get_secret("ADMIN_EMAIL", "admin@example.com")
        
        # Session state initialization
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'device_id' not in st.session_state:
            st.session_state.device_id = self._generate_device_id()
    
    def _generate_device_id(self) -> str:
        """Generate unique device identifier"""
        try:
            device_info = f"{platform.system()}-{platform.node()}-{socket.gethostname()}"
            return hashlib.md5(device_info.encode()).hexdigest()
        except:
            import random
            return hashlib.md5(str(random.randint(0, 999999)).encode()).hexdigest()
    
    def sign_up(self, email: str, password: str, full_name: str) -> tuple:
        """User signup with email notification to admin"""
        if not self.client:
            return False, "Authentication not configured"
        
        try:
            # Validate inputs
            if not full_name or full_name.strip() == "":
                return False, "Please enter your full name"
            
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            if not self._validate_password(password):
                return False, "Password must be at least 8 characters with letters and numbers"
            
            # Hash password
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Create user record (NOT approved by default)
            user_data = {
                'email': email.lower(),
                'password_hash': hashed_password,
                'full_name': full_name.strip(),
                'is_approved': False,
                'approved_at': None,
                'approved_by': None,
                'approved_devices': [],
                'signup_date': datetime.now().isoformat(),
                'last_login': None
            }
            
            # Check if user already exists
            existing = self.client.table('users').select('email').eq('email', email.lower()).execute()
            if existing.data:
                return False, "❌ Email already registered. Waiting for admin approval."
            
            # Insert new user
            response = self.client.table('users').insert(user_data).execute()
            
            if response.data:
                # Send email notification to admin
                email_sent = self._send_admin_email(email, full_name, st.session_state.device_id)
                
                success_msg = f"✅ Account created for {full_name}!\n\n⏳ Your account is pending admin approval."
                
                if email_sent:
                    success_msg += "\n\n📧 Admin has been notified via email."
                else:
                    success_msg += "\n\n⚠️ Admin will be notified."
                
                return True, success_msg
            else:
                return False, "Failed to create account"
        
        except Exception as e:
            return False, f"Signup failed: {str(e)}"
    
    def _send_admin_email(self, user_email: str, user_name: str, device_id: str) -> bool:
        """Send email notification to admin"""
        try:
            # Get SMTP settings
            smtp_server = get_secret("SMTP_SERVER", None)
            smtp_port = int(get_secret("SMTP_PORT", 587))
            sender_email = get_secret("SENDER_EMAIL", None)
            sender_password = get_secret("SENDER_PASSWORD", None)
            
            # Check if SMTP is configured
            if not all([smtp_server, sender_email, sender_password]):
                print("⚠️ SMTP not configured. Email notification skipped.")
                return False
            
            # Import email libraries
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create email
            subject = f"🔔 New User Signup: {user_name}"
            
            body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #4A90E2;">🆕 New User Signup Request</h2>
    
    <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <p><strong>Name:</strong> {user_name}</p>
        <p><strong>Email:</strong> {user_email}</p>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Device ID:</strong> {device_id[:16]}...</p>
    </div>
    
    <h3 style="color: #E74C3C;">⚡ Action Required:</h3>
    
    <p>To approve this user, follow these steps:</p>
    
    <ol>
        <li>Go to <a href="https://supabase.com/dashboard">Supabase Dashboard</a></li>
        <li>Open <strong>SQL Editor</strong></li>
        <li>Run this query:</li>
    </ol>
    
    <div style="background: #282c34; color: #abb2bf; padding: 15px; border-radius: 5px; margin: 15px 0; font-family: 'Courier New', monospace;">
<pre>UPDATE users 
SET is_approved = true, 
    approved_at = NOW(), 
    approved_by = '{self.admin_email}',
    approved_devices = ARRAY['{device_id}']
WHERE email = '{user_email}';</pre>
    </div>
    
    <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
    
    <p style="color: #666; font-size: 12px;">
        This is an automated email from <strong>AI Resume Shortlisting System</strong>.<br>
        Do not reply to this email.
    </p>
</body>
</html>
"""
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"AI Resume System <{sender_email}>"
            msg['To'] = self.admin_email
            
            # Attach HTML body
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            print(f"✅ Email notification sent to {self.admin_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    def sign_in(self, email: str, password: str) -> tuple:
        """User login with admin approval and device verification"""
        if not self.client:
            return False, "Authentication not configured"
        
        try:
            # Hash password
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Check user exists and credentials match
            response = self.client.table('users').select('*').eq('email', email.lower()).eq('password_hash', hashed_password).execute()
            
            if not response.data:
                return False, "❌ Invalid email or password"
            
            user = response.data[0]
            
            # CHECK 1: Is user approved by admin?
            if not user.get('is_approved', False):
                return False, "⏳ Your account is pending admin approval.\n\nPlease wait for the administrator to approve your access."
            
            # CHECK 2: Is this device approved?
            current_device = st.session_state.device_id
            approved_devices = user.get('approved_devices', [])
            
            if current_device not in approved_devices:
                # Send new device notification
                self._send_device_alert(email, user['full_name'], current_device)
                return False, f"🔐 New device detected!\n\nThis device needs admin approval.\n\nAn alert has been sent to admin."
            
            # All checks passed - Login successful
            st.session_state.user = {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'approved_at': user.get('approved_at')
            }
            
            # Update last login
            self.client.table('users').update({
                'last_login': datetime.now().isoformat()
            }).eq('id', user['id']).execute()
            
            return True, f"✅ Welcome back, {user['full_name']}!"
        
        except Exception as e:
            return False, f"Login failed: {str(e)}"
    
    def _send_device_alert(self, user_email: str, user_name: str, device_id: str):
        """Send alert for new device login attempt"""
        try:
            smtp_server = get_secret("SMTP_SERVER", None)
            smtp_port = int(get_secret("SMTP_PORT", 587))
            sender_email = get_secret("SENDER_EMAIL", None)
            sender_password = get_secret("SENDER_PASSWORD", None)
            
            if not all([smtp_server, sender_email, sender_password]):
                return
            
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            subject = f"🔐 New Device Login: {user_name}"
            
            body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2 style="color: #E74C3C;">🔐 New Device Login Attempt</h2>
    
    <p><strong>{user_name}</strong> ({user_email}) tried to login from a new device.</p>
    
    <div style="background: #f5f5f5; padding: 15px; margin: 20px 0;">
        <p><strong>Device ID:</strong> {device_id}</p>
        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <h3>To approve this device:</h3>
    
    <div style="background: #282c34; color: #abb2bf; padding: 15px;">
<pre>UPDATE users 
SET approved_devices = array_append(approved_devices, '{device_id}')
WHERE email = '{user_email}';</pre>
    </div>
</body>
</html>
"""
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = self.admin_email
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            print(f"✅ Device alert sent for {user_name}")
            
        except Exception as e:
            print(f"❌ Device alert failed: {e}")
    
    def sign_out(self):
        """Logout user"""
        st.session_state.user = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.user is not None
    
    def get_current_user(self):
        """Get current authenticated user"""
        return st.session_state.user
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> bool:
        """Validate password strength"""
        return (len(password) >= 8 and 
                any(c.isalpha() for c in password) and 
                any(c.isdigit() for c in password))


# Keep render_auth_page, render_auth_sidebar, require_auth same as before
def render_auth_page():
    """Render authentication page"""
    auth = AdminApprovalAuth()
    
    if auth.is_authenticated():
        st.success(f"✅ Logged in as: {auth.get_current_user()['full_name']}")
        if st.button("Logout", type="primary"):
            auth.sign_out()
            st.rerun()
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1>🎯 AI Resume Shortlisting</h1>
            <p style='color: #666;'>Sign in to access your recruitment dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                st.markdown("### Welcome Back!")
                email = st.text_input("Email", placeholder="your.email@company.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                
                if st.form_submit_button("🚀 Login", use_container_width=True, type="primary"):
                    if email and password:
                        with st.spinner("Signing in..."):
                            success, message = auth.sign_in(email, password)
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(message)
        
        with tab2:
            with st.form("signup_form"):
                st.markdown("### Create Account")
                st.info("🔒 Account will be reviewed by admin")
                
                full_name = st.text_input("Full Name *", placeholder="John Doe")
                email = st.text_input("Email *", placeholder="your.email@company.com")
                password = st.text_input("Password *", type="password", placeholder="••••••••")
                confirm_password = st.text_input("Confirm Password *", type="password")
                agree = st.checkbox("I understand that my access is subject to admin approval")
                
                if st.form_submit_button("✨ Create Account", use_container_width=True, type="primary"):
                    if not agree:
                        st.error("Please acknowledge approval requirement")
                    elif password != confirm_password:
                        st.error("Passwords don't match")
                    elif full_name and email and password:
                        with st.spinner("Creating account..."):
                            success, message = auth.sign_up(email, password, full_name)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
        
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 12px; padding: 20px 0;'>
            <p>🔐 Secure Access | Admin Approval Required</p>
            <p>© 2024 AI Resume Shortlisting System</p>
        </div>
        """, unsafe_allow_html=True)


def render_auth_sidebar():
    """Render auth in sidebar"""
    auth = AdminApprovalAuth()
    with st.sidebar:
        if auth.is_authenticated():
            user = auth.get_current_user()
            st.write(f"**{user['full_name']}**")
            if st.button("Logout"):
                auth.sign_out()
                st.rerun()


def require_auth(func):
    """Auth decorator"""
    def wrapper(*args, **kwargs):
        auth = AdminApprovalAuth()
        if not auth.is_authenticated():
            st.warning("Please login")
            return
        return func(*args, **kwargs)
    return wrapper
