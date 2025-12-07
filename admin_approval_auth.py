import streamlit as st
from database import SupabaseManager
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class AdminApprovalAuth:
    """Authentication manager using Supabase Auth + admin approval"""

    def __init__(self):
        self.db = SupabaseManager()

        self.admin_email = st.secrets["email"]["admin"]
        self.smtp_user = st.secrets["email"]["user"]
        self.smtp_pass = st.secrets["email"]["pass"]
        self.smtp_host = st.secrets["email"]["host"]

    # --------------- AUTH CHECK -----------------
    def is_authenticated(self):
        return st.session_state.get("authenticated", False)

    def is_admin(self):
        return st.session_state.get("is_admin", False)

    # --------------- SIGNUP LOGIC -----------------
    def signup(self, full_name, email, password):
        """
        1) Check authorized_emails table
        2) If allowed -> Supabase Auth sign_up (sends confirmation email)
        3) DO NOT create user record yet
        """

        # Step 1 — Check authorized email
        allowed = self.db.client.table("authorized_emails").select("*").eq("email", email).execute()
        if len(allowed.data) == 0:
            return False, "❌ This email is not authorized"

        # Step 2 — Supabase AUTH signup (official email will be sent)
        try:
            res = self.db.client.auth.sign_up({"email": email, "password": password})
        except Exception as e:
            return False, f"Signup failed: {e}"

        # If signup error
        if isinstance(res, dict) and res.get("error"):
            return False, res["error"]["message"]

        return True, "Signup successful! Please check your email to confirm."

    # --------------- LOGIN LOGIC -----------------
    def login(self, email, password):
        """
        On login:
        - Supabase Auth login
        - If user_row not exists -> create user_row and notify admin
        - If exists but not approved -> block login
        - Else -> login success
        """

        # Step 1 — Supabase Auth login
        try:
            res = self.db.client.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as e:
            return False, f"Login failed: {e}"

        if isinstance(res, dict) and res.get("error"):
            return False, res["error"]["message"]

        # Step 2 — Check users table
        user_row = self.db.client.table("users").select("*").eq("email", email).single().execute()

        # If row missing → create new + notify admin
        if not user_row.data:
            self._create_user_and_notify_admin(email)
            return False, "Your email is confirmed. Admin has been notified for approval."

        user = user_row.data

        # Step 3 — Not approved
        if not user["approved"]:
            return False, "Your account is pending admin approval."

        # Approval done → allow login
        st.session_state.authenticated = True
        st.session_state.user_email = email
        st.session_state.user_name = user.get("name", "")
        st.session_state.is_admin = user.get("is_admin", False)

        return True, "Login successful!"

    # --------------- CREATE USER + NOTIFY ADMIN --------------
    def _create_user_and_notify_admin(self, email):
        """Create user row in database and notify admin"""
        payload = {
            "email": email,
            "name": "",
            "approved": False,
            "approved_at": None,
            "created_at": datetime.utcnow().isoformat()
        }

        # Insert user
        self.db.client.table("users").insert(payload).execute()

        # Send mail to admin
        sql = f"""
UPDATE users
SET approved = true,
    approved_at = NOW()
WHERE email = '{email}';
"""

        body = f"""
New user email confirmed:
Email: {email}

Run the following SQL to approve:

{sql}
"""

        self._send_email(self.admin_email, "New User Confirmed - Approval Required", body)

    # ---------------- EMAIL SENDER ------------------
    def _send_email(self, to, subject, body):
        msg = MIMEMultipart()
        msg["From"] = self.smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        s = smtplib.SMTP(self.smtp_host, 587)
        s.starttls()
        s.login(self.smtp_user, self.smtp_pass)
        s.sendmail(self.smtp_user, to, msg.as_string())
        s.quit()


# ------------ RENDER AUTH PAGE ------------
def render_auth_page():
    st.title("🔐 Login / Signup")

    auth = AdminApprovalAuth()

    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            ok, msg = auth.login(email, password)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with tab2:
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")

        if st.button("Signup"):
            if password != confirm:
                st.error("Passwords do not match")
            else:
                ok, msg = auth.signup(name, email, password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


def render_auth_sidebar():
    if st.session_state.get("authenticated", False):
        with st.sidebar:
            st.markdown("---")
            st.write("Logged in as:", st.session_state.get("user_email", ""))
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.rerun()
