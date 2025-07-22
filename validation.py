#!/usr/bin/env python3
"""
SERVICE-HERO Input Validation
Secure input validation for all user inputs
"""

import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator, EmailStr


class PhoneNumber:
    """Phone number validation utility"""
    
    @staticmethod
    def clean(phone: str) -> str:
        """Clean and format phone number"""
        if not phone:
            raise ValueError("Phone number is required")
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Add +1 if no country code
        if not cleaned.startswith('+') and len(cleaned) == 10:
            cleaned = '+1' + cleaned
        
        return cleaned
    
    @staticmethod
    def validate(phone: str) -> bool:
        """Validate phone number format"""
        try:
            cleaned = PhoneNumber.clean(phone)
            return bool(re.match(r'^\+?[\d]{10,15}$', cleaned))
        except:
            return False


class TextSanitizer:
    """Text input sanitization"""
    
    @staticmethod
    def is_safe(text: str) -> bool:
        """Check if text is safe from XSS"""
        if not text:
            return True
        
        # Block HTML tags and scripts
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'<iframe',
            r'<img.*onerror',
            r'<.*onclick'
        ]
        
        text_lower = text.lower()
        return not any(re.search(pattern, text_lower) for pattern in dangerous_patterns)
    
    @staticmethod
    def sanitize(text: str, max_length: int = 500) -> str:
        """Sanitize text input"""
        if not text:
            return ""
        
        # Truncate if too long
        text = text[:max_length]
        
        # Remove potentially dangerous characters
        text = re.sub(r'[<>"\']', '', text)
        
        return text.strip()


class PlumberEmergencyRequest(BaseModel):
    """Validated plumber emergency request"""
    customer_phone: str = Field(min_length=10, max_length=20)
    location: str = Field(min_length=5, max_length=200)
    issue: str = Field(min_length=5, max_length=500)
    urgency: str = Field(pattern="^(low|medium|high|critical)$")
    
    @validator('customer_phone')
    def validate_phone(cls, v):
        if not PhoneNumber.validate(v):
            raise ValueError('Invalid phone number format')
        return PhoneNumber.clean(v)
    
    @validator('location')
    def validate_location(cls, v):
        if not TextSanitizer.is_safe(v):
            raise ValueError('Location contains unsafe content')
        return TextSanitizer.sanitize(v, 200)
    
    @validator('issue')
    def validate_issue(cls, v):
        if not TextSanitizer.is_safe(v):
            raise ValueError('Issue description contains unsafe content')
        return TextSanitizer.sanitize(v, 500)


class DentalAppointmentRequest(BaseModel):
    """Validated dental appointment request"""
    patient_name: str = Field(min_length=1, max_length=100)
    patient_email: EmailStr
    patient_phone: str = Field(min_length=10, max_length=20)
    appointment_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    appointment_time: str = Field(pattern=r'^\d{1,2}:\d{2}$')
    service_type: str = Field(max_length=100)
    
    @validator('patient_name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z\s\-\.]+$', v):
            raise ValueError('Name contains invalid characters')
        return v.strip()
    
    @validator('patient_phone')
    def validate_phone(cls, v):
        if not PhoneNumber.validate(v):
            raise ValueError('Invalid phone number format')
        return PhoneNumber.clean(v)
    
    @validator('service_type')
    def validate_service(cls, v):
        allowed = ['cleaning', 'checkup', 'filling', 'crown', 'extraction']
        if v.lower() not in allowed:
            raise ValueError('Invalid service type')
        return v.strip()


class WorkflowRequest(BaseModel):
    """Generic workflow request with validation"""
    template_id: str = Field(pattern="^[a-z_]+$")
    trigger_data: Dict[str, Any]
    
    @validator('template_id')
    def validate_template(cls, v):
        allowed_templates = ['plumber_emergency', 'dental_appointment']
        if v not in allowed_templates:
            raise ValueError('Invalid template ID')
        return v