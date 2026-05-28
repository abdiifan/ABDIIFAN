"""
auth.py — Supabase authentication & session helpers for CDSS Based Alloc
"""

import streamlit as st
import requests
import json
from datetime import datetime, timezone
from typing import Optional, Tuple

# ── Supabase config ──────────────────────────────────────────────────────────
# Set these in .streamlit/secrets.toml:
#   [supabase]
#   url = "https://xxxx.supabase.co"
#   anon_key = "eyJ..."
#   service_role_key = "eyJ..."   ← only needed for admin operations

def _cfg():
    """Return (url, anon_key, service_role_key) from st.secrets."""
    sb = st.secrets.get("supabase", {})
    url = sb.get("url", "")
    anon = sb.get("anon_key", "")
    svc  = sb.get("service_role_key", "")
    if not url or not anon:
        st.error("⚠️  Supabase credentials missing. Add them to `.streamlit/secrets.toml`.")
        st.stop()
    return url, anon, svc

# ── Low-level REST helpers ────────────────────────────────────────────────────

def _auth_post(path: str, payload: dict) -> dict:
    url, anon, _ = _cfg()
    r = requests.post(
        f"{url}/auth/v1/{path}",
        headers={"apikey": anon, "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    return r.json()

def _rest_get(table: str, params: dict = None, token: str = None, use_service: bool = False) -> list:
    url, anon, svc = _cfg()
    key = svc if use_service else anon
    tok = token or key
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
    }
    r = requests.get(
        f"{url}/rest/v1/{table}",
        headers=headers,
        params=params or {},
        timeout=10,
    )
    return r.json() if r.status_code == 200 else []

def _rest_patch(table: str, match: dict, payload: dict, use_service: bool = True) -> dict:
    url, anon, svc = _cfg()
    key = svc if use_service else anon
    params = {k: f"eq.{v}" for k, v in match.items()}
    r = requests.patch(
        f"{url}/rest/v1/{table}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        params=params,
        json=payload,
        timeout=10,
    )
    return r.json()

def _rest_post(table: str, payload: dict, token: str = None, use_service: bool = False) -> dict:
    url, anon, svc = _cfg()
    key = svc if use_service else anon
    tok = token or key
    r = requests.post(
        f"{url}/rest/v1/{table}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json=payload,
        timeout=10,
    )
    return r.json()

# ── Session helpers ───────────────────────────────────────────────────────────

def init_session():
    """Initialise auth-related session-state keys (call once at app start)."""
    for k, v in [
        ("auth_user", None),
        ("auth_token", None),
        ("auth_role", None),
        ("auth_status", None),     # 'pending' | 'approved' | 'rejected'
        ("auth_error", ""),
        ("auth_signup_ok", ""),    # success message shown on login page after sign-up
        ("auth_tab", "login"),     # 'login' | 'signup'
    ]:
        if k not in st.session_state:
            st.session_state[k] = v


def is_logged_in() -> bool:
    return st.session_state.get("auth_user") is not None


def current_user() -> Optional[dict]:
    return st.session_state.get("auth_user")


def current_role() -> str:
    return st.session_state.get("auth_role", "user")


def is_admin() -> bool:
    return current_role() == "admin"


def logout():
    for k in ["auth_user", "auth_token", "auth_role", "auth_status", "auth_error",
              "auth_signup_ok", "auth_tab", "admin_view_mode"]:
        if k == "auth_error" or k == "auth_signup_ok":
            st.session_state[k] = ""
        elif k == "auth_tab":
            st.session_state[k] = "login"
        else:
            st.session_state[k] = None
    st.rerun()

# ── Sign-up ───────────────────────────────────────────────────────────────────

def sign_up(email: str, password: str, full_name: str = "") -> Tuple[bool, str]:
    """
    Create a Supabase Auth user then insert a profile row with
    role='user' and status='pending'.
    Returns (success, message).
    """
    res = _auth_post("signup", {"email": email, "password": password})

    if "error" in res or res.get("code") == 422:
        msg = res.get("msg") or res.get("message") or res.get("error_description", "Sign-up failed")
        return False, msg

    user_id = res.get("user", {}).get("id") or res.get("id")
    if not user_id:
        return False, "Unexpected response from Supabase — no user ID returned."

    # Insert profile (service role bypasses RLS for initial insert)
    profile = {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "role": "user",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _rest_post("profiles", profile, use_service=True)
    return True, "Account created! Please wait for admin approval before logging in."


# ── Login ─────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> Tuple[bool, str]:
    """
    Authenticate with Supabase, then check profile status/role.
    Populates session state on success.
    Returns (success, message).
    """
    res = _auth_post("token?grant_type=password", {"email": email, "password": password})

    if "error" in res or "access_token" not in res:
        msg = res.get("error_description") or res.get("msg") or "Invalid email or password."
        return False, msg

    token = res["access_token"]
    user_id = res.get("user", {}).get("id") or res.get("user_id")

    # Fetch profile
    profiles = _rest_get(
        "profiles",
        params={"id": f"eq.{user_id}", "select": "id,email,full_name,role,status"},
        token=token,
        use_service=True,
    )

    if not profiles or not isinstance(profiles, list):
        return False, "Profile not found. Contact your administrator."

    profile = profiles[0]
    status = profile.get("status", "pending")

    if status == "pending":
        return False, "⏳ Your account is pending admin approval."
    if status == "rejected":
        return False, "❌ Your account has been rejected. Contact your administrator."

    # All good — store in session
    st.session_state.auth_user    = profile
    st.session_state.auth_token   = token
    st.session_state.auth_role    = profile.get("role", "user")
    st.session_state.auth_status  = status
    st.session_state.auth_error   = ""

    _log_activity(user_id, token, "login", f"User {email} logged in")
    return True, "Welcome back!"

# ── Admin: user management ────────────────────────────────────────────────────

def admin_list_users() -> list:
    """Return all profiles (admin only)."""
    return _rest_get(
        "profiles",
        params={"select": "id,email,full_name,role,status,created_at", "order": "created_at.desc"},
        use_service=True,
    )


def admin_update_status(user_id: str, new_status: str) -> bool:
    """Approve or reject a user (pending → approved/rejected)."""
    result = _rest_patch("profiles", {"id": user_id}, {"status": new_status}, use_service=True)
    _log_activity(
        st.session_state.auth_user["id"],
        st.session_state.auth_token,
        "status_change",
        f"Set user {user_id} status → {new_status}",
    )
    return isinstance(result, list) and len(result) > 0


def admin_update_role(user_id: str, new_role: str) -> bool:
    """Promote/demote a user (user ↔ admin)."""
    result = _rest_patch("profiles", {"id": user_id}, {"role": new_role}, use_service=True)
    _log_activity(
        st.session_state.auth_user["id"],
        st.session_state.auth_token,
        "role_change",
        f"Set user {user_id} role → {new_role}",
    )
    return isinstance(result, list) and len(result) > 0


# ── Activity log ─────────────────────────────────────────────────────────────

def _log_activity(actor_id: str, token: str, action: str, detail: str):
    try:
        _rest_post(
            "activity_logs",
            {
                "actor_id": actor_id,
                "action": action,
                "detail": detail,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            use_service=True,
        )
    except Exception:
        pass  # Non-critical — swallow errors


def admin_get_logs(limit: int = 100) -> list:
    return _rest_get(
        "activity_logs",
        params={
            "select": "id,actor_id,action,detail,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        },
        use_service=True,
    )