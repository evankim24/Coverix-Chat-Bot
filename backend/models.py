from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User info
    zip_code = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    license_type = Column(String, nullable=True)
    license_status = Column(String, nullable=True)
    
    # Current state
    current_step = Column(String, default="zip_code")
    is_complete = Column(Boolean, default=False)
    
    # Relationships
    vehicles = relationship("Vehicle", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    
    # Vehicle identification
    vin = Column(String, nullable=True)
    year = Column(String, nullable=True)
    make = Column(String, nullable=True)
    body_type = Column(String, nullable=True)
    
    # Vehicle details
    vehicle_use = Column(String, nullable=True)
    blind_spot_warning = Column(Boolean, nullable=True)
    
    # Commuting specific
    days_per_week = Column(Integer, nullable=True)
    one_way_miles = Column(Integer, nullable=True)
    
    # Commercial/farming/business specific
    annual_mileage = Column(Integer, nullable=True)
    
    conversation = relationship("Conversation", back_populates="vehicles")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String)  # user, assistant, system
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")