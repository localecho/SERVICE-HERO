#!/usr/bin/env python3
"""
SERVICE-HERO Unit Testing Suite
Comprehensive testing for all components
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime, timedelta
import uuid

from validation import PhoneNumber, TextSanitizer, PlumberEmergencyRequest
from auth import AuthManager
from database import DatabaseManager, UserRecord, ExecutionRecord
from workflow_engine_enhanced import EnhancedWorkflowEngine, RetryConfig, CircuitBreaker


class TestPhoneValidation:
    """Test phone number validation"""
    
    def test_valid_phone_numbers(self):
        """Test valid phone formats are accepted"""
        valid_phones = [
            "+1234567890",
            "(123) 456-7890",
            "123-456-7890",
            "1234567890"
        ]
        
        for phone in valid_phones:
            assert PhoneNumber.validate(phone)
            cleaned = PhoneNumber.clean(phone)
            assert cleaned.startswith("+")
    
    def test_invalid_phone_numbers(self):
        """Test invalid phone formats are rejected"""
        invalid_phones = [
            "",
            "123",
            "abcdefghij",
            "12345678901234567890"
        ]
        
        for phone in invalid_phones:
            assert not PhoneNumber.validate(phone)


class TestTextSecurity:
    """Test text sanitization and XSS prevention"""
    
    def test_safe_text_passes(self):
        """Test that normal text passes validation"""
        safe_texts = [
            "Normal business description",
            "123 Main Street Address",
            "Plumbing emergency description",
            "Customer name and details"
        ]
        
        for text in safe_texts:
            assert TextSanitizer.is_safe(text)
    
    def test_dangerous_text_blocked(self):
        """Test that dangerous patterns are blocked"""
        dangerous_texts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<iframe src='malicious.com'></iframe>",
            "<img onerror='hack()' src=x>",
            "<div onclick='steal()'>text</div>"
        ]
        
        for text in dangerous_texts:
            assert not TextSanitizer.is_safe(text)
    
    def test_text_sanitization(self):
        """Test text cleaning functionality"""
        dangerous_text = "Normal text with dangerous chars <>''"
        cleaned = TextSanitizer.sanitize(dangerous_text)
        
        assert "Normal text" in cleaned
        assert "<" not in cleaned
        assert ">" not in cleaned
        assert "'" not in cleaned


class TestRequestValidation:
    """Test Pydantic request validation"""
    
    def test_valid_plumber_request(self):
        """Test valid plumber emergency request"""
        valid_data = {
            "customer_phone": "+1234567890",
            "location": "123 Main Street",
            "issue": "Burst pipe in basement",
            "urgency": "high"
        }
        
        request = PlumberEmergencyRequest(**valid_data)
        assert request.urgency == "high"
        assert request.customer_phone.startswith("+")
    
    def test_invalid_urgency_rejected(self):
        """Test that invalid urgency levels are rejected"""
        invalid_data = {
            "customer_phone": "+1234567890",
            "location": "123 Main Street",
            "issue": "Minor problem",
            "urgency": "extreme"
        }
        
        with pytest.raises(ValueError):
            PlumberEmergencyRequest(**invalid_data)


class TestAuthentication:
    """Test authentication system"""
    
    def setup_method(self):
        """Setup authentication manager for testing"""
        self.auth = AuthManager()
    
    def test_password_hashing(self):
        """Test password hashing with bcrypt"""
        password = "test_password_123"
        hashed = self.auth.hash_password(password)
        
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60
        assert self.auth.verify_password(password, hashed)
        assert not self.auth.verify_password("wrong_password", hashed)
    
    def test_jwt_token_creation(self):
        """Test JWT token generation"""
        email = "test@example.com"
        token = self.auth.create_access_token(email)
        
        assert isinstance(token, str)
        assert len(token.split('.')) == 3
    
    def test_token_expiration(self):
        """Test JWT token expiration handling"""
        email = "test@example.com"
        
        # Create already expired token
        expired_delta = timedelta(seconds=-1)
        token = self.auth.create_access_token(email, expired_delta)
        
        # Should return None for expired token
        user = self.auth.verify_token(token)
        assert user is None


@pytest.mark.asyncio
class TestDatabaseOperations:
    """Test database operations"""
    
    async def setup_method(self):
        """Setup in-memory database for testing"""
        self.db = DatabaseManager()
        self.db.db_path = ":memory:"
        await self.db.initialize()
    
    async def teardown_method(self):
        """Cleanup database after test"""
        await self.db.close()
    
    async def test_user_creation(self):
        """Test user creation and retrieval"""
        user_data = UserRecord(
            email="test@example.com",
            password_hash="hashed_password",
            business_name="Test Business",
            business_type="plumbing"
        )
        
        user_id = await self.db.create_user(user_data)
        assert user_id > 0
        
        retrieved_user = await self.db.get_user_by_id(user_id)
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.business_type == "plumbing"
    
    async def test_execution_creation(self):
        """Test workflow execution creation"""
        execution_data = ExecutionRecord(
            id=str(uuid.uuid4()),
            workflow_id=1,
            user_id=1,
            status="pending",
            trigger_data={"customer": "John Doe", "issue": "Leak"},
            step_results=[],
            started_at=datetime.now()
        )
        
        execution_id = await self.db.create_execution(execution_data)
        assert execution_id == execution_data.id
        
        retrieved = await self.db.get_execution(execution_id)
        assert retrieved.status == "pending"
        assert retrieved.trigger_data["customer"] == "John Doe"


@pytest.mark.asyncio
class TestWorkflowEngine:
    """Test workflow engine functionality"""
    
    async def setup_method(self):
        """Setup workflow engine for testing"""
        self.engine = EnhancedWorkflowEngine()
    
    async def test_template_registration(self):
        """Test workflow template registration"""
        from workflow_engine import WorkflowTemplate, WorkflowStep, StepType
        
        template = WorkflowTemplate(
            id="test_template",
            name="Test Template",
            description="Test workflow template",
            steps=[
                WorkflowStep(
                    id="trigger_step",
                    type=StepType.TRIGGER,
                    name="Test Trigger",
                    config={"event": "manual"}
                )
            ]
        )
        
        self.engine.register_template(template)
        assert "test_template" in self.engine.templates
        
        retrieved = self.engine.get_template("test_template")
        assert retrieved.name == "Test Template"
    
    async def test_workflow_execution(self):
        """Test workflow execution"""
        from workflow_engine import WorkflowTemplate, WorkflowStep, StepType
        
        # Register template first
        template = WorkflowTemplate(
            id="execution_test",
            name="Execution Test",
            description="Template for execution testing",
            steps=[
                WorkflowStep(
                    id="trigger",
                    type=StepType.TRIGGER,
                    name="Trigger",
                    config={"event": "manual"}
                )
            ]
        )
        self.engine.register_template(template)
        
        # Start workflow execution
        trigger_data = {"customer": "Test Customer", "issue": "Test Issue"}
        execution_id = await self.engine.start_workflow(
            "execution_test", "1", trigger_data
        )
        
        assert execution_id is not None
        
        # Give execution time to start
        await asyncio.sleep(0.1)
        
        # Check execution status
        execution = await self.engine.get_execution_status(execution_id)
        assert execution is not None


class TestCircuitBreaker:
    """Test circuit breaker pattern"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after failures"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Function that always fails
        async def failing_function():
            raise Exception("Service failure")
        
        # First few failures should be allowed
        for i in range(2):
            try:
                await breaker.call(failing_function)
            except Exception:
                pass
        
        # Circuit should now be open
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await breaker.call(failing_function)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success_reset(self):
        """Test circuit breaker resets on success"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        # Successful function
        async def success_function():
            return "success"
        
        result = await breaker.call(success_function)
        assert result == "success"
        assert breaker.failure_count == 0


class TestRetryLogic:
    """Test retry configuration and logic"""
    
    def test_retry_config_creation(self):
        """Test retry configuration object"""
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.jitter is True
    
    @pytest.mark.asyncio
    async def test_integration_retry(self):
        """Test integration manager retry logic"""
        from workflow_engine_enhanced import EnhancedIntegrationManager
        
        manager = EnhancedIntegrationManager()
        
        # Mock handler that succeeds on second attempt
        attempt_count = 0
        async def mock_handler(action, params):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise Exception("First attempt fails")
            return {"status": "success", "data": "test_data"}
        
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        manager.register_integration("test_service", mock_handler, config)
        
        result = await manager.execute_integration_with_retry(
            "test_service", "test_action", {}
        )
        
        assert result["success"] is True
        assert result["data"]["status"] == "success"
        assert attempt_count == 2


class TestSecurityConfiguration:
    """Test security configuration and settings"""
    
    def test_secret_key_present(self):
        """Test that secret key is configured"""
        from auth import SECRET_KEY
        
        assert SECRET_KEY is not None
        assert len(SECRET_KEY) >= 16
    
    def test_database_config_safe(self):
        """Test database configuration safety"""
        from database import DatabaseConfig
        
        config = DatabaseConfig("test_database.db")
        assert config.db_path == "test_database.db"
        assert config.connection_pool_size == 10


class TestIntegrationSafety:
    """Test integration handler safety"""
    
    @pytest.mark.asyncio
    async def test_safe_integration_execution(self):
        """Test that integrations execute safely"""
        from workflow_engine_enhanced import EnhancedIntegrationManager
        
        manager = EnhancedIntegrationManager()
        
        # Mock safe handler
        async def safe_handler(action, params):
            if action == "send_sms":
                return {"message_id": "test_123", "status": "sent"}
            return {"status": "unknown_action"}
        
        manager.register_integration("safe_service", safe_handler)
        
        result = await manager.execute_integration_with_retry(
            "safe_service", "send_sms", {"phone": "+1234567890", "message": "Test"}
        )
        
        assert result["success"] is True
        assert result["data"]["status"] == "sent"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])