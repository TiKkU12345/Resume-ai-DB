"""
Admin Approval Authentication System
- Users can signup but cannot login until admin approves
- New device login requires admin confirmation via email
- Full control for admin
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import hashlib
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class AdminApprovalAuth:
    """Authentication with admin approval and device verification"""
    
    def _init_(self):
        # Supabase connection
        self.url = st.secrets.get("SUPABASE_URL", "")
        self.key = st.secrets.get("SUPABASE_KEY", "")
        
        if self.url and self.key:
            self.client: Client = create_client(self.url, self.key)
        else:
            self.client = None
        
        # Admin email (YOU)
        self.admin_email = st.secrets.get("ADMIN_EMAIL", "your-admin@email.com")
        
        # Session state initialization
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'device_id' not in st.session_state:
            st.session_state.device_id = self._generate_device_id()
    
    def _generate_device_id(self) -> str:
        """Generate unique device identifier"""
        import platform
        import socket
        
        device_info = f"{platform.system()}-{platform.node()}-{socket.gethostname()}"
        return hashlib.md5(device_info.encode()).hexdigest()
    
    def sign_up(self, email: str, password: str, full_name: str) -> tuple:
        """
        User signup - Account created but NOT approved
        Admin will receive email to approve
        """
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
                'is_approved': False,  # ← Admin approval required
                'approved_at': None,
                'approved_by': None,
                'approved_devices': [],  # List of approved device IDs
                'signup_date': datetime.now().isoformat(),
                'last_login': None
            }
            
            # Check if user already exists
            existing = self.client.table('users').select('email').eq('email', email.lower()).execute()
            if existing.data:
                return False, "Email already registered. Waiting for admin approval."
            
            # Insert new user
            response = self.client.table('users').insert(user_data).execute()
            
            if response.data:
                # Send email to admin for approval
                self._send_approval_request_to_admin(email, full_name)
                
                return True, f"✅ Account created for {full_name}!\n\n⏳ Your account is pending admin approval. You'll receive an email once approved."
            else:
                return False, "Failed to create account"
        
        except Exception as e:
            return False, f"Signup failed: {str(e)}"
    
    def sign_in(self, email: str, password: str) -> tuple:
        """
        User login with admin approval and device verification
        """
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
                return False, "⏳ Your account is pending admin approval.\n\nPlease wait for admin to approve your access."
            
            # CHECK 2: Is this device approved?
            current_device = st.session_state.device_id
            approved_devices = user.get('approved_devices', [])
            
            if current_device not in approved_devices:
                # New device detected - Request admin approval
                self._send_new_device_alert_to_admin(email, user['full_name'], current_device)
                
                return False, f"🔐 New device detected!\n\nAdmin approval required for this device.\n\nAn email has been sent to the admin. Please wait for approval."
            
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
    
    def _send_approval_request_to_admin(self, user_email: str, user_name: str):
        """Send email to admin when new user signs up"""
        try:
            # Create approval link (you'll manually approve in Supabase)
            message = f"""
🔔 NEW USER SIGNUP REQUEST

Name: {user_name}
Email: {user_email}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ACTION REQUIRED:
1. Go to Supabase Dashboard
2. Open 'users' table
3. Find user: {user_email}
4. Set 'is_approved' = TRUE
5. Add first device to 'approved_devices': []

Or use SQL:
UPDATE users 
SET is_approved = true, 
    approved_at = NOW(), 
    approved_by = '{self.admin_email}',
    approved_devices = ARRAY['{st.session_state.device_id}']::text[]
WHERE email = '{user_email}';

---
AI Resume Shortlisting System
"""
            
            # Log to activity_logs table
            if self.client:
                self.client.table('activity_logs').insert({
                    'action_type': 'signup_request',
                    'details': {
                        'user_email': user_email,
                        'user_name': user_name,
                        'admin_notified': True
                    },
                    'created_at': datetime.now().isoformat()
                }).execute()
            
            # Print for now (you can setup email later)
            print(message)
            
            # TODO: Send actual email using SMTP
            # self._send_email_to_admin(subject, message)
            
        except Exception as e:
            print(f"Failed to send approval request: {e}")
    
    def _send_new_device_alert_to_admin(self, user_email: str, user_name: str, device_id: str):
        """Send alert when user tries to login from new device"""
        try:
            message = f"""
🔐 NEW DEVICE LOGIN ATTEMPT

User: {user_name} ({user_email})
Device ID: {device_id}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ACTION REQUIRED:
Approve this device by running SQL:

UPDATE users 
SET approved_devices = array_append(approved_devices, '{device_id}')
WHERE email = '{user_email}';

---
AI Resume Shortlisting System
"""
            
            # Log to database
            if self.client:
                self.client.table('activity_logs').insert({
                    'action_type': 'new_device_alert',
                    'details': {
                        'user_email': user_email,
                        'user_name': user_name,
                        'device_id': device_id,
                        'admin_notified': True
                    },
                    'created_at': datetime.now().isoformat()
                }).execute()
            
            print(message)
            
            # TODO: Send actual email
            
        except Exception as e:
            print(f"Failed to send device alert: {e}")
    
    def sign_out(self):
        """Logout user"""
        st.session_state.user = None
        st.session_state.parsed_resumes = []
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
    """Render authentication page"""
    
    auth = AdminApprovalAuth()
    
    if auth.is_authenticated():
        st.success(f"✅ Logged in as: {auth.get_current_user()['full_name']}")
        if st.button("Logout"):
            auth.sign_out()
            st.rerun()
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1>🎯 AI Resume Shortlisting</h1>
            <p style='color: #666;'>Admin-Approved Access Only</p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Request Access"])
        
        # Login Tab
        with tab1:
            with st.form("login_form"):
                st.markdown("### Login")
                st.caption("⚠ Only approved users can login")
                
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                
                submit = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
                
                if submit:
                    if email and password:
                        with st.spinner("Verifying..."):
                            success, message = auth.sign_in(email, password)
                        
                        if success:
                            st.success(message)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill in all fields")
        
        # Signup Tab
        with tab2:
            with st.form("signup_form"):
                st.markdown("### Request Access")
                st.info("🔒 Your account will be reviewed by admin before granting access")
                
                full_name = st.text_input("Full Name *", key="signup_name")
                email = st.text_input("Email *", key="signup_email")
                password = st.text_input("Password *", type="password", key="signup_password")
                confirm_password = st.text_input("Confirm Password *", type="password", key="signup_confirm")
                
                agree = st.checkbox("I understand that my access is subject to admin approval")
                
                submit = st.form_submit_button("✨ Request Access", use_container_width=True, type="primary")
                
                if submit:
                    if not agree:
                        st.error("Please acknowledge the approval requirement")
                    elif not all([full_name, email, password, confirm_password]):
                        st.error("Please fill in all fields")
                    elif password != confirm_password:
                        st.error("Passwords don't match")
                    else:
                        with st.spinner("Sending request..."):
                            success, message = auth.sign_up(email, password, full_name)
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
        
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 12px;'>
            <p>🔐 Secure Access | Admin Approval Required</p>
            <p>© 2024 AI Resume Shortlisting System</p>
        </div>
        """, unsafe_allow_html=True)


# SQL to create users table with approval system
USERS_TABLE_SQL = """
-- Drop existing table if needed
-- DROP TABLE IF EXISTS users;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    
    -- Admin approval fields
    is_approved BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMP,
    approved_by VARCHAR(255),
    
    -- Device management
    approved_devices TEXT[] DEFAULT '{}',
    
    -- Metadata
    signup_date TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_approved ON users(is_approved);

-- Sample: Approve a user
-- UPDATE users 
-- SET is_approved = true, 
--     approved_at = NOW(), 
--     approved_by = 'admin@email.com',
--     approved_devices = ARRAY['device_id_here']::text[]
-- WHERE email = 'user@email.com';

-- Sample: Add new device
-- UPDATE users 
-- SET approved_devices = array_append(approved_devices, 'new_device_id')
-- WHERE email = 'user@email.com';
"""
