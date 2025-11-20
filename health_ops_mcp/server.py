from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from health_ops_mcp.storage import store
from health_ops_mcp.models import Shift, Caregiver



mcp = FastMCP("health-ops")


def _parse_window(from_ts: str, to_ts: str) -> tuple[datetime, datetime]:
    """Here I parse ISO8601 timestamps into datetimes."""
    start = datetime.fromisoformat(from_ts)
    end = datetime.fromisoformat(to_ts)
    return start, end


@mcp.tool()
async def list_open_shifts(
    location_id: str | None,
    from_ts: str,
    to_ts: str,
) -> List[Dict[str, Any]]:
    """Here I list open shifts in a time window.

    Args:
        location_id: Optional location filter (e.g. 'loc_nyc').
        from_ts: Start of window (ISO8601).
        to_ts: End of window (ISO8601).
    """
    start, end = _parse_window(from_ts, to_ts)

    results: List[Dict[str, Any]] = []
    for shift in store.shifts.values():
        if shift.status != "open":
            continue
        if location_id is not None and shift.location_id != location_id:
            continue
        if not (start <= shift.starts_at <= end):
            continue
        results.append(shift.model_dump())
    return results


@mcp.tool()
async def suggest_assignments(
    location_id: str,
    from_ts: str,
    to_ts: str,
    strategy: str = "fair_load",
) -> List[Dict[str, Any]]:
    """Here I suggest caregiver assignments for open shifts.

    Simple heuristic:
    - role and skills must match
    - caregiver must belong to location
    - prefer caregivers whose preferred_shift_types match the shift time
    """
    start, end = _parse_window(from_ts, to_ts)

    caregivers: List[Caregiver] = [
        c for c in store.caregivers.values() if c.home_location_id == location_id
    ]

    def classify_shift(shift: Shift) -> str:
        # Here I classify shifts roughly as "day" vs "night" based on start hour
        hour = shift.starts_at.hour
        return "day" if 7 <= hour < 19 else "night"

    suggestions: List[Dict[str, Any]] = []

    for shift in store.shifts.values():
        if shift.status != "open":
            continue
        if shift.location_id != location_id:
            continue
        if not (start <= shift.starts_at <= end):
            continue

        shift_type = classify_shift(shift)

        # First pass: caregivers with matching preferred_shift_types
        primary_candidates: List[Caregiver] = []
        secondary_candidates: List[Caregiver] = []

        for cg in caregivers:
            if cg.role != shift.required_role:
                continue
            if shift.required_skill not in cg.skills:
                continue

            if shift_type in cg.preferred_shift_types:
                primary_candidates.append(cg)
            else:
                secondary_candidates.append(cg)

        chosen: Caregiver | None = None
        if primary_candidates:
            chosen = primary_candidates[0]
        elif secondary_candidates:
            chosen = secondary_candidates[0]

        if chosen is None:
            continue

        suggestions.append(
            {
                "shift_id": shift.id,
                "caregiver_id": chosen.id,
                "score": 1.0,
                "reason": f"role_and_skill_match; shift_type={shift_type}",
            }
        )

    return suggestions

@mcp.tool()
async def assign_shift(
    shift_id: str,
    caregiver_id: str,
    source: str = "agent",
) -> Dict[str, Any]:
    """Here I assign a caregiver to a shift if valid."""
    if shift_id not in store.shifts:
        return {"ok": False, "error": "shift_not_found"}
    if caregiver_id not in store.caregivers:
        return {"ok": False, "error": "caregiver_not_found"}

    shift: Shift = store.shifts[shift_id]
    if shift.status != "open":
        return {"ok": False, "error": "shift_not_open"}

    shift.caregiver_id = caregiver_id
    shift.status = "assigned"

    return {
        "ok": True,
        "shift": shift.model_dump(),
        "source": source,
    }


@mcp.tool()
async def list_expiring_compliance(days_ahead: int = 30) -> List[Dict[str, Any]]:
    """Here I list caregivers with compliance items expiring soon.

    Args:
        days_ahead: Lookahead window in days (default 30).
    """
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days_ahead)

    results: List[Dict[str, Any]] = []
    for comp in store.compliance.values():
        if now <= comp.expires_at <= cutoff:
            cg = store.caregivers[comp.caregiver_id]
            results.append(
                {
                    "caregiver_id": cg.id,
                    "caregiver_name": cg.name,
                    "type": comp.type,
                    "expires_at": comp.expires_at.isoformat(),
                }
            )
    return results


@mcp.resource("resource://workforce_schema", description="Synthetic workforce schema for the health-ops MCP server.")
async def workforce_schema() -> str:
    """Here I describe the synthetic workforce schema used by this MCP server."""
    return """
Entities:
- Location(id, name, timezone)
- Caregiver(id, name, role, skills[], home_location_id, max_hours_per_week, preferred_shift_types[])
- Shift(id, location_id, starts_at, ends_at, required_role, required_skill, status, caregiver_id?)
- ComplianceItem(id, caregiver_id, type, expires_at, status)
"""



def main() -> None:
    print("health-ops-mcp: starting MCP server on stdio")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
