"""
admin_panel.py — Admin-only dashboard for CDSS Based Alloc
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from auth import (
    admin_list_users,
    admin_update_status,
    admin_update_role,
    admin_get_logs,
    logout,
)

ADMIN_CSS = """
<style>
.admin-header {
    display:flex; align-items:center; justify-content:space-between;
    margin-bottom:1.4rem;
}
.admin-title { font-size:1.4rem; font-weight:800; color:#0f172a; }
.admin-sub   { font-size:0.78rem; color:#64748b; }
.stat-row    { display:flex; gap:1rem; margin-bottom:1.4rem; flex-wrap:wrap; }
.stat-card {
    flex:1; min-width:140px;
    background:#fff; border:1px solid #e2e8f0; border-radius:14px;
    padding:1rem 1.2rem;
    box-shadow:0 1px 3px rgba(15,23,42,0.05);
    position:relative; overflow:hidden;
}
.stat-card::before {
    content:''; position:absolute; top:0;left:0;right:0; height:3px;
}
.stat-card.blue::before  { background:linear-gradient(90deg,#3b82f6,#6366f1); }
.stat-card.amber::before { background:linear-gradient(90deg,#f59e0b,#eab308); }
.stat-card.green::before { background:linear-gradient(90deg,#22c55e,#10b981); }
.stat-card.red::before   { background:linear-gradient(90deg,#ef4444,#f97316); }
.stat-num   { font-size:2rem; font-weight:800; color:#0f172a; line-height:1; }
.stat-label { font-size:0.68rem; font-weight:600; text-transform:uppercase; letter-spacing:.06em; color:#94a3b8; margin-top:0.3rem; }
.user-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:0.75rem 1rem;
    border-bottom:1px solid #f1f5f9;
    gap:0.5rem;
}
.user-email  { font-size:0.85rem; font-weight:600; color:#0f172a; }
.user-name   { font-size:0.75rem; color:#64748b; }
.badge-role-admin { background:#ede9fe; color:#7c3aed; font-size:0.7rem; font-weight:600; padding:2px 8px; border-radius:6px; }
.badge-role-user  { background:#f1f5f9; color:#475569; font-size:0.7rem; font-weight:600; padding:2px 8px; border-radius:6px; }
.badge-status-pending  { background:#fef3c7; color:#b45309; font-size:0.7rem; font-weight:600; padding:2px 8px; border-radius:6px; }
.badge-status-approved { background:#dcfce7; color:#15803d; font-size:0.7rem; font-weight:600; padding:2px 8px; border-radius:6px; }
.badge-status-rejected { background:#fee2e2; color:#dc2626; font-size:0.7rem; font-weight:600; padding:2px 8px; border-radius:6px; }
</style>
"""


def _status_badge(status: str) -> str:
    cls = {
        "pending":  "badge-status-pending",
        "approved": "badge-status-approved",
        "rejected": "badge-status-rejected",
    }.get(status, "badge-status-pending")
    icons = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
    return f'<span class="{cls}">{icons.get(status,"")} {status.capitalize()}</span>'


def _role_badge(role: str) -> str:
    cls = "badge-role-admin" if role == "admin" else "badge-role-user"
    icon = "👑" if role == "admin" else "👤"
    return f'<span class="{cls}">{icon} {role.capitalize()}</span>'


def render_admin_panel():
    st.markdown(ADMIN_CSS, unsafe_allow_html=True)

    me = st.session_state.auth_user or {}

    # ── Header ───────────────────────────────────────────────────
    col_h1, col_h2 = st.columns([6, 1])
    with col_h1:
        st.markdown(f"""
        <div>
          <div class="admin-title">👑 Admin Panel</div>
          <div class="admin-sub">Signed in as <b>{me.get('email','')}</b> · Role: admin</div>
        </div>
        """, unsafe_allow_html=True)
    with col_h2:
        if st.button("🚪 Sign Out", use_container_width=True):
            logout()

    st.divider()

    # ── Fetch users ──────────────────────────────────────────────
    with st.spinner("Loading users…"):
        users = admin_list_users()

    if not isinstance(users, list):
        st.error("Failed to load users. Check your Supabase service role key.")
        return

    total     = len(users)
    pending   = sum(1 for u in users if u.get("status") == "pending")
    approved  = sum(1 for u in users if u.get("status") == "approved")
    admins    = sum(1 for u in users if u.get("role") == "admin")

    # ── Analytics row ────────────────────────────────────────────
    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-card blue">
        <div class="stat-num">{total}</div>
        <div class="stat-label">Total Users</div>
      </div>
      <div class="stat-card amber">
        <div class="stat-num">{pending}</div>
        <div class="stat-label">Pending Approval</div>
      </div>
      <div class="stat-card green">
        <div class="stat-num">{approved}</div>
        <div class="stat-label">Active Users</div>
      </div>
      <div class="stat-card red">
        <div class="stat-num">{admins}</div>
        <div class="stat-label">Administrators</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────
    tab_users, tab_pending, tab_logs = st.tabs([
        f"👥  All Users ({total})",
        f"⏳  Pending Approval ({pending})",
        "📋  Activity Logs",
    ])

    # ═══════════════ ALL USERS TAB ═══════════════════════════════
    with tab_users:
        if not users:
            st.info("No users found.")
        else:
            # Search
            search = st.text_input("🔍 Search by email or name", placeholder="Filter users…", key="user_search")
            filtered = [
                u for u in users
                if not search or search.lower() in (u.get("email","") + u.get("full_name","")).lower()
            ]

            if not filtered:
                st.info("No users match your search.")
            else:
                for u in filtered:
                    uid    = u.get("id", "")
                    email  = u.get("email", "—")
                    name   = u.get("full_name", "")
                    role   = u.get("role", "user")
                    status = u.get("status", "pending")
                    joined = u.get("created_at", "")[:10] if u.get("created_at") else "—"

                    # Skip self in action buttons to prevent accidental self-demotion
                    is_me = uid == me.get("id")

                    with st.container():
                        c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                        with c1:
                            st.markdown(f"""
                            <div class="user-email">{email}</div>
                            <div class="user-name">{name or '—'} · Joined {joined}</div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.markdown(_status_badge(status), unsafe_allow_html=True)
                        with c3:
                            st.markdown(_role_badge(role), unsafe_allow_html=True)
                        with c4:
                            if not is_me:
                                if status == "pending":
                                    if st.button("✅ Approve", key=f"appr_{uid}", use_container_width=True):
                                        if admin_update_status(uid, "approved"):
                                            st.success(f"Approved {email}")
                                            st.rerun()
                                elif status == "approved":
                                    if st.button("🚫 Reject", key=f"rej_{uid}", use_container_width=True):
                                        if admin_update_status(uid, "rejected"):
                                            st.warning(f"Rejected {email}")
                                            st.rerun()
                                elif status == "rejected":
                                    if st.button("↩️ Re-approve", key=f"reappr_{uid}", use_container_width=True):
                                        if admin_update_status(uid, "approved"):
                                            st.success(f"Re-approved {email}")
                                            st.rerun()
                            else:
                                st.markdown("<span style='font-size:0.75rem;color:#94a3b8'>You</span>", unsafe_allow_html=True)
                        with c5:
                            if not is_me:
                                new_role = "user" if role == "admin" else "admin"
                                label = "👤 Make User" if role == "admin" else "👑 Make Admin"
                                if st.button(label, key=f"role_{uid}", use_container_width=True):
                                    if admin_update_role(uid, new_role):
                                        st.success(f"Role updated to {new_role}")
                                        st.rerun()

                        st.divider()

    # ═══════════════ PENDING TAB ═════════════════════════════════
    with tab_pending:
        pending_users = [u for u in users if u.get("status") == "pending"]
        if not pending_users:
            st.success("🎉 No pending registrations.")
        else:
            st.markdown(f"**{len(pending_users)} registration(s) awaiting review:**")
            for u in pending_users:
                uid   = u.get("id", "")
                email = u.get("email", "—")
                name  = u.get("full_name", "")
                joined = u.get("created_at", "")[:10] if u.get("created_at") else "—"

                with st.container():
                    c1, c2, c3 = st.columns([4, 1.5, 1.5])
                    with c1:
                        st.markdown(f"""
                        <div class="user-email">{email}</div>
                        <div class="user-name">{name or 'No name provided'} · Registered {joined}</div>
                        """, unsafe_allow_html=True)
                    with c2:
                        if st.button("✅ Approve", key=f"p_appr_{uid}", use_container_width=True, type="primary"):
                            if admin_update_status(uid, "approved"):
                                st.success(f"Approved {email}")
                                st.rerun()
                    with c3:
                        if st.button("❌ Reject", key=f"p_rej_{uid}", use_container_width=True):
                            if admin_update_status(uid, "rejected"):
                                st.warning(f"Rejected {email}")
                                st.rerun()
                    st.divider()

    # ═══════════════ ACTIVITY LOGS TAB ═══════════════════════════
    with tab_logs:
        with st.spinner("Loading logs…"):
            logs = admin_get_logs(limit=200)

        if not isinstance(logs, list) or not logs:
            st.info("No activity logs found.")
        else:
            action_filter = st.selectbox(
                "Filter by action",
                ["All"] + sorted({l.get("action","") for l in logs}),
                key="log_filter"
            )
            filtered_logs = logs if action_filter == "All" else [l for l in logs if l.get("action") == action_filter]

            log_df = pd.DataFrame([{
                "Time":   l.get("created_at", "")[:19].replace("T", " ") if l.get("created_at") else "—",
                "Action": l.get("action", ""),
                "Detail": l.get("detail", ""),
            } for l in filtered_logs])

            st.dataframe(
                log_df,
                use_container_width=True,
                hide_index=True,
                height=420,
            )

            csv = log_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Export Logs CSV", data=csv, file_name="activity_logs.csv", mime="text/csv")