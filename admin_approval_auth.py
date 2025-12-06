"""
Admin Approval Authentication System
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
    """Authentication with admin approval"""
    
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
        """User signup"""
        if not self.client:
            return False, "Authentication not configured"
        
        try:
            if not full_name.strip():
                return False, "Please enter your full name"
            
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            if not self._validate_password(password):
                return False, "Password must be 8+ chars with letters and numbers"
            
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
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
            
            existing = self.client.table('users').select('email').eq('email', email.lower()).execute()
            if existing.data:
                return False, "Email already registered"
            
            response = self.client.table('users').insert(user_data).execute()
            
            if response.data:
                return True, f"✅ Account created!\n\n⏳ Pending admin approval."
            else:
                return False, "Failed to create account"
        
        except Exception as e:
            return False, f"Signup failed: {str(e)}"
    
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
                return False, f"🔐 New device detected!\n\nDevice needs admin approval."
            
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
    
    def sign_out(self):
        """Logout"""
        st.session_state.user = None
    
    def is_authenticated(self) -> bool:
        """Check auth"""
        return st.session_state.user is not None
    
    def get_current_user(self):
        """Get current user"""
        return st.session_state.user
    
    def _validate_email(self, email: str) -> bool:
        """Validate email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> bool:
        """Validate password"""
        return (len(password) >= 8 and 
                any(c.isalpha() for c in password) and 
                any(c.isdigit() for c in password))

    def render_auth_page():
    """Render authentication page (centered & styled)"""
    
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
                            st.info("You can now login once approved!")
                        else:
                            st.error(message)
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 12px;'>
            <p>🔐 Secure Access | Admin Approval Required</p>
            <p>Powered by AI & Machine Learning</p>
            <p>© 2024 AI Resume Shortlisting System. All rights reserved.</p>
        </div>
        """, unsafe_allow_html=True)

    
    with tab2:
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Sign Up", type="primary"):
                if password != confirm:
                    st.error("Passwords don't match")
                elif name and email and password:
                    success, message = auth.sign_up(email, password, name)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)


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

