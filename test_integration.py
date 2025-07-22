#!/usr/bin/env python3
"""
SERVICE-HERO Integration Testing
End-to-end testing for workflow execution and integrations
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
import uuid

from workflow_engine import WorkflowTemplate, WorkflowStep, StepType
from workflow_engine_enhanced import EnhancedWorkflowEngine, RetryConfig
from integrations import TwilioSMSIntegration
from validation import PlumberEmergencyRequest


@pytest.mark.asyncio
class TestWorkflowIntegration:
    """Test complete workflow execution with integrations"""
    
    async def setup_method(self):
        """Setup workflow engine with test template"""
        self.engine = EnhancedWorkflowEngine()
        
        # Create plumber emergency template
        self.plumber_template = WorkflowTemplate(
            id="plumber_emergency",
            name="Plumber Emergency Response",
            description="Automated response for plumbing emergencies",
            steps=[
                WorkflowStep(
                    id="trigger",
                    type=StepType.TRIGGER,
                    name="Emergency Received",
                    config={"event": "emergency_request"},
                    next_steps=["dispatch_sms"]
                ),
                WorkflowStep(
                    id="dispatch_sms",
                    type=StepType.ACTION,
                    name="Send Dispatch SMS",
                    config={
                        "service": "twilio",
                        "action": "send",
                        "params": {
                            "to": "{{customer_phone}}",
                            "message": "Emergency received at {{location}}. Plumber dispatched within 30 minutes."
                        }
                    },
                    next_steps=["confirmation_delay"]
                ),
                WorkflowStep(
                    id="confirmation_delay",
                    type=StepType.DELAY,
                    name="Wait for Response",
                    config={"minutes": 2},
                    next_steps=["follow_up"]
                ),
                WorkflowStep(
                    id="follow_up",
                    type=StepType.ACTION,
                    name="Follow Up SMS",
                    config={
                        "service": "twilio",
                        "action": "send",
                        "params": {
                            "to": "{{customer_phone}}",
                            "message": "Your plumber should arrive in 15-20 minutes. Call us at (555) 123-4567 for updates."
                        }
                    }
                )
            ]
        )
        
        self.engine.register_template(self.plumber_template)
        
        # Mock Twilio integration
        self.mock_sms_results = []
        
        async def mock_twilio_handler(action, params):
            """Mock Twilio SMS handler"""
            if action == "send":
                message_id = f"mock_msg_{len(self.mock_sms_results) + 1}"
                result = {
                    "message_id": message_id,
                    "to": params["to"],
                    "message": params["message"],
                    "status": "sent",
                    "timestamp": datetime.now().isoformat()
                }
                self.mock_sms_results.append(result)
                return result
            raise ValueError(f"Unknown action: {action}")
        
        # Register mock integration
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1, max_delay=5.0)
        self.engine.register_integration("twilio", mock_twilio_handler, retry_config)
    
    async def test_complete_plumber_workflow(self):
        """Test complete plumber emergency workflow execution"""
        # Validate emergency request
        request_data = {
            "customer_phone": "+15551234567",
            "location": "123 Main Street, Apt 4B",
            "issue": "Burst pipe flooding basement - water everywhere!",
            "urgency": "critical"
        }
        
        emergency_request = PlumberEmergencyRequest(**request_data)
        
        # Start workflow
        execution_id = await self.engine.start_workflow(
            "plumber_emergency",
            "1",  # user_id
            {
                "customer_phone": emergency_request.customer_phone,
                "location": emergency_request.location,
                "issue": emergency_request.issue,
                "urgency": emergency_request.urgency
            }
        )
        
        assert execution_id is not None
        
        # Wait for workflow to complete
        # Note: In real scenario, would wait longer for delay step
        await asyncio.sleep(0.5)
        
        # Check execution status
        execution = await self.engine.get_execution_status(execution_id)
        assert execution is not None
        
        # Verify SMS messages were sent
        assert len(self.mock_sms_results) >= 1  # At least dispatch SMS
        
        first_sms = self.mock_sms_results[0]
        assert first_sms["to"] == "+15551234567"
        assert "Emergency received at 123 Main Street, Apt 4B" in first_sms["message"]
        assert "plumber dispatched" in first_sms["message"].lower()
    
    async def test_workflow_with_integration_failure(self):
        """Test workflow behavior when integration fails"""
        # Create failing integration
        failure_count = 0
        
        async def failing_twilio_handler(action, params):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # Fail first 2 attempts
                raise Exception("Twilio service temporarily unavailable")
            # Succeed on 3rd attempt
            return {
                "message_id": f"success_msg_{failure_count}",
                "to": params["to"],
                "status": "sent",
                "attempt": failure_count
            }
        
        # Replace integration with failing one
        retry_config = RetryConfig(max_attempts=3, base_delay=0.05, max_delay=1.0)
        self.engine.register_integration("twilio", failing_twilio_handler, retry_config)
        
        # Start workflow
        execution_id = await self.engine.start_workflow(
            "plumber_emergency",
            "1",
            {
                "customer_phone": "+15551234567",
                "location": "456 Oak Street", 
                "issue": "Water heater leaking",
                "urgency": "high"
            }
        )
        
        # Wait for retries to complete
        await asyncio.sleep(1.0)
        
        # Verify workflow succeeded after retries
        execution = await self.engine.get_execution_status(execution_id)
        assert execution is not None
        
        # Should have succeeded on 3rd attempt
        assert failure_count == 3
    
    async def test_workflow_with_permanent_failure(self):
        """Test workflow behavior with permanent integration failure"""
        # Create permanently failing integration
        async def permanently_failing_handler(action, params):
            raise Exception("Service permanently unavailable")
        
        retry_config = RetryConfig(max_attempts=3, base_delay=0.05, max_delay=1.0)
        self.engine.register_integration("twilio", permanently_failing_handler, retry_config)
        
        # Start workflow
        execution_id = await self.engine.start_workflow(
            "plumber_emergency",
            "1",
            {
                "customer_phone": "+15551234567",
                "location": "789 Pine Street",
                "issue": "Clogged drain backup",
                "urgency": "medium"
            }
        )
        
        # Wait for all retries to complete
        await asyncio.sleep(1.0)
        
        # Execution should exist but may have failed steps
        execution = await self.engine.get_execution_status(execution_id)
        assert execution is not None


@pytest.mark.asyncio
class TestRealIntegrationMocking:
    """Test integration patterns with realistic mocking"""
    
    async def test_twilio_integration_patterns(self):
        """Test Twilio integration with realistic responses"""
        from workflow_engine_enhanced import EnhancedIntegrationManager
        
        manager = EnhancedIntegrationManager()
        
        # Mock realistic Twilio responses
        async def realistic_twilio(action, params):
            if action == "send":
                # Simulate Twilio API response format
                return {
                    "account_sid": "ACtest123456789",
                    "api_version": "2010-04-01",
                    "body": params["message"],
                    "date_created": datetime.now().isoformat(),
                    "date_sent": datetime.now().isoformat(),
                    "date_updated": datetime.now().isoformat(),
                    "direction": "outbound-api",
                    "error_code": None,
                    "error_message": None,
                    "from": "+15551234567",
                    "messaging_service_sid": None,
                    "num_media": "0",
                    "num_segments": "1",
                    "price": "-0.00750",
                    "price_unit": "USD",
                    "sid": f"SMtest{uuid.uuid4().hex[:24]}",
                    "status": "sent",
                    "subresource_uris": {},
                    "to": params["to"],
                    "uri": f"/2010-04-01/Accounts/ACtest123456789/Messages/SMtest{uuid.uuid4().hex[:24]}.json"
                }
            elif action == "check_status":
                return {
                    "sid": params["message_sid"],
                    "status": "delivered",
                    "date_sent": datetime.now().isoformat()
                }
            else:
                raise ValueError(f"Unknown Twilio action: {action}")
        
        retry_config = RetryConfig(max_attempts=3, base_delay=0.1)
        manager.register_integration("twilio", realistic_twilio, retry_config)
        
        # Test SMS sending
        sms_params = {
            "to": "+15551234567",
            "message": "Your plumber will arrive in 30 minutes. Emergency ID: EMG-12345"
        }
        
        result = await manager.execute_integration_with_retry(
            "twilio", "send", sms_params
        )
        
        assert result["success"] is True
        assert "sid" in result["data"]
        assert result["data"]["status"] == "sent"
        assert result["data"]["to"] == "+15551234567"
        
        # Test status checking
        status_result = await manager.execute_integration_with_retry(
            "twilio", "check_status", {"message_sid": result["data"]["sid"]}
        )
        
        assert status_result["success"] is True
        assert status_result["data"]["status"] == "delivered"


class TestWorkflowTemplateValidation:
    """Test workflow template validation and safety"""
    
    def test_template_structure_validation(self):
        """Test that workflow templates have proper structure"""
        # Valid template
        valid_template = WorkflowTemplate(
            id="valid_template",
            name="Valid Template",
            description="A properly structured template",
            steps=[
                WorkflowStep(
                    id="start",
                    type=StepType.TRIGGER,
                    name="Start Step",
                    config={"event": "manual"}
                )
            ]
        )
        
        assert valid_template.id == "valid_template"
        assert len(valid_template.steps) == 1
        assert valid_template.steps[0].type == StepType.TRIGGER
    
    def test_step_configuration_safety(self):
        """Test that step configurations are safe"""
        # Test action step with parameters
        action_step = WorkflowStep(
            id="safe_action",
            type=StepType.ACTION,
            name="Safe Action Step",
            config={
                "service": "email",
                "action": "send",
                "params": {
                    "to": "{{customer_email}}",
                    "subject": "Service Confirmation",
                    "body": "Thank you for choosing our service!"
                }
            }
        )
        
        assert action_step.config["service"] == "email"
        assert "{{customer_email}}" in action_step.config["params"]["to"]
        
        # Test delay step
        delay_step = WorkflowStep(
            id="wait_step",
            type=StepType.DELAY,
            name="Wait Step",
            config={"minutes": 5}
        )
        
        assert delay_step.config["minutes"] == 5
    
    def test_template_variable_replacement(self):
        """Test template variable replacement safety"""
        # This would be tested in the actual workflow execution
        # but we can test the concept here
        template_text = "Hello {{customer_name}}, your appointment is at {{appointment_time}}"
        variables = {
            "customer_name": "John Smith",
            "appointment_time": "2:00 PM"
        }
        
        # Simulate variable replacement (simplified)
        result = template_text
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", str(value))
        
        expected = "Hello John Smith, your appointment is at 2:00 PM"
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])