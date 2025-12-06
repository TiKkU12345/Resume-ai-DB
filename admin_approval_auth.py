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
    """Render auth page"""
    auth = AdminApprovalAuth()
    
    if auth.is_authenticated():
        st.success(f"Logged in as: {auth.get_current_user()['full_name']}")
        if st.button("Logout"):
            auth.sign_out()
            st.rerun()
        return
    
    st.title("🎯 AI Resume Shortlisting")
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login", type="primary"):
                if email and password:
                    success, message = auth.sign_in(email, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
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
