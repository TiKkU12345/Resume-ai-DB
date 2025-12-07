import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import hashlib
import re
from app_config import get_secret


class AdminApprovalAuth:
    """Simple Authentication with Supabase + Admin approval"""

    def __init__(self):
        self.url = get_secret("SUPABASE_URL", "")
        self.key = get_secret("SUPABASE_KEY", "")

        if self.url and self.key:
            self.client: Client = create_client(self.url, self.key)
        else:
            st.error("⚠️ Supabase not configured")
            self.client = None

        # admin email
        self.admin_email = get_secret("ADMIN_EMAIL", "admin@example.com")

        # only these emails can register
        self.allowed_emails = [
            
            "arunav11a31.hts21@gmail.com",
            "arunav.jsr.0604@gmail.com",
            "6801788@rungta.org"
        ]

        if 'user' not in st.session_state:
            st.session_state.user = None

    # -------------------------- UTILITIES --------------------------

    def _validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _validate_password(self, password: str) -> bool:
        return (len(password) >= 8 and 
                any(c.isalpha() for c in password) and 
                any(c.isdigit() for c in password))

    # --------------------------- SIGN UP ---------------------------

    def sign_up(self, email: str, password: str, full_name: str):

        if not self.client:
            return False, "Authentication not configured"

        # whitelist check
        if email.lower() not in [e.lower() for e in self.allowed_emails]:
            return False, "⛔ Only authorized emails can register."

        if not self._validate_email(email):
            return False, "Invalid email format"

        if not self._validate_password(password):
            return False, "Password must be 8+ characters with letters & numbers"

        # hash password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # check existing user
        existing = self.client.table("users").select("email").eq("email", email).execute()
        if existing.data:
            return False, "Email already registered"

        # insert user
        self.client.table("users").insert({
            "email": email.lower(),
            "password_hash": hashed_password,
            "full_name": full_name.strip(),
            "is_approved": False,
            "signup_date": datetime.now().isoformat(),
        }).execute()

        # ------------------------ SIMPLE ADMIN EMAIL ------------------------

        self._send_admin_email(full_name, email)

        return True, "Account created. Waiting for admin approval!"

    def _send_admin_email(self, full_name, email):
        """Simple clean email (NO HTML, NO BLOCKS)"""

        try:
            import smtplib
            from email.mime.text import MIMEText

            sender = get_secret("SENDER_EMAIL")
            sender_pass = get_secret("SENDER_PASSWORD")
            smtp_server = get_secret("SMTP_SERVER")
            smtp_port = get_secret("SMTP_PORT", 587)

            body = f"""
New User Signup

Name: {full_name}
Email: {email}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Action Required:
Approve this user by running:

UPDATE users
SET is_approved = true
WHERE email = '{email}';
"""

            msg = MIMEText(body)
            msg["Subject"] = f"New Signup Request: {full_name}"
            msg["From"] = sender
            msg["To"] = self.admin_email

            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                server.starttls()
                server.login(sender, sender_pass)
                server.send_message(msg)

        except Exception as e:
            print("Admin email failed:", e)

    # --------------------------- SIGN IN ---------------------------

    def sign_in(self, email: str, password: str):

        if not self.client:
            return False, "Authentication not configured"

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        response = (
            self.client.table("users")
            .select("*")
            .eq("email", email.lower())
            .eq("password_hash", hashed_password)
            .execute()
        )

        if not response.data:
            return False, "Invalid email or password"

        user = response.data[0]

        if not user["is_approved"]:
            return False, "⏳ Account pending admin approval"

        st.session_state.user = user
        return True, f"Welcome, {user['full_name']}!"

    # --------------------------- LOGOUT ---------------------------

    def sign_out(self):
        st.session_state.user = None

    # --------------------------- STATE -----------------------------

    def is_authenticated(self):
        return st.session_state.user is not None

    def get_current_user(self):
        return st.session_state.user


# --------------------------- UI PAGES ----------------------------

def render_auth_page():

    auth = AdminApprovalAuth()

    if auth.is_authenticated():
        user = auth.get_current_user()
        st.success(f"Logged in as {user['full_name']}")

        if st.button("Logout", type="primary"):
            auth.sign_out()
            st.rerun()

        return

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    # --------------------------- LOGIN ---------------------------
    with tab1:
        st.subheader("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            ok, msg = auth.sign_in(email, password)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # --------------------------- SIGNUP ---------------------------
    with tab2:
        st.subheader("Create Account")

        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")

        if st.button("Sign Up", use_container_width=True):

            if password != confirm:
                st.error("Passwords do not match")
            else:
                ok, msg = auth.sign_up(email, password, full_name)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


def render_auth_sidebar():
    auth = AdminApprovalAuth()
    if auth.is_authenticated():
        st.sidebar.markdown("---")
        user = auth.get_current_user()
        st.sidebar.write(f"👤 {user['full_name']}")

        if st.sidebar.button("Logout"):
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
