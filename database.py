import os
import json
from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker


from health_ops_mcp.models import Shift, Location, Caregiver, ComplianceItem

# Setting UP DB
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///local_demo.db"

# db stuff
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base() 

# We only stor ingShifts in SQL for now 
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

# 4. REPOSITORY: The Class that manages data
class PostgresStore:
    def __init__(self):
        Base.metadata.create_all(bind=engine)
        self._seed_static_data()


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