import sys
import os
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import asyncio

# ---  Path Hacking ---
# This adds the parent directory to the path so imports work reliably.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now we can safely import our backend logic
from health_ops_mcp.storage import store
from health_ops_mcp.server import suggest_assignments, assign_shift

# --- APP CONFIG ---
st.set_page_config(
    page_title="Arya Health Ops Agent", 
    page_icon="🏥", 
    layout="wide"
)

# --- HELPERS ---
def get_metrics():
    """
    Quick aggregation for the top dashboard banner.
    In a real app, this would be a cached SQL query.
    """
    total_shifts = len(store.shifts)
    open_shifts = sum(1 for s in store.shifts.values() if s.status == "open")
    compliance_issues = sum(1 for c in store.compliance.values() if c.status == "expiring")
    return total_shifts, open_shifts, compliance_issues

async def run_analysis():
    """
    Bridge between Sync (Streamlit) and Async (MCP Tools).
    Fetches the agent's staffing plan for the next 7 days.
    """
    return await suggest_assignments(
        location_id="loc_nyc", 
        from_ts=datetime.now(timezone.utc).isoformat(),
        to_ts=(datetime.now(timezone.utc) + pd.Timedelta(days=7)).isoformat()
    )

# --- HEADER ---
st.title("🏥 Health Ops: Agent Control Plane")

# --- SIDEBAR (Global Controls) ---
with st.sidebar:
    st.header("⚙️ Controls")
    
    # Great for demos: lets you nuke the state and start fresh without restarting the server
    if st.button("🔄 Reset / Seed Data", use_container_width=True):
        store.seed()
        # Nuke the session state too, otherwise old suggestions might stick around
        if 'suggestions' in st.session_state:
            del st.session_state['suggestions']
        st.toast("Database reset to initial state.", icon="✅")
    
    st.divider()
    st.caption("v0.1.0 • Connected to Local MCP Server")

# --- TOP METRICS (The "At a Glance" View) ---
m_total, m_open, m_risk = get_metrics()
c1, c2, c3 = st.columns(3)

c1.metric("Total Shifts", m_total)
# Use 'inverse' delta color so red = bad (needs attention)
c2.metric("Open Shifts", m_open, delta=f"{m_open} needed", delta_color="inverse")
c3.metric("Compliance Risks", m_risk, delta="Critical" if m_risk > 0 else "Safe", delta_color="inverse")

st.divider()

# --- MAIN INTERFACE ---
# Split: Left = "The Truth" (Current Schedule), Right = "The Magic" (Agent Actions)
left_col, right_col = st.columns([0.6, 0.4], gap="medium")

# === LEFT COLUMN: DB STATE ===
with left_col:
    st.subheader("📅 Live Schedule")
    
    # Flatten object data for the dataframe
    shifts_data = []
    for s in store.shifts.values():
        shifts_data.append({
            "Shift ID": s.id,
            "Start": s.starts_at.strftime("%a %H:%M"),
            "Role": s.required_role,
            "Status": s.status,
            "Caregiver": s.caregiver_id if s.caregiver_id else "Unassigned"
        })
    
    df_shifts = pd.DataFrame(shifts_data)

    # Use Streamlit's column_config to make the table look like a SaaS product
    # (hiding indexes, formatting status tags, etc.)
    st.dataframe(
        df_shifts, 
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                help="Current state of the shift",
                width="medium",
                options=["open", "assigned"],
                required=True,
            ),
            "Caregiver": st.column_config.TextColumn(
                "Assigned To",
                help="Caregiver ID",
                default="—"
            )
        }
    )

    # Compliance Alerts (The business value feature)
    if m_risk > 0:
        st.warning(f"⚠️ **Compliance Alert:** Found {m_risk} caregivers with expiring licenses.")
        for c in store.compliance.values():
            if c.status == 'expiring':
                cg_name = store.caregivers[c.caregiver_id].name
                st.error(f"**{cg_name} ({c.caregiver_id})**: {c.type} expires on {c.expires_at.strftime('%Y-%m-%d')}")

# === RIGHT COLUMN: AGENT ACTIONS ===
with right_col:
    st.subheader("🤖 Agent Reasoning")
    
    # The "Magic Button"
    if st.button("✨ Analyze & Staff Open Shifts", type="primary", use_container_width=True):
        with st.spinner("Agent is cross-referencing skills, availability, and compliance..."):
            
            # 1. Call the Async Tool
            suggestions = asyncio.run(run_analysis())
            
            # 2. Save to Session State
            # Streamlit reruns the whole script on every interaction. 
            # If we don't save this to state, the suggestions will disappear 
            # the moment you click "Approve" on one of them.
            st.session_state['suggestions'] = suggestions
            
            if not suggestions:
                st.info("No staffing suggestions found. (Are all shifts filled?)")

    # Render the cards from State
    if 'suggestions' in st.session_state and st.session_state['suggestions']:
        st.write(f"**Found {len(st.session_state['suggestions'])} matches:**")
        
        # Loop through suggestions
        # Note: We need 'enumerate' to generate unique keys for the buttons
        for i, s in enumerate(st.session_state['suggestions']):
            
            with st.container(border=True):
                c_text, c_btn = st.columns([0.7, 0.3])
                
                with c_text:
                    st.markdown(f"**Assign `{s['caregiver_id']}`** to **`{s['shift_id']}`**")
                    st.caption(f"Reason: {s['reason']}")
                
                with c_btn:
                    # The Action Trigger
                    if st.button("Approve", key=f"btn_{i}"):
                        result = asyncio.run(assign_shift(s['shift_id'], s['caregiver_id']))
                        
                        if result['ok']:
                            st.toast(f"Shift {s['shift_id']} assigned!", icon="🎉")
                            # Remove the approved item from the list immediately so the UI updates
                            st.session_state['suggestions'].pop(i)
                            st.rerun()
                        else:
                            st.error(f"Error: {result.get('error')}")