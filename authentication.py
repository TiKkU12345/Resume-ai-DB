"""
Authentication Module with Supabase
User login, signup, and session management with Name field
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import re

class AuthManager:
    """Handle user authentication with Supabase"""
    
    def __init__(self):
        # Get Supabase credentials
        self.url = st.secrets.get("SUPABASE_URL", "")
        self.key = st.secrets.get("SUPABASE_KEY", "")
        
        if self.url and self.key:
            self.client: Client = create_client(self.url, self.key)
        else:
            self.client = None
        
        # Initialize session state
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'access_token' not in st.session_state:
            st.session_state.access_token = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.user is not None
    
    def get_current_user(self):
        """Get current authenticated user"""
        return st.session_state.user
    
    def sign_up(self, email: str, password: str, full_name: str = "") -> tuple:
        """Register new user - Only allowed emails can signup"""
        if not self.client:
            return False, "Authentication not configured"
        
        try:
            # SECURITY: Only allow specific email(s) to signup
            ALLOWED_EMAILS = [
                "arunav11a31.hts21@gmail.com",  # 
                "arunav.jsr.0604@gmail.com", 
            ]
            
            if email.lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return False, "⛔ Signup restricted. Only authorized emails can register."
            
            # Validate inputs
            if not full_name or full_name.strip() == "":
                return False, "Please enter your full name"
            
            if not self._validate_email(email):
                return False, "Invalid email format"
            
            if not self._validate_password(password):
                return False, "Password must be at least 8 characters with letters and numbers"
            
            # Sign up with Supabase Auth
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name.strip()
                    }
                }
            })
            
            if response.user:
                return True, f"Welcome {full_name}! Please check your email to verify your account."
            else:
                return False, "Failed to create account"
        
        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower():
                return False, "Email already registered"
            return False, f"Signup failed: {error_msg}"
    
    def sign_in(self, email: str, password: str) -> tuple:
        """Login user"""
        if not self.client:
            return False, "Authentication not configured"
        
        try:
            # Sign in with Supabase Auth
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Store in session
                st.session_state.user = {
                    'id': response.user.id,
                    'email': response.user.email,
                    'full_name': response.user.user_metadata.get('full_name', ''),
                    'created_at': response.user.created_at
                }
                st.session_state.access_token = response.session.access_token
                
                return True, f"Welcome back, {st.session_state.user['full_name']}!"
            else:
                return False, "Invalid credentials"
        
        except Exception as e:
            error_msg = str(e)
            if "invalid" in error_msg.lower():
                return False, "Invalid email or password"
            return False, f"Login failed: {error_msg}"
    
    def sign_out(self):
        """Logout user"""
        if self.client:
            try:
                self.client.auth.sign_out()
            except:
                pass
        
        # Clear session
        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.parsed_resumes = []
        st.session_state.ranked_candidates = []
    
    def reset_password(self, email: str) -> tuple:
        """Send password reset email"""
        if not self.client:
            return False, "Authentication not configured"
        
        try:
            self.client.auth.reset_password_for_email(email)
            return True, "Password reset email sent! Check your inbox."
        except Exception as e:
            return False, f"Failed to send reset email: {str(e)}"
    
    def update_profile(self, full_name: str) -> tuple:
        """Update user profile"""
        if not self.client or not st.session_state.user:
            return False, "Not authenticated"
        
        try:
            if not full_name or full_name.strip() == "":
                return False, "Name cannot be empty"
            
            self.client.auth.update_user({
                "data": {
                    "full_name": full_name.strip()
                }
            })
            
            st.session_state.user['full_name'] = full_name.strip()
            return True, "Profile updated successfully!"
        except Exception as e:
            return False, f"Update failed: {str(e)}"
    
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
    """Render authentication page (login/signup)"""
    
    auth_manager = AuthManager()
    
    # Check if already authenticated
    if auth_manager.is_authenticated():
        render_profile_page(auth_manager)
        return
    
    # Center the auth form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
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
                            success, message = auth_manager.sign_in(email, password)
                        
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill in all fields")
                
                if forgot:
                    if email:
                        success, message = auth_manager.reset_password(email)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Please enter your email")
        
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
                    "I agree to the Terms of Service and Privacy Policy",
                    key="agree_terms"
                )
                
                submit = st.form_submit_button(
                    "✨ Create Account",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit:
                    if not agree:
                        st.error("Please agree to the terms")
                    elif not all([full_name, email, password, confirm_password]):
                        st.error("Please fill in all fields")
                    elif password != confirm_password:
                        st.error("Passwords don't match")
                    else:
                        with st.spinner("Creating account..."):
                            success, message = auth_manager.sign_up(email, password, full_name)
                        
                        if success:
                            st.success(message)
                            st.info("📧 Check your email to verify your account, then login!")
                        else:
                            st.error(message)
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 12px;'>
            <p>Powered by AI & Machine Learning</p>
            <p>© 2025 Resume Shortlisting System</p>
        </div>
        """, unsafe_allow_html=True)


def render_profile_page(auth_manager: AuthManager):
    """Render user profile page"""
    
    user = auth_manager.get_current_user()
    
    st.header("👤 User Profile")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Profile info
        st.markdown("### Account Information")
        
        with st.form("profile_form"):
            full_name = st.text_input(
                "Full Name",
                value=user.get('full_name', ''),
                key="profile_name"
            )
            
            st.text_input(
                "Email",
                value=user.get('email', ''),
                disabled=True,
                help="Email cannot be changed"
            )
            
            st.text_input(
                "Member Since",
                value=user.get('created_at', '')[:10] if user.get('created_at') else 'N/A',
                disabled=True
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                update = st.form_submit_button(
                    "💾 Update Profile",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_b:
                logout = st.form_submit_button(
                    "🚪 Logout",
                    use_container_width=True
                )
            
            if update:
                if full_name:
                    success, message = auth_manager.update_profile(full_name)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            
            if logout:
                auth_manager.sign_out()
                st.success("Logged out successfully!")
                st.rerun()
    
    with col2:
        st.markdown("### Quick Stats")
        
        # Get user stats from database if available
        st.metric("Resumes Processed", len(st.session_state.get('parsed_resumes', [])))
        st.metric("Jobs Analyzed", len(st.session_state.get('ranked_candidates', [])) > 0)


def require_auth(func):
    """Decorator to require authentication for a page"""
    def wrapper(*args, **kwargs):
        auth_manager = AuthManager()
        
        if not auth_manager.is_authenticated():
            st.warning("⚠️ Please login to access this feature")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                if st.button("🔐 Go to Login", use_container_width=True, type="primary"):
                    st.session_state.page = 'Login'
                    st.rerun()
            
            return
        
        return func(*args, **kwargs)
    
    return wrapper


def render_auth_sidebar():
    """Render auth status in sidebar"""
    
    auth_manager = AuthManager()
    
    with st.sidebar:
        st.markdown("---")
        
        if auth_manager.is_authenticated():
            user = auth_manager.get_current_user()
            
            st.markdown("### 👤 Logged In")
            st.write(f"**{user.get('full_name', 'User')}**")
            st.caption(user.get('email', ''))
            
            if st.button("🚪 Logout", use_container_width=True):
                auth_manager.sign_out()
                st.success("Logged out!")
                st.rerun()
        else:
            st.markdown("### 🔐 Not Logged In")
            
            if st.button("Login / Sign Up", use_container_width=True, type="primary"):
                st.session_state.page = 'Login'
                st.rerun()
