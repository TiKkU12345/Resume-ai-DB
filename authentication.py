"""
Authentication Module for AI Resume Shortlisting System
Handles user signup, login, and session management
"""

import streamlit as st
from supabase import create_client, Client
import hashlib
from datetime import datetime


def get_supabase_client():
    """Get Supabase client from secrets"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


class AuthManager:
    """Manages user authentication"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def signup(self, email, password):
        """
        Sign up a new user
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Sign up with Supabase Auth
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Check if email confirmation is required
                if response.session:
                    return True, "Account created successfully! You can now login."
                else:
                    return True, "Account created! Please check your email to verify your account."
            else:
                return False, "Failed to create account. Please try again."
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific errors
            if "User already registered" in error_msg:
                return False, "This email is already registered. Please login instead."
            elif "Invalid email" in error_msg:
                return False, "Invalid email address format."
            elif "Password should be at least" in error_msg:
                return False, "Password must be at least 6 characters long."
            elif "SMTP" in error_msg or "email" in error_msg.lower():
                # Email service issue - create user anyway
                st.warning("⚠️ Email service unavailable. Your account is created but email verification is disabled.")
                return True, "Account created! You can login directly (email verification skipped)."
            else:
                return False, f"Signup failed: {error_msg}"
    
    def login(self, email, password):
        """
        Login user
        
        Returns:
            tuple: (success: bool, message: str, user: dict)
        """
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                # Store in session state
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.user_id = response.user.id
                
                return True, "Login successful!", response.user
            else:
                return False, "Login failed. Please check your credentials.", None
                
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific errors
            if "Invalid login credentials" in error_msg:
                return False, "Invalid email or password.", None
            elif "Email not confirmed" in error_msg:
                return False, "Please verify your email before logging in. Check your inbox.", None
            else:
                return False, f"Login failed: {error_msg}", None
    
    def logout(self):
        """Logout current user"""
        try:
            self.supabase.auth.sign_out()
            
            # Clear session state
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            
            return True, "Logged out successfully"
        except Exception as e:
            return False, f"Logout failed: {str(e)}"
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_current_user(self):
        """Get current user info"""
        try:
            user = self.supabase.auth.get_user()
            return user
        except:
            return None
    
    def reset_password(self, email):
        """
        Send password reset email
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            self.supabase.auth.reset_password_for_email(email)
            return True, "Password reset email sent! Check your inbox."
        except Exception as e:
            return False, f"Failed to send reset email: {str(e)}"
    
    def resend_verification(self, email):
        """
        Resend verification email
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            self.supabase.auth.resend(
                type='signup',
                email=email
            )
            return True, "Verification email sent! Check your inbox."
        except Exception as e:
            return False, f"Failed to resend verification: {str(e)}"


def render_auth_page():
    """Render authentication page (Login/Signup)"""
    
    # Add custom CSS for centering and styling
    st.markdown("""
        <style>
        /* Center the main content */
        .main .block-container {
            max-width: 800px;
            padding-top: 3rem;
            padding-bottom: 5rem;
            margin: 0 auto;
        }
        
        /* Style the header */
        h1 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        /* Style the tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
            justify-content: center;
            margin-bottom: 2rem;
        }
        
        /* Style forms */
        .stForm {
            background: rgba(255, 255, 255, 0.05);
            padding: 2rem;
            border-radius: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Copyright footer */
        .copyright-footer {
            position: fixed;
    
            text-align: center;
        
        }
        
        .copyright-footer .line1 {
            color: #888;
            margin-bottom: 0.3rem;
        }
        
        .copyright-footer .line2 {
            color: #666;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("<h1>🎯 AI Resume Shortlisting</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888; margin-bottom: 2rem;'>Sign in to access your recruitment dashboard</p>", unsafe_allow_html=True)
    
    # Tabs for Login and Signup
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    auth_manager = AuthManager()
    
    # LOGIN TAB
    with tab1:
        with st.form("login_form"):
            st.markdown("### Login to Your Account")
            st.markdown("")
            
            email = st.text_input("Email", placeholder="your-email@company.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            st.markdown("")
            col1, col2 = st.columns(2)
            
            with col1:
                submit = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
            
            with col2:
                forgot_password = st.form_submit_button("🔑 Forgot Password?", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    with st.spinner("Logging in..."):
                        success, message, user = auth_manager.login(email, password)
                        
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(message)
                            
                            if "Email not confirmed" in message or "verify your email" in message:
                                if st.button("📧 Resend Verification Email"):
                                    success_resend, msg_resend = auth_manager.resend_verification(email)
                                    if success_resend:
                                        st.success(msg_resend)
                                    else:
                                        st.error(msg_resend)
            
            if forgot_password:
                if not email:
                    st.error("Please enter your email first")
                else:
                    success, message = auth_manager.reset_password(email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    # SIGNUP TAB
    with tab2:
        with st.form("signup_form"):
            st.markdown("### Create Account")
            st.markdown("")
            
            full_name = st.text_input("Full Name", placeholder="John Doe")
            email = st.text_input("Email", placeholder="your-email@company.com")
            password = st.text_input("Password", type="password", placeholder="••••••••", help="Minimum 6 characters")
            password_confirm = st.text_input("Confirm Password", type="password", placeholder="••••••••")
            
            st.markdown("")
            agree = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            st.markdown("")
            submit = st.form_submit_button("✨ Create Account", use_container_width=True, type="primary")
            
            if submit:
                # Validation
                if not full_name or not email or not password or not password_confirm:
                    st.error("Please fill all fields")
                elif not agree:
                    st.error("Please agree to Terms of Service")
                elif password != password_confirm:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    with st.spinner("Creating account..."):
                        success, message = auth_manager.signup(email, password)
                        
                        if success:
                            st.success(f"✅ Welcome {full_name}! {message}")
                            st.info("💡 You can now go to the Login tab and sign in!")
                            
                            if "email" in message.lower() and "verify" in message.lower():
                                st.info("📧 Check your email to verify your account")
                        else:
                            st.error(message)
    
    # Copyright Footer
    from datetime import datetime
    current_year = datetime.now().year
    
    st.markdown(f"""
        <div class="copyright-footer">
            <div class="line1">Powered by AI & Machine Learning</div>
            <div class="line2">© {current_year} Resume Shortlisting System</div>
        </div>
    """, unsafe_allow_html=True)


def render_auth_sidebar():
    """Render authentication info in sidebar"""
    
    auth_manager = AuthManager()
    
    if auth_manager.is_authenticated():
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 Logged In")
            
            user_email = st.session_state.get('user_email', 'Unknown')
            st.info(f"📧 {user_email}")
            
            if st.button("🚪 Logout", use_container_width=True):
                success, message = auth_manager.logout()
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def require_auth(func):
    """Decorator to require authentication for a function"""
    def wrapper(*args, **kwargs):
        auth_manager = AuthManager()
        if not auth_manager.is_authenticated():
            st.warning("⚠️ Please login to access this feature")
            render_auth_page()
            return None
        return func(*args, **kwargs)
    return wrapper


# Test authentication
if __name__ == "__main__":
    st.set_page_config(page_title="Authentication Test", layout="wide")
    render_auth_page()


