# Service Hero Developer Guide

## 🚀 Welcome to Service Hero Development

This guide will get you up and running as a Service Hero developer in under 15 minutes. Whether you're contributing to core features, building integrations, or creating custom templates, this is your comprehensive starting point.

---

## 📋 Prerequisites

### System Requirements
- **Python 3.8+** (recommended: 3.11)
- **Git** version control
- **Docker** and Docker Compose (for local development)
- **Code Editor** (VS Code recommended with Python extensions)

### Recommended Tools
- **Postman** or **HTTPie** for API testing
- **pgAdmin** or **DBeaver** for database management
- **Redis Desktop Manager** for cache inspection

---

## ⚡ Quick Start (5 Minutes)

### 1. Clone and Setup
```bash
# Clone repository
git clone https://github.com/localecho/SERVICE-HERO.git
cd SERVICE-HERO

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env.development

# Edit configuration (use your preferred editor)
nano .env.development
```

**.env.development:**
```bash
DATABASE_URL=sqlite:///./service_hero_dev.db
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=development-secret-key-change-me
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Development API Keys (get from team)
TWILIO_ACCOUNT_SID=your_test_sid
TWILIO_AUTH_TOKEN=your_test_token
```

### 3. Database Setup
```bash
# Initialize database
python -c "
import asyncio
from database import init_database
asyncio.run(init_database())
"

# Verify setup
python -c "
from database import db_manager
print('✅ Database initialized successfully')
"
```

### 4. Run Development Server
```bash
# Start the application
python main.py --dev --reload

# Test in another terminal
curl http://localhost:8000/health
# Should return: {"status": "healthy", ...}
```

### 5. Run Tests
```bash
# Run full test suite
./test_runner.sh

# Or run specific tests
python -m pytest test_service_hero.py -v
python -m pytest test_integration.py -v
```

**🎉 You're Ready!** Service Hero should be running at `http://localhost:8000`

---

## 🏗️ Architecture Overview

### Core Components
```
service-hero/
├── main.py                 # FastAPI application entry point
├── auth.py                 # JWT authentication & user management
├── database.py             # Database models & operations
├── validation.py           # Input validation & sanitization
├── integrations.py         # Third-party service connectors
├── workflow_engine.py      # Basic workflow processing
├── workflow_engine_enhanced.py  # Production workflow engine
└── templates/              # Jinja2 HTML templates
    └── home.html
```

### Key Patterns

#### 1. **Async-First Architecture**
All database operations and external API calls use async/await:
```python
# ✅ Good - Async database operation
async def create_user(user_data: UserRecord) -> int:
    async with db_manager.get_cursor() as cursor:
        cursor.execute("INSERT INTO users...", user_data)
        return cursor.lastrowid

# ❌ Bad - Blocking operation
def create_user_sync(user_data):
    cursor = db.cursor()
    cursor.execute("INSERT INTO users...", user_data)
```

#### 2. **Security-First Design**
Every input is validated and sanitized:
```python
# ✅ Good - Validated model
class PlumberEmergencyRequest(BaseModel):
    customer_phone: str = Field(pattern=r"^\+?[\d\s\-\(\)]{10,20}$")
    issue: str = Field(min_length=5, max_length=500)
    
    @field_validator('issue')
    def validate_issue(cls, v):
        if not TextSanitizer.is_safe(v):
            raise ValueError('Issue contains unsafe content')
        return TextSanitizer.sanitize(v)
```

#### 3. **Template-Driven Workflows**
Business logic is configuration, not code:
```python
# Template defines behavior
plumber_template = WorkflowTemplate(
    id="plumber_emergency",
    steps=[
        WorkflowStep(
            id="dispatch_sms",
            type=StepType.ACTION,
            config={
                "service": "twilio",
                "message": "Emergency received at {{location}}. ETA: {{eta}}"
            }
        )
    ]
)
```

---

## 🔧 Development Workflow

### Branch Strategy
- **`main`**: Production-ready code
- **`develop`**: Integration branch for features
- **`feature/xyz`**: Individual feature development
- **`hotfix/xyz`**: Critical production fixes

### Development Process
1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-integration
   ```

2. **Write Tests First (TDD)**
   ```python
   # test_new_feature.py
   def test_new_integration_handles_failure():
       """Test that new integration handles API failures gracefully"""
       # Arrange
       integration = NewIntegration()
       
       # Act & Assert
       with pytest.raises(IntegrationError):
           await integration.send_message("invalid_data")
   ```

3. **Implement Feature**
   ```python
   # new_integration.py
   class NewIntegration:
       async def send_message(self, data):
           if not self._validate_data(data):
               raise IntegrationError("Invalid data format")
           # Implementation...
   ```

4. **Run Quality Checks**
   ```bash
   # Format code
   black . --line-length 88
   
   # Check imports
   isort . --profile black
   
   # Type checking
   mypy . --ignore-missing-imports
   
   # Run tests
   pytest --cov=. --cov-report=html
   
   # Security scan
   bandit -r . -x tests/
   ```

5. **Create Pull Request**
   - Use descriptive titles
   - Include test coverage
   - Link to relevant issues
   - Request reviews from team

---

## 🎯 Common Development Tasks

### Adding a New Business Type Template

#### 1. Define Template Structure
```python
# templates/hvac_templates.py
def create_hvac_emergency_template():
    return WorkflowTemplate(
        id="hvac_emergency",
        name="HVAC Emergency Response",
        description="Automated HVAC emergency dispatch and customer communication",
        industry="hvac",
        steps=[
            WorkflowStep(
                id="trigger",
                type=StepType.TRIGGER,
                name="Emergency Request",
                config={"event": "hvac_emergency"}
            ),
            WorkflowStep(
                id="dispatch_sms",
                type=StepType.ACTION,
                name="Send Emergency SMS",
                config={
                    "service": "twilio",
                    "action": "send",
                    "params": {
                        "to": "{{customer_phone}}",
                        "message": "HVAC emergency received. Technician dispatched to {{location}}. ETA: {{response_time}} minutes."
                    }
                }
            )
        ]
    )
```

#### 2. Add Validation Models
```python
# validation.py
class HVACEmergencyRequest(BaseModel):
    """Validated HVAC emergency request"""
    customer_phone: str = Field(pattern=r"^\+?[\d\s\-\(\)]{10,20}$")
    location: str = Field(min_length=5, max_length=200)
    system_type: str = Field(pattern="^(heating|cooling|both)$")
    issue: str = Field(min_length=10, max_length=500)
    urgency: str = Field(pattern="^(low|medium|high|critical)$")
    
    @field_validator('issue')
    def validate_issue(cls, v):
        if not TextSanitizer.is_safe(v):
            raise ValueError('Issue contains unsafe content')
        return TextSanitizer.sanitize(v, 500)
```

#### 3. Write Tests
```python
# test_hvac_templates.py
class TestHVACTemplates:
    def test_hvac_emergency_validation(self):
        """Test HVAC emergency request validation"""
        valid_request = HVACEmergencyRequest(
            customer_phone="+1-555-123-4567",
            location="123 Business Park",
            system_type="heating",
            issue="Heating system not working, office is freezing",
            urgency="high"
        )
        assert valid_request.system_type == "heating"
        
    def test_hvac_template_structure(self):
        """Test HVAC template has correct structure"""
        template = create_hvac_emergency_template()
        assert template.id == "hvac_emergency"
        assert len(template.steps) >= 2
        assert template.steps[0].type == StepType.TRIGGER
```

### Adding a New Integration

#### 1. Create Integration Handler
```python
# integrations/slack_integration.py
import aiohttp
from typing import Dict, Any

class SlackIntegration:
    """Slack notifications integration"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def send_notification(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send Slack notification"""
        if action == "send":
            return await self._send_message(params)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to Slack"""
        payload = {
            "text": params.get("message", ""),
            "channel": params.get("channel", "#general"),
            "username": params.get("username", "Service Hero")
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json=payload) as response:
                if response.status == 200:
                    return {
                        "message_id": f"slack_{int(time.time())}",
                        "status": "sent",
                        "channel": payload["channel"]
                    }
                else:
                    raise Exception(f"Slack API error: {response.status}")
```

#### 2. Register Integration
```python
# integrations.py
from integrations.slack_integration import SlackIntegration

def register_integrations(engine: EnhancedWorkflowEngine):
    """Register all available integrations"""
    
    # Existing integrations
    twilio = TwilioSMSIntegration()
    engine.register_integration("twilio", twilio.send_sms)
    
    # New Slack integration
    slack = SlackIntegration(webhook_url=os.getenv("SLACK_WEBHOOK_URL"))
    engine.register_integration("slack", slack.send_notification)
```

#### 3. Add Integration Tests
```python
# test_slack_integration.py
@pytest.mark.asyncio
class TestSlackIntegration:
    async def test_slack_send_message(self):
        """Test Slack message sending"""
        integration = SlackIntegration("https://hooks.slack.com/test")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await integration.send_notification("send", {
                "message": "Test notification",
                "channel": "#alerts"
            })
            
            assert result["status"] == "sent"
            assert "message_id" in result
```

---

## 🧪 Testing Guidelines

### Test Structure
```
tests/
├── unit/
│   ├── test_validation.py      # Input validation tests
│   ├── test_auth.py           # Authentication tests
│   └── test_database.py       # Database operation tests
├── integration/
│   ├── test_workflows.py      # End-to-end workflow tests
│   ├── test_integrations.py   # External service tests
│   └── test_api.py           # API endpoint tests
└── fixtures/
    ├── sample_data.py         # Test data fixtures
    └── mock_responses.py      # Mock API responses
```

### Test Patterns

#### 1. **Unit Tests**
Test individual functions in isolation:
```python
def test_phone_number_validation():
    """Test phone number validation logic"""
    # Valid formats
    assert PhoneNumber.validate("+1-555-123-4567")
    assert PhoneNumber.validate("(555) 123-4567")
    
    # Invalid formats
    assert not PhoneNumber.validate("123")
    assert not PhoneNumber.validate("abc-def-ghij")
```

#### 2. **Integration Tests**
Test component interactions:
```python
@pytest.mark.asyncio
async def test_workflow_execution_with_database():
    """Test complete workflow execution with database persistence"""
    engine = EnhancedWorkflowEngine()
    template = create_test_template()
    engine.register_template(template)
    
    # Execute workflow
    execution_id = await engine.start_workflow(
        template.id, "test_user", {"phone": "+1-555-123-4567"}
    )
    
    # Verify database persistence
    execution = await engine.get_execution_status(execution_id)
    assert execution.status == ExecutionStatus.COMPLETED
```

#### 3. **API Tests**
Test HTTP endpoints:
```python
def test_workflow_creation_endpoint():
    """Test workflow creation API endpoint"""
    response = client.post("/workflows", json={
        "template_id": "plumber_emergency",
        "name": "Test Workflow",
        "configuration": {"business_phone": "+1-555-123-4567"}
    }, headers={"Authorization": f"Bearer {test_token}"})
    
    assert response.status_code == 201
    assert response.json()["id"].startswith("wf_")
```

### Test Data Management
```python
# fixtures/sample_data.py
@pytest.fixture
def sample_plumber_request():
    return PlumberEmergencyRequest(
        customer_phone="+1-555-987-6543",
        location="123 Test Street",
        issue="Test pipe burst for integration testing",
        urgency="high"
    )

@pytest.fixture
async def test_database():
    """Create isolated test database"""
    db = DatabaseManager()
    db.db_path = ":memory:"
    await db.initialize()
    yield db
    await db.close()
```

---

## 🔍 Debugging Guide

### Common Issues and Solutions

#### 1. **Database Connection Errors**
```python
# Problem: "database is locked" error
# Solution: Ensure proper async context management
async with db_manager.get_cursor() as cursor:
    # Database operations here
    pass  # Cursor automatically closed and committed
```

#### 2. **JWT Token Issues**
```python
# Problem: "Invalid token" errors
# Solution: Check token expiration and secret key
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
print(f"Token expires at: {datetime.fromtimestamp(payload['exp'])}")
```

#### 3. **Workflow Execution Failures**
```python
# Problem: Steps not executing
# Solution: Check step configuration and next_steps
template = engine.get_template(template_id)
for step in template.steps:
    print(f"Step {step.id}: type={step.type}, next={step.next_steps}")
```

### Debugging Tools

#### 1. **Enable Debug Logging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add debug statements
logger.debug(f"Processing workflow {workflow_id} with data: {trigger_data}")
```

#### 2. **Use Debugger**
```python
import pdb

async def debug_workflow_execution(execution_id):
    pdb.set_trace()  # Debugger breakpoint
    execution = await engine.get_execution_status(execution_id)
    return execution
```

#### 3. **Profile Performance**
```python
import cProfile
import pstats

def profile_function():
    pr = cProfile.Profile()
    pr.enable()
    
    # Code to profile
    result = expensive_operation()
    
    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative').print_stats(10)
    return result
```

---

## 📚 Code Style Guidelines

### Python Style (PEP 8 + Black)
```python
# ✅ Good
class WorkflowEngine:
    """Workflow execution engine with proper docstring."""
    
    def __init__(self, config: WorkflowConfig) -> None:
        self.config = config
        self.templates: Dict[str, WorkflowTemplate] = {}
    
    async def execute_workflow(
        self, template_id: str, trigger_data: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute workflow with proper type hints and documentation."""
        template = self.templates.get(template_id)
        if not template:
            raise WorkflowNotFoundError(f"Template {template_id} not found")
        
        return await self._process_workflow(template, trigger_data)

# ❌ Bad  
class workflowEngine:
    def __init__(self,config):
        self.config=config
        self.templates={}
    def executeWorkflow(self,templateId,triggerData):
        template=self.templates.get(templateId)
        if not template:raise Exception("not found")
        return self._processWorkflow(template,triggerData)
```

### Documentation Standards
```python
def validate_phone_number(phone: str) -> bool:
    """Validate phone number format for service business use.
    
    Accepts US and international formats with various separators.
    Blocks common attack patterns and malformed inputs.
    
    Args:
        phone: Phone number string to validate
        
    Returns:
        True if phone number is valid format, False otherwise
        
    Examples:
        >>> validate_phone_number("+1-555-123-4567")
        True
        >>> validate_phone_number("invalid")
        False
        
    Raises:
        ValueError: If phone contains malicious content
    """
```

---

## 🤝 Contributing Guidelines

### Pull Request Process
1. **Fork and Branch**
   ```bash
   git checkout -b feature/descriptive-name
   ```

2. **Make Changes**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Everything**
   ```bash
   # Run full test suite
   pytest tests/ -v --cov=.
   
   # Check code quality
   black . --check
   isort . --check-only --profile black
   mypy . --ignore-missing-imports
   ```

4. **Create Pull Request**
   - Use clear, descriptive title
   - Include motivation and context
   - Link related issues
   - Add screenshots for UI changes

### Commit Message Format
```
type(scope): brief description

Longer explanation if needed

- List specific changes
- Include breaking changes
- Reference issues: Fixes #123
```

**Types:** feat, fix, docs, style, refactor, test, chore

---

## 📖 Resources & References

### Internal Documentation
- [API Documentation](API_DOCS.md) - Complete API reference
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
- [Business Case](BUSINESS_CASE.md) - ROI and market analysis
- [Test Results](TEST_RESULTS.md) - Test coverage and security validation

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Models](https://pydantic-docs.helpmanual.io/)
- [SQLite Async](https://docs.python.org/3/library/sqlite3.html)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

### Development Tools
- [VS Code Python Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Postman](https://www.postman.com/) for API testing

---

## 🆘 Getting Help

### Team Communication
- **Slack**: #servicehero-dev channel
- **Email**: dev-team@servicehero.com
- **Office Hours**: Tuesdays 2-4 PM PT

### Issue Reporting
1. Check existing issues first
2. Use issue templates
3. Include reproduction steps
4. Add relevant labels
5. Assign to appropriate team member

### Code Review Process
- All changes require peer review
- Focus on logic, security, and maintainability
- Be constructive and specific in feedback
- Approve only when confident in changes

---

**Welcome to the team! 🚀 Let's build amazing automation tools for service businesses.**