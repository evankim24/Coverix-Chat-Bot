import openai
import os
from typing import List, Dict
import httpx
import re

class ChatService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
    
    def get_system_prompt(self, current_step: str, user_data: dict) -> str:
        """Generate system prompt based on current step"""
        base_prompt = """You are a helpful insurance onboarding assistant. Your job is to collect information from users in a friendly, conversational manner.

CRITICAL RULES:
1. Only ask for ONE piece of information at a time
2. Keep responses SHORT (1-2 sentences max)
3. Be friendly and conversational
4. If user seems frustrated, acknowledge it warmly
5. Never provide information they haven't given you yet

"""
        
        step_prompts = {
            "zip_code": "Ask for their ZIP code. Be friendly and brief.",
            "full_name": "Ask for their full name.",
            "email": "Ask for their email address.",
            "vehicle_intro": "Ask if they'd like to add a vehicle. Mention they can add multiple.",
            "vehicle_identification": "Ask for either VIN OR Year, Make, and Body Type. Let them choose.",
            "vehicle_use": "Ask how the vehicle is used: commuting, commercial, farming, or business.",
            "blind_spot_warning": "Ask if the vehicle has blind spot warning (yes/no).",
            "commuting_days": "Ask how many days per week they commute (1-7).",
            "commuting_miles": "Ask for one-way miles to work/school.",
            "annual_mileage": "Ask for annual mileage.",
            "add_another_vehicle": "Ask if they want to add another vehicle (yes/no).",
            "license_type": "Ask for license type: Foreign, Personal, or Commercial.",
            "license_status": "Ask if their license is valid or suspended.",
            "complete": "Thank them warmly for completing the process!"
        }
        
        current_prompt = step_prompts.get(current_step, "Continue naturally.")
        
        return f"{base_prompt}\nCURRENT TASK: {current_prompt}"
    
    async def get_response(self, messages: List[Dict], current_step: str, user_data: dict) -> str:
        """Get response from OpenAI"""
        system_message = {
            "role": "system",
            "content": self.get_system_prompt(current_step, user_data)
        }
        
        full_messages = [system_message] + messages[-10:]  # Keep last 10 messages for context
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "I'm having trouble right now. Could you try again?"
    
    def detect_frustration(self, message: str) -> bool:
        """Detect if user is frustrated"""
        frustration_keywords = [
            "frustrated", "annoyed", "angry", "human", "agent", 
            "representative", "help", "speak to someone", "talk to someone",
            "this is ridiculous", "waste of time"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in frustration_keywords)
    
    async def validate_vehicle_nhtsa(self, vin: str = None, year: str = None, make: str = None) -> dict:
        """Validate vehicle against NHTSA API"""
        try:
            if vin:
                url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
            else:
                url = f"https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMakeYear/make/{make}/modelyear/{year}?format=json"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                data = response.json()
                
                if vin:
                    results = data.get("Results", [])
                    error_code = next((r.get("ErrorCode") for r in results if "ErrorCode" in r), None)
                    if error_code == "0":
                        # Extract make and model
                        make_result = next((r.get("Value") for r in results if r.get("Variable") == "Make"), None)
                        model_result = next((r.get("Value") for r in results if r.get("Variable") == "Model"), None)
                        year_result = next((r.get("Value") for r in results if r.get("Variable") == "Model Year"), None)
                        return {
                            "valid": True,
                            "make": make_result,
                            "model": model_result,
                            "year": year_result
                        }
                    return {"valid": False}
                else:
                    results = data.get("Results", [])
                    return {"valid": len(results) > 0}
        except Exception as e:
            print(f"NHTSA API Error: {e}")
            return {"valid": False}
    
    async def get_zen_quote(self) -> str:
        """Get a zen quote for frustrated users"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://zenquotes.io/api/quotes", timeout=5.0)
                data = response.json()
                if data and len(data) > 0:
                    quote = data[0]
                    return f"I understand. Here's something calming: \"{quote['q']}\" - {quote['a']}\n\nWould you like me to connect you with a human representative?"
        except Exception as e:
            print(f"Zen Quote API Error: {e}")
        return "I understand you'd like to speak with someone. Let me connect you with a human representative."