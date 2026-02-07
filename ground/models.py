from sqlalchemy import Column, DateTime, Integer, Float
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Telemetry(Base):
    __tablename__ = 'telemetry'

    timestamp = Column(DateTime, primary_key=True)
    satellite_id = Column(Integer, primary_key=True)
    metric_id = Column(Integer, primary_key=True)
    value = Column(Float)

