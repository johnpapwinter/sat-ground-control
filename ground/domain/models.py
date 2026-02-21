from sqlalchemy import Column, DateTime, Integer, Float, Enum, BigInteger, JSON
from sqlalchemy.orm import DeclarativeBase

from ground.domain.enums import CommandPriority, CommandState


class Base(DeclarativeBase):
    pass


class Telemetry(Base):
    __tablename__ = 'telemetry'

    timestamp = Column(DateTime, primary_key=True)
    satellite_id = Column(Integer, primary_key=True)
    metric_id = Column(Integer, primary_key=True)
    value = Column(Float)


class PacketGap(Base):
    __tablename__ = 'packet_gaps'

    timestamp = Column(DateTime, primary_key=True)
    satellite_id = Column(Integer, primary_key=True)
    apid = Column(Integer, primary_key=True)
    expected_seq = Column(Integer)
    received_seq = Column(Integer)
    gap_size = Column(Integer)


class CommandEntry(Base):
    __tablename__ = 'command_entries'

    command_id = Column(BigInteger, primary_key=True, autoincrement=True)
    command_payload = Column(JSON)
    priority_level = Column(Enum(CommandPriority, native_enum=False))
    state = Column(Enum(CommandState, native_enum=False))
    opcode = Column(Integer)
    timestamp = Column(DateTime)


