from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv
import re

from database import engine, get_db, Base
from models import Conversation, Message, Vehicle
from chat_service import ChatService

# Load environment variables
load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Coverix Chatbot API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = ChatService()

# Pydantic models for API
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    message: str
    session_id: str
    current_step: str
    is_complete: bool

class ConversationData(BaseModel):
    session_id: str
    zip_code: Optional[str]
    full_name: Optional[str]
    email: Optional[str]
    license_type: Optional[str]
    license_status: Optional[str]
    vehicles: List[dict]
    current_step: str
    is_complete: bool
    messages: List[dict]


@app.get("/")
def read_root():
    return {"message": "Coverix Chatbot API is running"}


@app.post("/api/start-conversation")
def start_conversation(db: Session = Depends(get_db)):
    """Start a new conversation"""
    session_id = str(uuid.uuid4())
    
    conversation = Conversation(
        session_id=session_id,
        current_step="zip_code"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Add initial greeting message
    greeting = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="Hi! I'm a chat bot here to assist you with getting started on your " \
        "insurance quote. Let's begin with the first step. What is your ZIP code?"
    )
    db.add(greeting)
    db.commit()
    
    return {
        "session_id": session_id,
        "message": greeting.content,
        "current_step": "zip_code"
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Handle chat messages"""
    
    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.session_id == request.session_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check for frustration
    if chat_service.detect_frustration(request.message):
        zen_quote = await chat_service.get_zen_quote()
        
        # Save messages
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message
        )
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=zen_quote
        )
        db.add(user_msg)
        db.add(assistant_msg)
        db.commit()
        
        return ChatResponse(
            message=zen_quote,
            session_id=request.session_id,
            current_step=conversation.current_step,
            is_complete=conversation.is_complete
        )
    
    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()
    
    # Process based on current step
    response_text, next_step = await process_step(
        conversation, 
        request.message, 
        db
    )
    
    # Update conversation step
    conversation.current_step = next_step
    conversation.updated_at = datetime.utcnow()
    
    # Save assistant message
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text
    )
    db.add(assistant_message)
    db.commit()
    
    return ChatResponse(
        message=response_text,
        session_id=request.session_id,
        current_step=next_step,
        is_complete=conversation.is_complete
    )


async def process_step(conversation: Conversation, user_input: str, db: Session):
    """Process user input based on current step"""
    
    step = conversation.current_step
    user_input = user_input.strip()
    
    # ZIP CODE
    if step == "zip_code":
        if re.match(r'^\d{5}$', user_input):
            conversation.zip_code = user_input
            db.commit()
            return "Great! Now, what's your full name?", "full_name"
        else:
            return "Please enter a valid 5-digit ZIP code.", "zip_code"
    
    # FULL NAME
    elif step == "full_name":
        if len(user_input) >= 2:
            conversation.full_name = user_input
            db.commit()
            return "Thanks! What's your email address?", "email"
        else:
            return "Please enter your full name.", "full_name"
    
    # EMAIL
    elif step == "email":
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', user_input):
            conversation.email = user_input
            db.commit()
            return "Perfect! Now let's add a vehicle. Would you like to add a vehicle? (yes/no)", "vehicle_intro"
        else:
            return "Please enter a valid email address.", "email"
    
    # VEHICLE INTRO
    elif step == "vehicle_intro":
        if user_input.lower() in ["yes", "y", "sure", "ok", "okay"]:
            return "Great! Please provide either:\n- VIN (17 characters), OR\n- Year, Make, and Body Type", "vehicle_identification"
        else:
            return "No problem! What's your US License Type? (Foreign, Personal, or Commercial)", "license_type"
    
    # VEHICLE IDENTIFICATION
    elif step == "vehicle_identification":
        # Check if VIN (17 alphanumeric characters)
        vin_match = re.search(r'\b[A-HJ-NPR-Z0-9]{17}\b', user_input.upper())
        
        if vin_match:
            vin = vin_match.group(0)
            validation = await chat_service.validate_vehicle_nhtsa(vin=vin)
            
            if validation["valid"]:
                # Create vehicle with VIN
                vehicle = Vehicle(
                    conversation_id=conversation.id,
                    vin=vin,
                    year=validation.get("year"),
                    make=validation.get("make")
                )
                db.add(vehicle)
                db.commit()
                
                # Store current vehicle ID in a temp way (we'll use the last vehicle)
                return f"Vehicle validated! How is this vehicle used? (commuting, commercial, farming, or business)", "vehicle_use"
            else:
                return "Sorry, that VIN doesn't appear to be valid. Please check and try again, or provide Year, Make, and Body Type instead.", "vehicle_identification"
        else:
            # Try to extract year, make, body type
            year_match = re.search(r'\b(19|20)\d{2}\b', user_input)
            
            if year_match:
                year = year_match.group(0)
                # Extract make (common car brands)
                input_lower = user_input.lower()
                makes = ["toyota", "honda", "ford", "chevrolet", "chevy", "nissan", "bmw", "mercedes", "audi", "volkswagen", "vw", "hyundai", "kia", "mazda", "subaru", "jeep", "ram", "gmc", "dodge", "lexus", "acura", "infiniti", "cadillac", "buick", "tesla"]
                make = None
                for m in makes:
                    if m in input_lower:
                        make = m.title()
                        if m == "chevy":
                            make = "Chevrolet"
                        elif m == "vw":
                            make = "Volkswagen"
                        break
                
                if make:
                    # Validate with NHTSA
                    validation = await chat_service.validate_vehicle_nhtsa(year=year, make=make)
                    
                    if validation["valid"]:
                        # Extract body type if present
                        body_types = ["sedan", "suv", "truck", "coupe", "van", "wagon", "hatchback", "convertible"]
                        body_type = None
                        for bt in body_types:
                            if bt in input_lower:
                                body_type = bt.title()
                                break
                        
                        vehicle = Vehicle(
                            conversation_id=conversation.id,
                            year=year,
                            make=make,
                            body_type=body_type
                        )
                        db.add(vehicle)
                        db.commit()
                        
                        return f"Great! How is this {year} {make} used? (commuting, commercial, farming, or business)", "vehicle_use"
                    else:
                        return f"Sorry, I couldn't validate a {year} {make}. Please check the information and try again.", "vehicle_identification"
            
            return "I couldn't understand that. Please provide either a VIN or Year, Make, and Body Type (e.g., '2020 Toyota Sedan')", "vehicle_identification"
    
    # VEHICLE USE
    elif step == "vehicle_use":
        use_lower = user_input.lower()
        valid_uses = ["commuting", "commercial", "farming", "business"]
        
        matched_use = None
        for use in valid_uses:
            if use in use_lower:
                matched_use = use
                break
        
        if matched_use:
            # Get the last vehicle added
            vehicle = db.query(Vehicle).filter(
                Vehicle.conversation_id == conversation.id
            ).order_by(Vehicle.id.desc()).first()
            
            vehicle.vehicle_use = matched_use
            db.commit()
            
            return "Does this vehicle have blind spot warning? (yes/no)", "blind_spot_warning"
        else:
            return "Please specify: commuting, commercial, farming, or business", "vehicle_use"
    
    # BLIND SPOT WARNING
    elif step == "blind_spot_warning":
        response = user_input.lower()
        
        vehicle = db.query(Vehicle).filter(
            Vehicle.conversation_id == conversation.id
        ).order_by(Vehicle.id.desc()).first()
        
        if response in ["yes", "y", "true", "has it", "equipped"]:
            vehicle.blind_spot_warning = True
            db.commit()
        elif response in ["no", "n", "false", "doesn't have", "not equipped"]:
            vehicle.blind_spot_warning = False
            db.commit()
        else:
            return "Please answer yes or no.", "blind_spot_warning"
        
        # Branch based on vehicle use
        if vehicle.vehicle_use == "commuting":
            return "How many days per week do you use this vehicle for commuting? (1-7)", "commuting_days"
        else:
            return "What's the annual mileage for this vehicle?", "annual_mileage"
    
    # COMMUTING DAYS
    elif step == "commuting_days":
        try:
            days = int(user_input)
            if 1 <= days <= 7:
                vehicle = db.query(Vehicle).filter(
                    Vehicle.conversation_id == conversation.id
                ).order_by(Vehicle.id.desc()).first()
                
                vehicle.days_per_week = days
                db.commit()
                
                return "What's the one-way distance to work/school in miles?", "commuting_miles"
            else:
                return "Please enter a number between 1 and 7.", "commuting_days"
        except ValueError:
            return "Please enter a number between 1 and 7.", "commuting_days"
    
    # COMMUTING MILES
    elif step == "commuting_miles":
        try:
            miles = int(user_input)
            if miles >= 0:
                vehicle = db.query(Vehicle).filter(
                    Vehicle.conversation_id == conversation.id
                ).order_by(Vehicle.id.desc()).first()
                
                vehicle.one_way_miles = miles
                db.commit()
                
                return "Would you like to add another vehicle? (yes/no)", "add_another_vehicle"
            else:
                return "Please enter a positive number.", "commuting_miles"
        except ValueError:
            return "Please enter the number of miles.", "commuting_miles"
    
    # ANNUAL MILEAGE
    elif step == "annual_mileage":
        try:
            mileage = int(user_input)
            if mileage >= 0:
                vehicle = db.query(Vehicle).filter(
                    Vehicle.conversation_id == conversation.id
                ).order_by(Vehicle.id.desc()).first()
                
                vehicle.annual_mileage = mileage
                db.commit()
                
                return "Would you like to add another vehicle? (yes/no)", "add_another_vehicle"
            else:
                return "Please enter a positive number.", "annual_mileage"
        except ValueError:
            return "Please enter the annual mileage as a number.", "annual_mileage"
    
    # ADD ANOTHER VEHICLE
    elif step == "add_another_vehicle":
        if user_input.lower() in ["yes", "y", "sure"]:
            return "Great! Please provide either:\n- VIN (17 characters), OR\n- Year, Make, and Body Type", "vehicle_identification"
        else:
            return "Okay! What's your US License Type? (Foreign, Personal, or Commercial)", "license_type"
    
    # LICENSE TYPE
    elif step == "license_type":
        license_lower = user_input.lower()
        
        if "foreign" in license_lower:
            conversation.license_type = "Foreign"
            conversation.is_complete = True
            db.commit()
            return "Thank you for providing all your information! We'll be in touch soon with your quote.", "complete"
        elif "personal" in license_lower:
            conversation.license_type = "Personal"
            db.commit()
            return "Is your license valid or suspended?", "license_status"
        elif "commercial" in license_lower:
            conversation.license_type = "Commercial"
            db.commit()
            return "Is your license valid or suspended?", "license_status"
        else:
            return "Please specify: Foreign, Personal, or Commercial", "license_type"
    
    # LICENSE STATUS
    elif step == "license_status":
        status_lower = user_input.lower()
        
        if "valid" in status_lower:
            conversation.license_status = "valid"
            conversation.is_complete = True
            db.commit()
            return "Perfect! Thank you for providing all your information. We'll process your quote and be in touch soon!", "complete"
        elif "suspend" in status_lower:
            conversation.license_status = "suspended"
            conversation.is_complete = True
            db.commit()
            return "Thank you for providing all your information. We'll review your application and contact you shortly.", "complete"
        else:
            return "Please answer: valid or suspended", "license_status"
    
    # DEFAULT
    return "I didn't understand that. Could you try again?", step


@app.get("/api/conversation/{session_id}", response_model=ConversationData)
def get_conversation(session_id: str, db: Session = Depends(get_db)):
    """Get full conversation data - for viewing transcripts"""
    
    conversation = db.query(Conversation).filter(
        Conversation.session_id == session_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get all messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.timestamp).all()
    
    # Get all vehicles
    vehicles = db.query(Vehicle).filter(
        Vehicle.conversation_id == conversation.id
    ).all()
    
    return ConversationData(
        session_id=conversation.session_id,
        zip_code=conversation.zip_code,
        full_name=conversation.full_name,
        email=conversation.email,
        license_type=conversation.license_type,
        license_status=conversation.license_status,
        vehicles=[{
            "id": v.id,
            "vin": v.vin,
            "year": v.year,
            "make": v.make,
            "body_type": v.body_type,
            "vehicle_use": v.vehicle_use,
            "blind_spot_warning": v.blind_spot_warning,
            "days_per_week": v.days_per_week,
            "one_way_miles": v.one_way_miles,
            "annual_mileage": v.annual_mileage
        } for v in vehicles],
        current_step=conversation.current_step,
        is_complete=conversation.is_complete,
        messages=[{
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat()
        } for m in messages]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)