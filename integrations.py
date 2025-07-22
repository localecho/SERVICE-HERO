#!/usr/bin/env python3
"""
SERVICE-HERO Integrations
Real integration handlers for external services
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime
import asyncio

# Third-party integrations
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class TwilioIntegration:
    """Real Twilio SMS integration"""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_phone = os.getenv("TWILIO_FROM_PHONE")
        
        if self.account_sid and self.auth_token:
            self.client = TwilioClient(self.account_sid, self.auth_token)
            self.enabled = True
            logger.info("Twilio integration initialized")
        else:
            self.client = None
            self.enabled = False
            logger.warning("Twilio credentials not found - using mock mode")
    
    async def send_sms(self, to: str, message: str) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        if not self.enabled:
            return await self._mock_sms(to, message)
        
        try:
            # Validate phone number format
            if not to.startswith('+'):
                to = f"+1{to.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')}"
            
            # Send SMS
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=to
            )
            
            logger.info(f"SMS sent successfully: {message_obj.sid}")
            
            return {
                "message_id": message_obj.sid,
                "to": to,
                "status": message_obj.status,
                "timestamp": datetime.now().isoformat(),
                "provider": "twilio"
            }
        
        except TwilioRestException as e:
            logger.error(f"Twilio API error: {e.msg}")
            raise Exception(f"SMS sending failed: {e.msg}")
        
        except Exception as e:
            logger.error(f"SMS sending error: {str(e)}")
            raise Exception(f"SMS sending failed: {str(e)}")
    
    async def _mock_sms(self, to: str, message: str) -> Dict[str, Any]:
        """Mock SMS for testing without credentials"""
        logger.info(f"MOCK SMS to {to}: {message}")
        await asyncio.sleep(0.1)  # Simulate API delay
        
        return {
            "message_id": f"mock_sms_{int(datetime.now().timestamp())}",
            "to": to,
            "status": "sent",
            "timestamp": datetime.now().isoformat(),
            "provider": "twilio_mock"
        }


class SendGridIntegration:
    """SendGrid email integration (mock for now)"""
    
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@servicehero.com")
        
        if self.api_key:
            self.enabled = True
            logger.info("SendGrid integration initialized")
        else:
            self.enabled = False
            logger.warning("SendGrid credentials not found - using mock mode")
    
    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email via SendGrid"""
        logger.info(f"MOCK EMAIL to {to}: {subject}")
        await asyncio.sleep(0.2)  # Simulate API delay
        
        return {
            "message_id": f"mock_email_{int(datetime.now().timestamp())}",
            "to": to,
            "subject": subject,
            "status": "sent",
            "timestamp": datetime.now().isoformat(),
            "provider": "sendgrid_mock"
        }


class CalendlyIntegration:
    """Calendly scheduling integration (mock for now)"""
    
    def __init__(self):
        self.api_key = os.getenv("CALENDLY_API_KEY")
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            logger.info("Calendly integration initialized")
        else:
            logger.warning("Calendly credentials not found - using mock mode")
    
    async def create_appointment(self, **params) -> Dict[str, Any]:
        """Create appointment in Calendly"""
        logger.info(f"MOCK APPOINTMENT creation: {params}")
        await asyncio.sleep(0.3)
        
        return {
            "appointment_id": f"mock_appt_{int(datetime.now().timestamp())}",
            "status": "scheduled",
            "timestamp": datetime.now().isoformat(),
            "provider": "calendly_mock"
        }


# Initialize integrations
twilio_integration = TwilioIntegration()
sendgrid_integration = SendGridIntegration()
calendly_integration = CalendlyIntegration()


# Integration handlers for workflow engine
async def twilio_handler(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Twilio integration handler"""
    if action == "send_sms":
        return await twilio_integration.send_sms(
            to=params.get("to"),
            message=params.get("message")
        )
    else:
        raise ValueError(f"Unknown Twilio action: {action}")


async def sendgrid_handler(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """SendGrid integration handler"""
    if action == "send_email":
        return await sendgrid_integration.send_email(
            to=params.get("to"),
            subject=params.get("subject"),
            body=params.get("body")
        )
    else:
        raise ValueError(f"Unknown SendGrid action: {action}")


async def calendly_handler(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Calendly integration handler"""
    if action == "create_appointment":
        return await calendly_integration.create_appointment(**params)
    else:
        raise ValueError(f"Unknown Calendly action: {action}")


# Export handlers for workflow engine registration
INTEGRATION_HANDLERS = {
    "twilio": twilio_handler,
    "sendgrid": sendgrid_handler,
    "calendly": calendly_handler
}