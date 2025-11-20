from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class Location(BaseModel):
    id: str
    name: str
    timezone: str


class Caregiver(BaseModel):
    id: str
    name: str
    role: str              # e.g. "RN"
    skills: List[str]      # e.g. ["wound_care", "pediatrics"]
    home_location_id: str
    max_hours_per_week: int
    preferred_shift_types: List[str]  # e.g. ["day", "night"]


ShiftStatus = Literal["open", "held", "assigned"]


class Shift(BaseModel):
    id: str
    location_id: str
    starts_at: datetime
    ends_at: datetime
    required_role: str
    required_skill: str
    status: ShiftStatus = "open"
    caregiver_id: Optional[str] = None


class ComplianceItem(BaseModel):
    id: str
    caregiver_id: str
    type: str              # e.g. "license", "cpr"
    expires_at: datetime
    status: Literal["valid", "expiring", "expired"]
