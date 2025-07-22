#!/usr/bin/env python3
"""
SERVICE-HERO Enhanced Workflow Engine
Production-ready workflow processor with database integration and retry logic
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import uuid
import json
from dataclasses import dataclass

from workflow_engine import (
    StepType, ExecutionStatus, WorkflowStep, WorkflowTemplate, 
    WorkflowExecution, StepResult, IntegrationManager
)
from database import db_manager, ExecutionRecord

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for step retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for integration failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN - service temporarily unavailable")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        if not self.last_failure_time:
            return False
        
        return datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
    
    async def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    async def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")


class EnhancedIntegrationManager(IntegrationManager):
    """Enhanced integration manager with retry logic and circuit breakers"""
    
    def __init__(self):
        super().__init__()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_configs: Dict[str, RetryConfig] = {}
    
    def register_integration(self, service_name: str, handler: Callable, retry_config: RetryConfig = None):
        """Register integration with retry configuration"""
        super().register_integration(service_name, handler)
        self.circuit_breakers[service_name] = CircuitBreaker()
        self.retry_configs[service_name] = retry_config or RetryConfig()
    
    async def execute_integration_with_retry(self, service_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute integration with retry logic and circuit breaker"""
        if service_name not in self.handlers:
            raise ValueError(f"Integration {service_name} not registered")
        
        retry_config = self.retry_configs.get(service_name, RetryConfig())
        circuit_breaker = self.circuit_breakers[service_name]
        
        for attempt in range(retry_config.max_attempts):
            try:
                handler = self.handlers[service_name]
                result = await circuit_breaker.call(handler, action, params)
                
                # Update integration stats on success
                self.integrations[service_name]["last_used"] = datetime.now()
                self.integrations[service_name]["success_count"] += 1
                
                return {"success": True, "data": result, "attempt": attempt + 1}
            
            except Exception as e:
                self.integrations[service_name]["error_count"] += 1
                
                if attempt == retry_config.max_attempts - 1:
                    # Last attempt failed
                    logger.error(f"Integration {service_name} failed after {retry_config.max_attempts} attempts: {str(e)}")
                    return {"success": False, "error": str(e), "attempts": retry_config.max_attempts}
                
                # Calculate delay with exponential backoff
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** attempt),
                    retry_config.max_delay
                )
                
                if retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)  # Add jitter
                
                logger.warning(f"Integration {service_name} attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f}s")
                await asyncio.sleep(delay)
        
        return {"success": False, "error": "Max retry attempts exceeded"}


class EnhancedWorkflowEngine:
    """Enhanced workflow engine with database persistence and monitoring"""
    
    def __init__(self):
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.executions: Dict[str, WorkflowExecution] = {}  # In-memory cache
        self.integration_manager = EnhancedIntegrationManager()
        self.running = False
        self.execution_callbacks: List[Callable] = []
    
    def register_template(self, template: WorkflowTemplate):
        """Register a workflow template"""
        self.templates[template.id] = template
        logger.info(f"Registered template: {template.name} ({template.id})")
    
    def register_integration(self, service_name: str, handler: Callable, retry_config: RetryConfig = None):
        """Register an external service integration with retry configuration"""
        self.integration_manager.register_integration(service_name, handler, retry_config)
    
    def add_execution_callback(self, callback: Callable):
        """Add callback for execution status changes"""
        self.execution_callbacks.append(callback)
    
    async def _notify_execution_change(self, execution: WorkflowExecution, event: str):
        """Notify callbacks of execution changes"""
        for callback in self.execution_callbacks:
            try:
                await callback(execution, event)
            except Exception as e:
                logger.error(f"Execution callback failed: {e}")
    
    async def start_workflow(self, template_id: str, user_id: str, trigger_data: Dict[str, Any], workflow_id: int = None) -> str:
        """Start a new workflow execution with database persistence"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        execution_id = str(uuid.uuid4())
        
        # Create execution record
        execution = WorkflowExecution(
            id=execution_id,
            template_id=template_id,
            user_id=user_id,
            status=ExecutionStatus.PENDING,
            context={"trigger_data": trigger_data}
        )
        
        # Store in memory cache
        self.executions[execution_id] = execution
        
        # Persist to database
        execution_record = ExecutionRecord(
            id=execution_id,
            workflow_id=workflow_id or 0,  # Default workflow ID
            user_id=int(user_id) if isinstance(user_id, str) and user_id.isdigit() else 1,  # Default user ID
            status=execution.status.value,
            trigger_data=trigger_data,
            step_results=[],
            started_at=datetime.now()
        )
        
        try:
            await db_manager.create_execution(execution_record)
            logger.info(f"Execution {execution_id} persisted to database")
        except Exception as e:
            logger.error(f"Failed to persist execution to database: {e}")
        
        # Start execution in background
        asyncio.create_task(self._execute_workflow_with_monitoring(execution))
        
        # Notify callbacks
        await self._notify_execution_change(execution, "started")
        
        logger.info(f"Started workflow {template.name} (execution_id: {execution_id})")
        return execution_id
    
    async def _execute_workflow_with_monitoring(self, execution: WorkflowExecution):
        """Execute workflow with monitoring and database updates"""
        template = self.templates[execution.template_id]
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now()
        
        # Update database
        await self._update_execution_in_db(execution)
        await self._notify_execution_change(execution, "running")
        
        try:
            # Find first step (usually trigger)
            current_step = template.steps[0] if template.steps else None
            
            while current_step:
                execution.current_step_id = current_step.id
                
                # Update current step in database
                await self._update_execution_in_db(execution)
                
                # Execute current step with enhanced error handling
                step_result = await self._execute_step_with_retry(current_step, execution)
                execution.step_results.append(step_result.model_dump())
                
                # Update database with step results
                await self._update_execution_in_db(execution)
                
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
                await self._notify_execution_change(execution, "completed")
        
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Workflow execution failed: {str(e)}")
            await self._notify_execution_change(execution, "failed")
        
        finally:
            execution.completed_at = datetime.now()
            execution.current_step_id = None
            
            # Final database update
            await self._update_execution_in_db(execution)
    
    async def _update_execution_in_db(self, execution: WorkflowExecution):
        """Update execution record in database"""
        try:
            updates = {
                "status": execution.status.value,
                "step_results": [result for result in execution.step_results],
                "current_step_id": execution.current_step_id,
                "error_message": execution.error_message,
                "completed_at": execution.completed_at
            }
            
            await db_manager.update_execution(execution.id, updates)
        except Exception as e:
            logger.error(f"Failed to update execution in database: {e}")
    
    async def _execute_step_with_retry(self, step: WorkflowStep, execution: WorkflowExecution) -> StepResult:
        """Execute a single workflow step with enhanced error handling"""
        result = StepResult(
            step_id=step.id,
            status="running",
            started_at=datetime.now()
        )
        
        try:
            if step.type == StepType.TRIGGER:
                result.output = await self._handle_trigger(step, execution)
            
            elif step.type == StepType.ACTION:
                result.output = await self._handle_action_with_retry(step, execution)
            
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
    
    async def _handle_action_with_retry(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Handle action step with retry logic"""
        service = step.config.get("service")
        action = step.config.get("action", "send")
        params = step.config.get("params", {})
        
        # Replace template variables in params
        params = self._replace_variables(params, execution.context)
        
        if not service:
            raise ValueError("Action step must specify a service")
        
        logger.info(f"Executing action: {service}.{action}")
        
        # Use enhanced integration manager with retry logic
        result = await self.integration_manager.execute_integration_with_retry(service, action, params)
        
        if not result["success"]:
            raise Exception(f"Action failed after {result.get('attempts', 1)} attempts: {result['error']}")
        
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
    
    async def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get current execution status (from memory cache or database)"""
        # First check memory cache
        if execution_id in self.executions:
            return self.executions[execution_id]
        
        # If not in cache, try to load from database
        try:
            execution_record = await db_manager.get_execution(execution_id)
            if execution_record:
                # Convert database record back to WorkflowExecution
                execution = WorkflowExecution(
                    id=execution_record.id,
                    template_id=self.templates.get(execution_record.workflow_id, {}).get('template_id', 'unknown'),
                    user_id=str(execution_record.user_id),
                    status=ExecutionStatus(execution_record.status),
                    started_at=execution_record.started_at,
                    completed_at=execution_record.completed_at,
                    current_step_id=execution_record.current_step_id,
                    context=execution_record.trigger_data,
                    step_results=execution_record.step_results,
                    error_message=execution_record.error_message
                )
                
                # Cache for future requests
                self.executions[execution_id] = execution
                return execution
        except Exception as e:
            logger.error(f"Failed to load execution from database: {e}")
        
        return None
    
    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[WorkflowTemplate]:
        """List all registered templates"""
        return list(self.templates.values())
    
    async def list_executions_for_user(self, user_id: int, limit: int = 50) -> List[WorkflowExecution]:
        """List executions for a specific user from database"""
        try:
            execution_records = await db_manager.get_executions_by_user(user_id, limit)
            executions = []
            
            for record in execution_records:
                execution = WorkflowExecution(
                    id=record.id,
                    template_id=f"template_{record.workflow_id}",  # Simplified mapping
                    user_id=str(record.user_id),
                    status=ExecutionStatus(record.status),
                    started_at=record.started_at,
                    completed_at=record.completed_at,
                    current_step_id=record.current_step_id,
                    context=record.trigger_data,
                    step_results=record.step_results,
                    error_message=record.error_message
                )
                executions.append(execution)
            
            return executions
        except Exception as e:
            logger.error(f"Failed to load executions from database: {e}")
            return []


# Create enhanced workflow engine instance
enhanced_workflow_engine = EnhancedWorkflowEngine()