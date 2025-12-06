"""
Admin Approval Authentication System
- Users can signup but cannot login until admin approves
- New device login requires admin confirmation
- Full control for admin
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
    """Authentication with admin approval and device verification"""
    
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
        """User signup - Account created but NOT approved"""
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
                return True, f"✅ Account created for {full_name}!\n\n⏳ Your account is pending admin approval.\n\nYou'll be able to login once approved by the administrator."
            else:
                return False, "Failed to create account"
        
        except Exception as e:
            return False, f"Signup failed: {str(e)}"
    
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
                return False, "⏳ Your account is pending admin approval.\n\nPlease wait for the administrator to approve your access.\n\nContact admin if you've been waiting for more than 24 hours."
            
            # CHECK 2: Is this device approved?
            current_device = st.session_state.device_id
            approved_devices = user.get('approved_devices', [])
            
            if current_device not in approved_devices:
                return False, f"🔐 New device detected!\n\nThis device needs admin approval.\n\nDevice ID: {current_device[:8]}...\n\nPlease contact admin for approval."
            
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
    
    def sign_out(self):
        """Logout user"""
        st.session_state.user = None
        if 'parsed_resumes' in st.session_state:
            st.session_state.parsed_resumes = []
        if 'ranked_candidates' in st.session_state:
            st.session_state.ranked_candidates = []
    
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


def render_auth_page():
    """Render authentication page (centered & professional)"""
    
    auth = AdminApprovalAuth()
    
    if auth.is_authenticated():
        st.success(f"✅ Logged in as: {auth.get_current_user()['full_name']}")
        if st.button("Logout", type="primary"):
            auth.sign_out()
            st.rerun()
        return
    
    # Center the auth form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Header
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1>🎯 AI Resume Shortlisting</h1>
            <p style='color: #666;'>Sign in to access your recruitment dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs for login/signup
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
        
        # Login Tab
        with tab1:
            with st.form("login_form"):
                st.markdown("### Welcome Back!")
                
                email = st.text_input(
                    "Email",
                    placeholder="your.email@company.com",
                    key="login_email"
                )
                
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="••••••••",
                    key="login_password"
                )
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    submit = st.form_submit_button(
                        "🚀 Login",
                        use_container_width=True,
                        type="primary"
                    )
                
                with col_b:
                    forgot = st.form_submit_button(
                        "Forgot Password?",
                        use_container_width=True
                    )
                
                if submit:
                    if email and password:
                        with st.spinner("Signing in..."):
                            success, message = auth.sign_in(email, password)
                        
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill in all fields")
                
                if forgot:
                    st.info("Please contact admin for password reset")
        
        # Signup Tab
        with tab2:
            with st.form("signup_form"):
                st.markdown("### Create Account")
                st.info("🔒 Your account will be reviewed by admin before granting access")
                
                full_name = st.text_input(
                    "Full Name *",
                    placeholder="John Doe",
                    key="signup_name",
                    help="Your name will be displayed in the system"
                )
                
                email = st.text_input(
                    "Email *",
                    placeholder="your.email@company.com",
                    key="signup_email"
                )
                
                password = st.text_input(
                    "Password *",
                    type="password",
                    placeholder="••••••••",
                    help="At least 8 characters with letters and numbers",
                    key="signup_password"
                )
                
                confirm_password = st.text_input(
                    "Confirm Password *",
                    type="password",
                    placeholder="••••••••",
                    key="signup_confirm"
                )
                
                agree = st.checkbox(
                    "I understand that my access is subject to admin approval",
                    key="agree_terms"
                )
                
                submit = st.form_submit_button(
                    "✨ Create Account",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit:
                    if not agree:
                        st.error("Please acknowledge the approval requirement")
                    elif not all([full_name, email, password, confirm_password]):
                        st.error("Please fill in all fields")
                    elif password != confirm_password:
                        st.error("Passwords don't match")
                    else:
                        with st.spinner("Creating account..."):
                            success, message = auth.sign_up(email, password, full_name)
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 12px; padding: 20px 0;'>
            <p style='margin: 5px 0;'>🔐 Secure Access | Admin Approval Required</p>
            <p style='margin: 5px 0;'>Powered by AI & Machine Learning</p>
            <p style='margin: 5px 0;'>© 2024 AI Resume Shortlisting System. All rights reserved.</p>
        </div>
        """, unsafe_allow_html=True)


def render_auth_sidebar():
    """Render auth status in sidebar"""
    
    auth = AdminApprovalAuth()
    
    with st.sidebar:
        st.markdown("---")
        
        if auth.is_authenticated():
            user = auth.get_current_user()
            
            st.markdown("### 👤 Logged In")
            st.write(f"**{user.get('full_name', 'User')}**")
            st.caption(user.get('email', ''))
            
            if st.button("🚪 Logout", use_container_width=True):
                auth.sign_out()
                st.success("Logged out!")
                st.rerun()
        else:
            st.markdown("### 🔐 Not Logged In")
            
            if st.button("Login / Sign Up", use_container_width=True, type="primary"):
                st.session_state.page = 'Login'
                st.rerun()


def require_auth(func):
    """Decorator to require authentication for a page"""
    def wrapper(*args, **kwargs):
        auth = AdminApprovalAuth()
        
        if not auth.is_authenticated():
            st.warning("⚠️ Please login to access this feature")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                if st.button("🔐 Go to Login", use_container_width=True, type="primary"):
                    st.session_state.page = 'Login'
                    st.rerun()
            
            return
        
        return func(*args, **kwargs)
    
    return wrapper
