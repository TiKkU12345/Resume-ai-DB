"""
Admin Approval Authentication System
 Email whitelist for security
 Email notifications for admin
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
    """Authentication with whitelist and admin approval"""
    
    def __init__(self):
        # Supabase connection
        self.url = get_secret("SUPABASE_URL", "")
        self.key = get_secret("SUPABASE_KEY", "")
        
        if self.url and self.key:
            self.client: Client = create_client(self.url, self.key)
        else:
            self.client = None
            st.error("⚠️ Supabase not configured")
        
        # Admin email
        self.admin_email = get_secret("ADMIN_EMAIL", "admin@example.com")
        
        # 🔒 WHITELIST - Only these emails can signup
        self.allowed_emails = [
            "arunav11a31.hts21@gmail.com",  # Replace with your authorized emails
            "6801788@rungta.org",   # Add more if needed
        ]
        
        # Session state
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'device_id' not in st.session_state:
            st.session_state.device_id = self._generate_device_id()
    
    def _generate_device_id(self) -> str:
        """Generate device ID"""
        try:
            device_info = f"{platform.system()}-{platform.node()}"
            return hashlib.md5(device_info.encode()).hexdigest()
        except:
            import random
            return hashlib.md5(str(random.randint(0, 999999)).encode()).hexdigest()
    
    def sign_up(self, email: str, password: str, full_name: str) -> tuple:
        """User signup - Only whitelisted emails allowed"""
        if not self.client:
            return False, "Authentication not configured"
        
        try:
            # 🔒 SECURITY CHECK: Email whitelist
            if email.lower() not in [e.lower() for e in self.allowed_emails]:
                return False, "⛔ Registration restricted.\n\nOnly authorized personnel can signup.\n\nContact administrator if you need access."
            
            # Validate inputs
            if not full_name.strip():
                return False, "Please enter your full name"
            
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            if not self._validate_password(password):
                return False, "Password must be 8+ chars with letters and numbers"
            
            # Hash password
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Create user record
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
            
            # Check if already exists
            existing = self.client.table('users').select('email').eq('email', email.lower()).execute()
            if existing.data:
                return False, "Email already registered"
            
            # Insert user
            response = self.client.table('users').insert(user_data).execute()
            
            if response.data:
                # Try to send email
                email_sent = self._send_admin_email(email, full_name, st.session_state.device_id)
                
                msg = f"✅ Account created for {full_name}!\n\n⏳ Pending admin approval."
                
                if email_sent:
                    msg += "\n\n📧 Admin notified via email."
                
                return True, msg
            else:
                return False, "Failed to create account"
        
        except Exception as e:
            return False, f"Signup failed: {str(e)}"
    
    def _send_admin_email(self, user_email: str, user_name: str, device_id: str) -> bool:
        """Send email to admin"""
        try:
            # Get SMTP settings
            smtp_server = get_secret("SMTP_SERVER", None)
            smtp_port = get_secret("SMTP_PORT", None)
            sender_email = get_secret("SENDER_EMAIL", None)
            sender_password = get_secret("SENDER_PASSWORD", None)
            
            # Check if configured
            if not all([smtp_server, sender_email, sender_password]):
                print("⚠️ SMTP not configured")
                
                # Log to activity_logs instead
                if self.client:
                    try:
                        self.client.table('activity_logs').insert({
                            'action_type': 'signup_request',
                            'details': {
                                'user_email': user_email,
                                'user_name': user_name,
                                'device_id': device_id,
                                'timestamp': datetime.now().isoformat()
                            },
                            'created_at': datetime.now().isoformat()
                        }).execute()
                    except:
                        pass
                
                return False
            
            # Send email
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            subject = f"🔔 New Signup: {user_name}"
            
            body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2 style="color: #4A90E2;">🆕 New User Signup</h2>
    
    <div style="background: #f5f5f5; padding: 15px; margin: 20px 0;">
        <p><strong>Name:</strong> {user_name}</p>
        <p><strong>Email:</strong> {user_email}</p>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p><strong>Device:</strong> {device_id[:16]}...</p>
    </div>
    
    <h3 style="color: #E74C3C;">Action Required:</h3>
    
    <p>Approve this user:</p>
    
    <div style="background: #282c34; color: #abb2bf; padding: 15px; font-family: monospace;">
<pre>UPDATE users 
SET is_approved = true, 
    approved_at = NOW(), 
    approved_by = '{self.admin_email}',
    approved_devices = ARRAY['{device_id}']
WHERE email = '{user_email}';</pre>
    </div>
    
    <p style="color: #666; font-size: 12px; margin-top: 30px;">
        AI Resume Shortlisting System
    </p>
</body>
</html>
"""
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"Resume System <{sender_email}>"
            msg['To'] = self.admin_email
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            print(f"✅ Email sent to {self.admin_email}")
            return True
            
        except Exception as e:
            print(f"❌ Email failed: {e}")
            return False
    
    def sign_in(self, email: str, password: str) -> tuple:
        """User login"""
        if not self.client:
            return False, "Authentication not configured"
        
        try:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            response = self.client.table('users').select('*').eq('email', email.lower()).eq('password_hash', hashed_password).execute()
            
            if not response.data:
                return False, "❌ Invalid email or password"
            
            user = response.data[0]
            
            if not user.get('is_approved', False):
                return False, "⏳ Account pending admin approval"
            
            current_device = st.session_state.device_id
            approved_devices = user.get('approved_devices', [])
            
            if current_device not in approved_devices:
                self._send_device_alert(email, user['full_name'], current_device)
                return False, f"🔐 New device detected!\n\nAdmin approval required."
            
            st.session_state.user = {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'approved_at': user.get('approved_at')
            }
            
            self.client.table('users').update({
                'last_login': datetime.now().isoformat()
            }).eq('id', user['id']).execute()
            
            return True, f"✅ Welcome, {user['full_name']}!"
        
        except Exception as e:
            return False, f"Login failed: {str(e)}"
    
    def _send_device_alert(self, user_email: str, user_name: str, device_id: str):
        """Send new device alert"""
        try:
            smtp_server = get_secret("SMTP_SERVER", None)
            if not smtp_server:
                return
            
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            subject = f"🔐 New Device: {user_name}"
            body = f"""
<html>
<body>
    <h2>🔐 New Device Login</h2>
    <p><strong>{user_name}</strong> ({user_email}) tried login from new device.</p>
    <p><strong>Device:</strong> {device_id}</p>
    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    
    <h3>Approve:</h3>
    <pre>UPDATE users 
SET approved_devices = array_append(approved_devices, '{device_id}')
WHERE email = '{user_email}';</pre>
</body>
</html>
"""
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = get_secret("SENDER_EMAIL")
            msg['To'] = self.admin_email
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(smtp_server, int(get_secret("SMTP_PORT", 587))) as server:
                server.starttls()
                server.login(get_secret("SENDER_EMAIL"), get_secret("SENDER_PASSWORD"))
                server.send_message(msg)
            
        except Exception as e:
            print(f"Device alert failed: {e}")
    
    def sign_out(self):
        st.session_state.user = None
    
    def is_authenticated(self) -> bool:
        return st.session_state.user is not None
    
    def get_current_user(self):
        return st.session_state.user
    
    def _validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> bool:
        return (len(password) >= 8 and 
                any(c.isalpha() for c in password) and 
                any(c.isdigit() for c in password))


def render_auth_page():
    """Render auth page"""
    auth = AdminApprovalAuth()
    
    if auth.is_authenticated():
        st.success(f"✅ Logged in: {auth.get_current_user()['full_name']}")
        if st.button("Logout", type="primary"):
            auth.sign_out()
            st.rerun()
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1>🎯 AI Resume Shortlisting</h1>
            <p style='color: #666;'>Secure Access | Authorized Personnel Only</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                st.markdown("### Welcome Back!")
                email = st.text_input("Email", placeholder="your.email@company.com")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("🚀 Login", use_container_width=True, type="primary"):
                    if email and password:
                        success, message = auth.sign_in(email, password)
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(message)
        
        with tab2:
            with st.form("signup_form"):
                st.markdown("### Request Access")
                st.warning("🔒 Only authorized emails can register")
                
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                password = st.text_input("Password *", type="password")
                confirm = st.text_input("Confirm Password *", type="password")
                agree = st.checkbox("I understand access is restricted")
                
                if st.form_submit_button("✨ Request Access", use_container_width=True, type="primary"):
                    if not agree:
                        st.error("Please acknowledge")
                    elif password != confirm:
                        st.error("Passwords don't match")
                    elif full_name and email and password:
                        success, message = auth.sign_up(email, password, full_name)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
        
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 12px; padding: 20px;'>
            <p>🔐 Secure Access | Admin Approval Required</p>
            <p>© 2024 AI Resume Shortlisting System</p>
        </div>
        """, unsafe_allow_html=True)


def render_auth_sidebar():
    auth = AdminApprovalAuth()
    with st.sidebar:
        if auth.is_authenticated():
            user = auth.get_current_user()
            st.write(f"**{user['full_name']}**")
            if st.button("Logout"):
                auth.sign_out()
                st.rerun()


def require_auth(func):
    def wrapper(*args, **kwargs):
        auth = AdminApprovalAuth()
        if not auth.is_authenticated():
            st.warning("Please login")
            return
        return func(*args, **kwargs)
    return wrapper
