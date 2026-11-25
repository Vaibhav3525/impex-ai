from sqlalchemy import Column, Integer
from app.core.database import Base

class DispatchLock(Base):
    __tablename__ = "dispatch_lock"
    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False, default=0)
