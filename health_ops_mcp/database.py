import os
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

from health_ops_mcp.models import Shift, Location, Caregiver, ComplianceItem

# 1. SETUP: Get the secret URL
DATABASE_URL = os.getenv("DATABASE_URL")

# FIX: DigitalOcean requires SSL. If missing, we force it.
if DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

# Fallback: Use local file if no Cloud DB
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///local_demo.db"

# 2. ENGINE
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base() 

# 3. TABLE
class ShiftDB(Base):
    """
    Hybrid storage model for Shifts.
    Critical query fields (id, status) are indexed columns.
    Full object data is stored as JSON for schema flexibility.
    """
    __tablename__ = "shifts"
    id = Column(String, primary_key=True)
    status = Column(String)
    data = Column(JSON)

# 4. REPOSITORY
class PostgresStore:
    def __init__(self):
        Base.metadata.create_all(bind=engine)
        self._seed_static_data()
        self._seed_db_if_empty() # <--- Added this back so you have shifts!

    def _seed_static_data(self):
        # Keeping caregivers in memory for the MVP phase
        self.locations = {}
        self.caregivers = {}
        self.compliance = {}
        
        # Seed NYC Location
        nyc = Location(id="loc_nyc", name="NYC Home Care", timezone="America/New_York")
        self.locations[nyc.id] = nyc

        # Seed Caregivers
        nurse = Caregiver(
            id="cg_alex", 
            name="Alex Nurse", 
            role="RN", 
            skills=["wound_care", "pediatrics"],
            home_location_id=nyc.id, 
            max_hours_per_week=40, 
            preferred_shift_types=["day"]
        )
        self.caregivers[nurse.id] = nurse

    def _seed_db_if_empty(self):
        with SessionLocal() as db:
            if db.query(ShiftDB).first() is None:
                # Create a sample shift so the dashboard isn't empty
                now = datetime.now(timezone.utc)
                s = Shift(
                    id="shift_1",
                    location_id="loc_nyc",
                    starts_at=now + timedelta(hours=4),
                    ends_at=now + timedelta(hours=12),
                    required_role="RN",
                    required_skill="wound_care"
                )
                self.save_shift(s)

    # --- Read Operations ---
    def get_shift(self, shift_id):
        with SessionLocal() as db:
            row = db.query(ShiftDB).filter(ShiftDB.id == shift_id).first()
            if row:
                shift_obj = Shift.model_validate(row.data)
                shift_obj.status = row.status
                return shift_obj
            return None
        
    @property
    def shifts(self):
        """
        Retrieve all shifts from the database.
        Returns a dictionary keyed by shift ID.
        """
        with SessionLocal() as db:
            rows = db.query(ShiftDB).all()
            result_dict = {}
            for row in rows:
                shift_obj = Shift.model_validate(row.data)
                result_dict[shift_obj.id] = shift_obj
            return result_dict
        
    # --- Write Operations ---
    def save_shift(self, shift):
        with SessionLocal() as db:
            row = db.query(ShiftDB).filter(ShiftDB.id == shift.id).first()
            
            shift_data = shift.model_dump(mode='json')
            
            if row:
                row.status = shift.status
                row.data = shift_data
            else:
                row = ShiftDB(id=shift.id, status=shift.status, data=shift_data)
                db.add(row)
            
            db.commit()

    def seed(self):
        """Resets the DB (Used by Dashboard Reset Button)"""
        with SessionLocal() as db:
            db.query(ShiftDB).delete()
            db.commit()
        self._seed_db_if_empty()

store = PostgresStore()