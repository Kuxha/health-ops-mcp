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