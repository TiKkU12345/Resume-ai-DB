import streamlit as st
from supabase import create_client
from datetime import datetime
from app_config import get_secret
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class AdminApprovalAuth:
    """FINAL VERSION — Supabase Auth + Admin Approval + Email Whitelist"""

    def __init__(self):
        # Supabase connection
        self.url = get_secret("SUPABASE_URL")
        self.key = get_secret("SUPABASE_KEY")
        self.client = create_client(self.url, self.key)

        # EMAIL CONFIG
        self.admin_email = get_secret("ADMIN_EMAIL")
        self.smtp_user = get_secret("SENDER_EMAIL")
        self.smtp_pass = get_secret("SENDER_PASSWORD")
        self.smtp_host = get_secret("SMTP_SERVER")
        self.smtp_port = int(get_secret("SMTP_PORT", 587))

        # Session
        if "user_email" not in st.session_state:
            st.session_state.user_email = None
            st.session_state.authenticated = False

    # ---------------- AUTH CHECK ----------------
    def is_authenticated(self):
        return st.session_state.get("authenticated", False)

    def sign_out(self):
        st.session_state.user_email = None
        st.session_state.authenticated = False

    # ---------------- SIGNUP ----------------
    def sign_up(self, full_name, email, password):
        """
        ✔ Check authorized_emails table
        ✔ Use Supabase Auth (sends confirm email automatically)
        """

        # 1) Check whitelist
        allowed = self.client.table("authorized_emails").select("*").eq("email", email.lower()).execute()
        if len(allowed.data) == 0:
            return False, "⛔ Not authorized. Only approved emails can signup."

        # 2) Call Supabase Auth signup (THIS sends confirmation email!)
        try:
            res = self.client.auth.sign_up({"email": email, "password": password})
        except Exception as e:
            return False, f"Signup failed: {e}"

        if "error" in res and res["error"]:
            return False, res["error"]["message"]

        return True, "✔ Signup created — check your email to confirm."

    # ---------------- LOGIN ----------------
    def sign_in(self, email, password):
        """
        ✔ Login via Supabase Auth
        ✔ If users row doesn't exist -> create row + notify admin
        ✔ Block login until approved
        """

        # 1) Supabase Auth login
        try:
            res = self.client.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as e:
            return False, f"Login failed: {e}"

        if "error" in res and res["error"]:
            return False, res["error"]["message"]

        # 2) Check user row
        db_user = self.client.table("users").select("*").eq("email", email).single().execute()

        if not db_user.data:
            # First login after email confirmation → create row
            self._create_user_and_notify_admin(email)
            return False, "🔔 Email confirmed — waiting for admin approval."

        user = db_user.data

        # 3) Reject if not approved
        if not user["approved"]:
            return False, "⏳ Account pending admin approval."

        # 4) Login success
        st.session_state.user_email = email
        st.session_state.authenticated = True
        return True, "Welcome back!"

    # ---------------- CREATE USER + NOTIFY ADMIN ----------------
    def _create_user_and_notify_admin(self, email):
        """Insert new user & send admin approval SQL"""

        payload = {
            "email": email,
            "name": "",
            "approved": False,
            "approved_at": None,
            "created_at": datetime.utcnow().isoformat(),
        }

        self.client.table("users").insert(payload).execute()

        sql = f"""
UPDATE users 
SET approved = true,
    approved_at = NOW()
WHERE email = '{email}';
"""

        body = f"""
<h2>New User Email Confirmed</h2>

<p><b>Email:</b> {email}</p>
<p><b>Time:</b> {datetime.utcnow().isoformat()}</p>

<h3>Approve User:</h3>

<pre>{sql}</pre>
"""

        self._send_email(self.admin_email, "New User Confirmed - Approval Needed", body)

    # ---------------- EMAIL SENDER ----------------
    def _send_email(self, to, subject, body):
        msg = MIMEMultipart("alternative")
        msg["From"] = self.smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        s = smtplib.SMTP(self.smtp_host, self.smtp_port)
        s.starttls()
        s.login(self.smtp_user, self.smtp_pass)
        s.sendmail(self.smtp_user, to, msg.as_string())
        s.quit()


# ---------------- AUTH PAGE UI ----------------
def render_auth_page():
    auth = AdminApprovalAuth()

    if auth.is_authenticated():
        st.success(f"Logged in as: {st.session_state.user_email}")
        if st.button("Logout"):
            auth.sign_out()
            st.rerun()
        return

    tab1, tab2 = st.tabs(["Login", "Signup"])

    # ---- LOGIN ----
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            ok, msg = auth.sign_in(email, password)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # ---- SIGNUP ----
    with tab2:
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")

        if st.button("Signup"):
            if password != confirm:
                st.error("Passwords don't match")
            else:
                ok, msg = auth.sign_up(name, email, password)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


def render_auth_sidebar():
    if st.session_state.get("authenticated", False):
        with st.sidebar:
            st.write(f"Logged in as: {st.session_state.user_email}")
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.rerun()
