"""
auth_ui.py — Login & Sign-up page rendered inside Streamlit
"""

import streamlit as st
from auth import sign_up, login

# ── CSS for the auth screens ──────────────────────────────────────────────────
AUTH_CSS = """
<style>
.auth-shell {
    max-width: 420px;
    margin: 3rem auto 0;
    padding: 0 1rem;
}
.auth-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 2.2rem 2.4rem 2rem;
    box-shadow: 0 4px 24px rgba(15,23,42,0.08);
}
.auth-logo {
    display: flex; align-items: center; gap: 0.7rem;
    margin-bottom: 1.8rem;
}
.auth-logo-icon {
    width: 44px; height: 44px;
    background: linear-gradient(135deg,#3b82f6,#6366f1);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem;
}
.auth-logo-title { font-size: 1.1rem; font-weight: 800; color: #0f172a; }
.auth-logo-sub   { font-size: 0.72rem; color: #64748b; }
.auth-heading    { font-size: 1.4rem; font-weight: 800; color: #0f172a; margin-bottom: 0.3rem; }
.auth-sub        { font-size: 0.83rem; color: #64748b; margin-bottom: 1.6rem; }
.auth-divider    { border: none; border-top: 1px solid #e2e8f0; margin: 1.2rem 0; }
.auth-switch     { text-align: center; font-size: 0.82rem; color: #64748b; margin-top: 1.2rem; }
.auth-err {
    background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px;
    padding: 0.75rem 1rem; font-size: 0.82rem; color: #dc2626;
    margin-bottom: 1rem;
}
.auth-ok {
    background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px;
    padding: 0.75rem 1rem; font-size: 0.82rem; color: #16a34a;
    margin-bottom: 1rem;
}
.pending-card {
    max-width: 420px;
    margin: 5rem auto;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 18px;
    padding: 2.4rem;
    text-align: center;
    box-shadow: 0 4px 24px rgba(15,23,42,0.07);
}
.pending-icon { font-size: 3rem; margin-bottom: 1rem; }
.pending-title { font-size: 1.3rem; font-weight: 800; color: #92400e; margin-bottom: 0.5rem; }
.pending-body  { font-size: 0.85rem; color: #78350f; line-height: 1.6; }
</style>
"""


def render_login_page():
    """
    Renders either the Login or Sign-Up form.
    Returns only after successful login (mutates st.session_state directly via auth.login).
    """
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # Tab toggle stored in session
    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = "login"

    tab = st.session_state.auth_tab

    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-card">
      <div class="auth-logo">
        <div class="auth-logo-icon">💊</div>
        <div>
          <div class="auth-logo-title">CDSS Based Alloc</div>
          <div class="auth-logo-sub">Pharmaceutical Inventory Allocation</div>
        </div>
      </div>
    """, unsafe_allow_html=True)

    # ── Show persistent success message from sign-up ──
    if st.session_state.get("auth_signup_ok"):
        st.markdown(f'<div class="auth-ok">✅ {st.session_state.auth_signup_ok}</div>', unsafe_allow_html=True)

    # ── Show error if any ──
    if st.session_state.get("auth_error"):
        st.markdown(f'<div class="auth-err">{st.session_state.auth_error}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)   # close auth-card (re-opened below per tab)

    # ─── LOGIN FORM ──────────────────────────────────────────────
    if tab == "login":
        with st.form("login_form", clear_on_submit=False):
            st.markdown("""
            <div style="font-size:1.35rem;font-weight:800;color:#0f172a;margin-bottom:0.25rem">Sign In</div>
            <div style="font-size:0.82rem;color:#64748b;margin-bottom:1.4rem">Access your allocation dashboard</div>
            """, unsafe_allow_html=True)

            email    = st.text_input("Email address", placeholder="you@organisation.org")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign In →", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.session_state.auth_error = "Please enter your email and password."
                st.rerun()
            else:
                st.session_state.auth_error = ""
                st.session_state.auth_signup_ok = ""
                ok, msg = login(email.strip().lower(), password)
                if ok:
                    st.rerun()
                else:
                    st.session_state.auth_error = msg
                    st.rerun()

        st.markdown("""
        <div class="auth-switch">
          Don't have an account?
        </div>
        """, unsafe_allow_html=True)
        if st.button("Create an account", use_container_width=True):
            st.session_state.auth_tab = "signup"
            st.session_state.auth_error = ""
            st.session_state.auth_signup_ok = ""
            st.rerun()

    # ─── SIGN-UP FORM ────────────────────────────────────────────
    else:
        with st.form("signup_form", clear_on_submit=True):
            st.markdown("""
            <div style="font-size:1.35rem;font-weight:800;color:#0f172a;margin-bottom:0.25rem">Create Account</div>
            <div style="font-size:0.82rem;color:#64748b;margin-bottom:1.4rem">Request access — an admin will review your registration</div>
            """, unsafe_allow_html=True)

            full_name = st.text_input("Full name", placeholder="Abebe Girma")
            email     = st.text_input("Email address", placeholder="you@organisation.org")
            password  = st.text_input("Password", type="password", placeholder="Min. 8 characters")
            password2 = st.text_input("Confirm password", type="password", placeholder="Repeat password")
            submitted = st.form_submit_button("Request Access →", use_container_width=True, type="primary")

        if submitted:
            if not email or not password or not full_name:
                st.session_state.auth_error = "All fields are required."
                st.rerun()
            elif len(password) < 8:
                st.session_state.auth_error = "Password must be at least 8 characters."
                st.rerun()
            elif password != password2:
                st.session_state.auth_error = "Passwords do not match."
                st.rerun()
            else:
                st.session_state.auth_error = ""
                ok, msg = sign_up(email.strip().lower(), password, full_name.strip())
                if ok:
                    st.session_state.auth_signup_ok = msg
                    st.session_state.auth_tab = "login"
                else:
                    st.session_state.auth_error = msg
                st.rerun()

        st.markdown('<div class="auth-switch">Already have an account?</div>', unsafe_allow_html=True)
        if st.button("Back to Sign In", use_container_width=True):
            st.session_state.auth_tab = "login"
            st.session_state.auth_error = ""
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # close auth-shell


def render_pending_screen():
    """Shown when a logged-in user's account is still pending (shouldn't normally reach here)."""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    user = st.session_state.auth_user or {}
    st.markdown(f"""
    <div class="pending-card">
      <div class="pending-icon">⏳</div>
      <div class="pending-title">Awaiting Approval</div>
      <div class="pending-body">
        Hi <b>{user.get('full_name') or user.get('email', '')}</b>,<br><br>
        Your registration is under review. An administrator will approve or reject
        your account shortly. You'll be able to log in once approved.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button("🚪 Sign Out", use_container_width=True):
            from auth import logout
            logout()