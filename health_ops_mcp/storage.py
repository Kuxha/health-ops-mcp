from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

from .models import Location, Caregiver, Shift, ComplianceItem


class InMemoryStore:
    def __init__(self) -> None:
        self.locations: Dict[str, Location] = {}
        self.caregivers: Dict[str, Caregiver] = {}
        self.shifts: Dict[str, Shift] = {}
        self.compliance: Dict[str, ComplianceItem] = {}

    def seed(self) -> None:
        # Here I seed a couple of locations, caregivers, shifts, and compliance items
        now = datetime.utcnow()

        loc = Location(
            id="loc_nyc",
            name="NYC Home Care",
            timezone="America/New_York",
        )
        self.locations[loc.id] = loc

        cg1 = Caregiver(
            id="cg_alex",
            name="Alex Nurse",
            role="RN",
            skills=["wound_care", "pediatrics"],
            home_location_id=loc.id,
            max_hours_per_week=40,
            preferred_shift_types=["day"],
        )
        cg2 = Caregiver(
            id="cg_beth",
            name="Beth Care",
            role="RN",
            skills=["wound_care"],
            home_location_id=loc.id,
            max_hours_per_week=30,
            preferred_shift_types=["night"],
        )
        self.caregivers[cg1.id] = cg1
        self.caregivers[cg2.id] = cg2

        shift1 = Shift(
            id="shift_1",
            location_id=loc.id,
            starts_at=now + timedelta(hours=4),
            ends_at=now + timedelta(hours=12),
            required_role="RN",
            required_skill="wound_care",
        )
        shift2 = Shift(
            id="shift_2",
            location_id=loc.id,
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=1, hours=8),
            required_role="RN",
            required_skill="pediatrics",
        )
        self.shifts[shift1.id] = shift1
        self.shifts[shift2.id] = shift2

        comp1 = ComplianceItem(
            id="comp_1",
            caregiver_id=cg1.id,
            type="license",
            expires_at=now + timedelta(days=20),
            status="expiring",
        )
        comp2 = ComplianceItem(
            id="comp_2",
            caregiver_id=cg2.id,
            type="license",
            expires_at=now + timedelta(days=120),
            status="valid",
        )
        self.compliance[comp1.id] = comp1
        self.compliance[comp2.id] = comp2


store = InMemoryStore()
store.seed()
