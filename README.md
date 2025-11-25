# health-ops-mcp

An MCP server that models staffing and compliance agents over a synthetic home-care workforce dataset.

## What it does

Exposes MCP tools that let an agent:

- List open RN shifts for a location in a time window.
- Suggest caregiver assignments based on role, skills, and day/night preference.
- Assign a caregiver to an open shift.
- List caregivers with expiring compliance items (for example licenses).

All data is synthetic. A real EMR or HR/payroll system could sit behind the same interfaces with minimal changes to the tool signatures.

## Demo video 

Link : youtube.com/watch?v=Me-UrRhvh_A&feature=youtu.be

## Running

From the project root:

1. Activate the virtualenv  
   - source .venv/bin/activate

2. Start the MCP dev server  
   - mcp dev health_ops_mcp/server.py

This starts the MCP server and opens the MCP Inspector in your browser.

## Example flow (from MCP Inspector)

1. Call "list_open_shifts"  
   - Arguments:  
     - location_id = "loc_nyc"  
     - from_ts = "2020-01-01T00:00:00"  
     - to_ts   = "2030-01-01T00:00:00"  
   - Effect: returns open RN shifts at the NYC Home Care location.

2. Call "suggest_assignments"  
   - Arguments:  
     - location_id = "loc_nyc"  
     - from_ts = "2020-01-01T00:00:00"  
     - to_ts   = "2030-01-01T00:00:00"  
     - strategy = "fair_load"  
   - Effect: proposes caregivers for the open shifts, preferring those whose shift preferences (day or night) match the shift start time, while still enforcing role and skill match.

3. Call "assign_shift"  
   - Example arguments:  
     - shift_id = "shift_1"  
     - caregiver_id = "cg_beth"  
     - source = "agent"  
   - Effect: marks shift_1 as "assigned" to cg_beth in the synthetic dataset.

4. Call "list_open_shifts" again  
   - Use the same arguments as in step 1.  
   - Effect: shift_1 no longer appears as open; only remaining open shifts are listed.

5. Call "list_expiring_compliance"  
   - Arguments:  
     - days_ahead = 30  
   - Effect: returns caregivers with compliance items (for example licenses) expiring in the next 30 days, so an agent could trigger notifications or adjust scheduling.
