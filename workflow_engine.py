#!/usr/bin/env python3
"""
SERVICE-HERO Workflow Execution Engine
Core automation processor for template-based workflows
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from pydantic import BaseModel
import uuid


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Workflow step types"""
    TRIGGER = "trigger"
    ACTION = "action"
    DELAY = "delay"
    CONDITION = "condition"
    WEBHOOK = "webhook"


class ExecutionStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class WorkflowStep(BaseModel):
    """Individual workflow step definition"""
    id: str
    type: StepType
    name: str
    description: Optional[str] = None
    config: Dict[str, Any] = {}
    next_steps: List[str] = []
    conditions: Dict[str, Any] = {}


class WorkflowTemplate(BaseModel):
    """Automation template structure"""
    id: str
    name: str
    description: str
    business_type: str
    category: str
    steps: List[WorkflowStep]
    required_integrations: List[str] = []
    estimated_execution_time: int = 0  # seconds


class WorkflowExecution(BaseModel):
    """Runtime workflow execution instance"""
    id: str
    template_id: str
    user_id: str
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step_id: Optional[str] = None
    context: Dict[str, Any] = {}
    step_results: List[Dict[str, Any]] = []
    error_message: Optional[str] = None


class StepResult(BaseModel):
    """Result of a single step execution"""
    step_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    output: Dict[str, Any] = {}
    error: Optional[str] = None
    retry_count: int = 0


class IntegrationManager:
    """Manages external service integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, Any] = {}
        self.handlers: Dict[str, Callable] = {}
    
    def register_integration(self, service_name: str, handler: Callable):
        """Register an integration handler"""
        self.handlers[service_name] = handler
        self.integrations[service_name] = {
            "status": "connected",
            "last_used": None,
            "success_count": 0,
            "error_count": 0
        }
        logger.info(f"Registered integration: {service_name}")
    
    async def execute_integration(self, service_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an integration action"""
        if service_name not in self.handlers:
            raise ValueError(f"Integration {service_name} not registered")
        
        try:
            handler = self.handlers[service_name]
            result = await handler(action, params)
            
            # Update integration stats
            self.integrations[service_name]["last_used"] = datetime.now()
            self.integrations[service_name]["success_count"] += 1
            
            return {"success": True, "data": result}
        
        except Exception as e:
            self.integrations[service_name]["error_count"] += 1
            logger.error(f"Integration {service_name} failed: {str(e)}")
            return {"success": False, "error": str(e)}


class WorkflowEngine:
    """Core workflow execution engine"""
    
    def __init__(self):
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.integration_manager = IntegrationManager()
        self.running = False
    
    def register_template(self, template: WorkflowTemplate):
        """Register a workflow template"""
        self.templates[template.id] = template
        logger.info(f"Registered template: {template.name} ({template.id})")
    
    def register_integration(self, service_name: str, handler: Callable):
        """Register an external service integration"""
        self.integration_manager.register_integration(service_name, handler)
    
    async def start_workflow(self, template_id: str, user_id: str, trigger_data: Dict[str, Any]) -> str:
        """Start a new workflow execution"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        execution_id = str(uuid.uuid4())
        
        execution = WorkflowExecution(
            id=execution_id,
            template_id=template_id,
            user_id=user_id,
            status=ExecutionStatus.PENDING,
            context={"trigger_data": trigger_data}
        )
        
        self.executions[execution_id] = execution
        
        # Start execution in background
        asyncio.create_task(self._execute_workflow(execution))
        
        logger.info(f"Started workflow {template.name} (execution_id: {execution_id})")
        return execution_id
    
    async def _execute_workflow(self, execution: WorkflowExecution):
        """Execute workflow steps sequentially"""
        template = self.templates[execution.template_id]
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now()
        
        try:
            # Find first step (usually trigger)
            current_step = template.steps[0]
            
            while current_step:
                execution.current_step_id = current_step.id
                
                # Execute current step
                step_result = await self._execute_step(current_step, execution)
                execution.step_results.append(step_result.model_dump())
                
                # Check if step failed
                if step_result.status == "failed":
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = step_result.error
                    break
                
                # Determine next step
                current_step = self._get_next_step(current_step, step_result, template)
            
            # Mark as completed if no failures
            if execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.COMPLETED
        
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Workflow execution failed: {str(e)}")
        
        finally:
            execution.completed_at = datetime.now()
            execution.current_step_id = None
    
    async def _execute_step(self, step: WorkflowStep, execution: WorkflowExecution) -> StepResult:
        """Execute a single workflow step"""
        result = StepResult(
            step_id=step.id,
            status="running",
            started_at=datetime.now()
        )
        
        try:
            if step.type == StepType.TRIGGER:
                result.output = await self._handle_trigger(step, execution)
            
            elif step.type == StepType.ACTION:
                result.output = await self._handle_action(step, execution)
            
            elif step.type == StepType.DELAY:
                result.output = await self._handle_delay(step, execution)
            
            elif step.type == StepType.CONDITION:
                result.output = await self._handle_condition(step, execution)
            
            elif step.type == StepType.WEBHOOK:
                result.output = await self._handle_webhook(step, execution)
            
            else:
                raise ValueError(f"Unknown step type: {step.type}")
            
            result.status = "completed"
            result.completed_at = datetime.now()
        
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.completed_at = datetime.now()
            logger.error(f"Step {step.id} failed: {str(e)}")
        
        return result
    
    async def _handle_trigger(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Handle trigger step"""
        trigger_event = step.config.get("event", "manual")
        trigger_data = execution.context.get("trigger_data", {})
        
        logger.info(f"Processing trigger: {trigger_event}")
        
        return {
            "event": trigger_event,
            "data": trigger_data,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_action(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Handle action step (integration call)"""
        service = step.config.get("service")
        action = step.config.get("action", "send")
        params = step.config.get("params", {})
        
        # Replace template variables in params
        params = self._replace_variables(params, execution.context)
        
        if not service:
            raise ValueError("Action step must specify a service")
        
        logger.info(f"Executing action: {service}.{action}")
        
        result = await self.integration_manager.execute_integration(service, action, params)
        
        if not result["success"]:
            raise Exception(f"Action failed: {result['error']}")
        
        return result["data"]
    
    async def _handle_delay(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Handle delay step"""
        delay_seconds = step.config.get("seconds", 0)
        delay_minutes = step.config.get("minutes", 0)
        delay_hours = step.config.get("hours", 0)
        
        total_seconds = delay_seconds + (delay_minutes * 60) + (delay_hours * 3600)
        
        if total_seconds > 0:
            logger.info(f"Delaying execution for {total_seconds} seconds")
            await asyncio.sleep(total_seconds)
        
        return {
            "delay_seconds": total_seconds,
            "delayed_until": (datetime.now() + timedelta(seconds=total_seconds)).isoformat()
        }
    
    async def _handle_condition(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Handle condition step"""
        condition = step.config.get("condition", "true")
        context = execution.context
        
        # Evaluate basic conditions
        if condition == "true":
            result = True
        elif condition == "false":
            result = False
        elif ">" in condition:
            # Simple numeric comparison
            parts = condition.split(">")
            left = float(self._resolve_value(parts[0].strip(), context))
            right = float(parts[1].strip())
            result = left > right
        else:
            result = True
        
        logger.info(f"Condition '{condition}' evaluated to: {result}")
        
        return {
            "condition": condition,
            "result": result,
            "evaluation_time": datetime.now().isoformat()
        }
    
    async def _handle_webhook(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Handle webhook step"""
        url = step.config.get("url")
        method = step.config.get("method", "POST")
        payload = step.config.get("payload", {})
        
        # Replace variables in payload
        payload = self._replace_variables(payload, execution.context)
        
        logger.info(f"Webhook call: {method} {url}")
        
        return {
            "url": url,
            "method": method,
            "payload": payload,
            "status_code": 200,
            "response": {"success": True}
        }
    
    def _get_next_step(self, current_step: WorkflowStep, step_result: StepResult, 
                      template: WorkflowTemplate) -> Optional[WorkflowStep]:
        """Determine the next step to execute"""
        if current_step.next_steps:
            next_step_id = current_step.next_steps[0]
            return next((s for s in template.steps if s.id == next_step_id), None)
        
        current_index = next((i for i, s in enumerate(template.steps) if s.id == current_step.id), -1)
        if current_index >= 0 and current_index < len(template.steps) - 1:
            return template.steps[current_index + 1]
        
        return None
    
    def _replace_variables(self, data: Any, context: Dict[str, Any]) -> Any:
        """Replace template variables in data"""
        if isinstance(data, dict):
            return {k: self._replace_variables(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables(item, context) for item in data]
        elif isinstance(data, str) and data.startswith("{{") and data.endswith("}}"):
            variable_name = data[2:-2].strip()
            return self._resolve_value(variable_name, context)
        else:
            return data
    
    def _resolve_value(self, variable_name: str, context: Dict[str, Any]) -> Any:
        """Resolve variable from context"""
        parts = variable_name.split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return variable_name
        
        return value
    
    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get current execution status"""
        return self.executions.get(execution_id)
    
    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[WorkflowTemplate]:
        """List all registered templates"""
        return list(self.templates.values())
    
    def list_executions(self, user_id: Optional[str] = None) -> List[WorkflowExecution]:
        """List executions, optionally filtered by user"""
        executions = list(self.executions.values())
        if user_id:
            executions = [e for e in executions if e.user_id == user_id]
        return executions


# Create global workflow engine instance
workflow_engine = WorkflowEngine()


# Mock integration handlers
async def mock_sms_handler(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock SMS integration handler"""
    phone = params.get("to", "unknown")
    message = params.get("message", "")
    
    logger.info(f"Sending SMS to {phone}: {message}")
    await asyncio.sleep(0.1)
    
    return {
        "message_id": f"msg_{uuid.uuid4().hex[:8]}",
        "to": phone,
        "status": "sent",
        "timestamp": datetime.now().isoformat()
    }


async def mock_email_handler(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Mock email integration handler"""
    to = params.get("to", "unknown")
    subject = params.get("subject", "")
    body = params.get("body", "")
    
    logger.info(f"Sending email to {to}: {subject}")
    await asyncio.sleep(0.2)
    
    return {
        "message_id": f"email_{uuid.uuid4().hex[:8]}",
        "to": to,
        "subject": subject,
        "status": "sent",
        "timestamp": datetime.now().isoformat()
    }


# Register mock integrations
workflow_engine.register_integration("twilio", mock_sms_handler)
workflow_engine.register_integration("sendgrid", mock_email_handler)


def create_plumber_emergency_template() -> WorkflowTemplate:
    """Create the plumber emergency response template"""
    return WorkflowTemplate(
        id="plumber_emergency",
        name="Emergency Response Workflow",
        description="Automated emergency dispatch and customer communication",
        business_type="plumbing",
        category="emergency_response",
        required_integrations=["twilio", "sendgrid"],
        estimated_execution_time=300,
        steps=[
            WorkflowStep(
                id="trigger_emergency",
                type=StepType.TRIGGER,
                name="Emergency Call Received",
                description="Customer calls emergency line",
                config={"event": "emergency_call_received"}
            ),
            WorkflowStep(
                id="send_eta_sms",
                type=StepType.ACTION,
                name="Send ETA SMS",
                description="Send estimated arrival time to customer",
                config={
                    "service": "twilio",
                    "action": "send_sms",
                    "params": {
                        "to": "{{trigger_data.customer_phone}}",
                        "message": "Emergency plumber dispatched! ETA: 30 minutes. Service call #{{trigger_data.call_id}}"
                    }
                }
            ),
            WorkflowStep(
                id="notify_dispatch",
                type=StepType.ACTION,
                name="Notify Dispatch Team",
                description="Send emergency details to dispatch team",
                config={
                    "service": "sendgrid",
                    "action": "send_email",
                    "params": {
                        "to": "dispatch@plumbingco.com",
                        "subject": "EMERGENCY: {{trigger_data.issue}}",
                        "body": "Emergency call received:\nLocation: {{trigger_data.location}}\nIssue: {{trigger_data.issue}}\nCustomer: {{trigger_data.customer_phone}}\nUrgency: {{trigger_data.urgency}}"
                    }
                }
            ),
            WorkflowStep(
                id="follow_up_survey",
                type=StepType.ACTION,
                name="Send Follow-up Survey",
                description="Send customer satisfaction survey",
                config={
                    "service": "twilio",
                    "action": "send_sms",
                    "params": {
                        "to": "{{trigger_data.customer_phone}}",
                        "message": "Emergency service complete! Rate your experience: https://survey.link/{{trigger_data.call_id}}"
                    }
                }
            )
        ]
    )


# Register the plumber emergency template
plumber_template = create_plumber_emergency_template()
workflow_engine.register_template(plumber_template)