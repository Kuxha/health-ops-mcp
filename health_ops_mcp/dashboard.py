import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import asyncio

# Import your actual backend logic
from health_ops_mcp.main import store, suggest_assignments, assign_shift

st.set_page_config(page_title="Arya Health Ops Agent", layout="wide")

st.title("🏥 Health Ops: Agent Control Plane")

# Sidebar for controls
with st.sidebar:
    st.header("Agent Controls")
    if st.button("Reset / Seed Data"):
        store.seed()
        st.success("Database reset to initial state.")
    
    st.divider()
    st.info("This dashboard visualizes the state of the MCP Server.")

# COL 1: Shift Schedule
st.subheader("📅 Live Schedule State")
shifts_data = []
for s in store.shifts.values():
    shifts_data.append({
        "ID": s.id,
        "Start": s.starts_at.strftime("%H:%M"),
        "End": s.ends_at.strftime("%H:%M"),
        "Role": s.required_role,
        "Status": s.status,
        "Assigned To": s.caregiver_id if s.caregiver_id else "—"
    })

df_shifts = pd.DataFrame(shifts_data)

# Highlight unassigned shifts
def highlight_status(val):
    color = '#ffcccb' if val == 'open' else '#90ee90'
    return f'background-color: {color}'

st.dataframe(df_shifts.style.applymap(highlight_status, subset=['Status']), use_container_width=True)

# COL 2: Actions
col1, col2 = st.columns(2)

with col1:
    st.subheader("🤖 Agent Reasoning")
    if st.button("Ask Agent to Suggest Assignments"):
        # We wrap the async call since Streamlit is sync
        suggestions = asyncio.run(suggest_assignments(
            location_id="loc_nyc", 
            from_ts=datetime.now(timezone.utc).isoformat(),
            to_ts=(datetime.now(timezone.utc) + pd.Timedelta(days=2)).isoformat()
        ))
        
        if suggestions:
            for s in suggestions:
                st.write(f"**Suggestion:** Assign `{s['caregiver_id']}` to `{s['shift_id']}`")
                st.caption(f"Reason: {s['reason']}")
                
                if st.button(f"Approve {s['shift_id']}", key=s['shift_id']):
                    res = asyncio.run(assign_shift(s['shift_id'], s['caregiver_id']))
                    if res['ok']:
                        st.success(f"Assigned! Refreshing...")
                        st.rerun()
                    else:
                        st.error(f"Failed: {res.get('error')}")
        else:
            st.warning("No suggestions found.")

with col2:
    st.subheader("⚠️ Compliance Watch")
    # Quick visual for expiring licenses
    count_expiring = sum(1 for c in store.compliance.values() if c.status == 'expiring')
    st.metric(label="Expiring Licenses (30d)", value=count_expiring, delta="-1" if count_expiring > 0 else "0", delta_color="inverse")
    
    for c in store.compliance.values():
        if c.status == 'expiring':
            st.error(f"License for {c.caregiver_id} expires on {c.expires_at.date()}")