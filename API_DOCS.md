# Service Hero API Documentation

## 🚀 Overview

The Service Hero API provides programmatic access to automation templates, workflow management, and business integrations. Built on FastAPI with automatic OpenAPI documentation.

**Base URL**: `https://api.servicehero.com/v1`
**Authentication**: JWT Bearer tokens
**Rate Limiting**: 1000 requests/hour per API key

---

## 🔐 Authentication

### Get Access Token
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@business.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### API Key Authentication (Alternative)
```http
GET /workflows
Authorization: Bearer your_jwt_token_here
```

---

## 🛠️ Workflows API

### List All Workflows
```http
GET /workflows
Authorization: Bearer {token}
```

**Response:**
```json
{
  "workflows": [
    {
      "id": "wf_12345",
      "name": "Plumber Emergency Response",
      "template_id": "plumber_emergency",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "executions_count": 147,
      "success_rate": 0.96
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

### Create New Workflow
```http
POST /workflows
Authorization: Bearer {token}
Content-Type: application/json

{
  "template_id": "plumber_emergency",
  "name": "Emergency Response - Downtown",
  "configuration": {
    "business_phone": "+1-555-123-4567",
    "response_time_minutes": 30,
    "emergency_contacts": ["tech1@business.com", "manager@business.com"]
  }
}
```

**Response:**
```json
{
  "id": "wf_67890",
  "name": "Emergency Response - Downtown",
  "template_id": "plumber_emergency",
  "status": "active",
  "created_at": "2024-01-15T14:22:00Z",
  "webhook_url": "https://api.servicehero.com/webhooks/wf_67890"
}
```

### Execute Workflow
```http
POST /workflows/{workflow_id}/execute
Authorization: Bearer {token}
Content-Type: application/json

{
  "trigger_data": {
    "customer_phone": "+1-555-987-6543",
    "location": "123 Main St, Downtown",
    "issue": "Burst pipe flooding basement",
    "urgency": "critical"
  }
}
```

**Response:**
```json
{
  "execution_id": "exec_abc123",
  "workflow_id": "wf_67890",
  "status": "pending",
  "created_at": "2024-01-15T15:45:00Z",
  "estimated_completion": "2024-01-15T15:47:00Z"
}
```

### Get Execution Status
```http
GET /executions/{execution_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "exec_abc123",
  "workflow_id": "wf_67890",
  "status": "completed",
  "started_at": "2024-01-15T15:45:00Z",
  "completed_at": "2024-01-15T15:46:30Z",
  "steps": [
    {
      "step_id": "dispatch_sms",
      "status": "completed",
      "output": {
        "message_id": "SM_xyz789",
        "delivered": true,
        "delivery_time": "2024-01-15T15:45:15Z"
      }
    },
    {
      "step_id": "email_notification",
      "status": "completed", 
      "output": {
        "email_id": "EM_def456",
        "opened": true,
        "open_time": "2024-01-15T15:46:22Z"
      }
    }
  ],
  "success_rate": 1.0,
  "total_duration_seconds": 90
}
```

---

## 📋 Templates API

### List Available Templates
```http
GET /templates
Authorization: Bearer {token}
```

**Query Parameters:**
- `industry`: Filter by industry (plumbing, dental, salon, auto_repair)
- `category`: Filter by category (communication, operations, revenue)

**Response:**
```json
{
  "templates": [
    {
      "id": "plumber_emergency",
      "name": "Plumber Emergency Response",
      "description": "Automated emergency dispatch and customer communication",
      "industry": "plumbing",
      "category": "communication",
      "steps_count": 5,
      "avg_execution_time": 180,
      "success_rate": 0.97,
      "monthly_usage": 1247
    }
  ]
}
```

### Get Template Details
```http
GET /templates/{template_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "plumber_emergency",
  "name": "Plumber Emergency Response",
  "description": "Automated emergency dispatch and customer communication",
  "industry": "plumbing",
  "category": "communication",
  "steps": [
    {
      "id": "trigger",
      "type": "trigger",
      "name": "Emergency Received",
      "config": {
        "event": "emergency_request"
      },
      "next_steps": ["dispatch_sms"]
    },
    {
      "id": "dispatch_sms",
      "type": "action",
      "name": "Send Dispatch SMS", 
      "config": {
        "service": "twilio",
        "action": "send",
        "params": {
          "to": "{{customer_phone}}",
          "message": "Emergency received at {{location}}. Plumber dispatched within {{response_time_minutes}} minutes."
        }
      },
      "next_steps": ["email_notification"]
    }
  ],
  "required_integrations": ["twilio"],
  "configuration_schema": {
    "business_phone": {
      "type": "string",
      "required": true,
      "description": "Business phone number for customer communication"
    },
    "response_time_minutes": {
      "type": "integer",
      "default": 30,
      "description": "Promised response time in minutes"
    }
  }
}
```

---

## 🔗 Integrations API

### List Available Integrations
```http
GET /integrations
Authorization: Bearer {token}
```

**Response:**
```json
{
  "integrations": [
    {
      "service": "twilio",
      "name": "Twilio SMS",
      "category": "communication",
      "status": "connected",
      "last_used": "2024-01-15T15:45:00Z",
      "success_rate": 0.99,
      "monthly_usage": 1847
    },
    {
      "service": "sendgrid", 
      "name": "SendGrid Email",
      "category": "communication",
      "status": "available",
      "description": "Professional email automation"
    }
  ]
}
```

### Connect Integration
```http
POST /integrations/{service}/connect
Authorization: Bearer {token}
Content-Type: application/json

{
  "credentials": {
    "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "auth_token": "your_auth_token_here"
  },
  "configuration": {
    "default_from_number": "+1-555-123-4567"
  }
}
```

### Test Integration
```http
POST /integrations/{service}/test
Authorization: Bearer {token}
Content-Type: application/json

{
  "test_params": {
    "to": "+1-555-987-6543",
    "message": "Test message from Service Hero API"
  }
}
```

**Response:**
```json
{
  "success": true,
  "response_time_ms": 245,
  "test_result": {
    "message_id": "SM_test123",
    "status": "sent",
    "cost": 0.0075
  }
}
```

---

## 📊 Analytics API

### Get Workflow Analytics
```http
GET /analytics/workflows/{workflow_id}
Authorization: Bearer {token}
```

**Query Parameters:**
- `start_date`: ISO 8601 date (default: 30 days ago)
- `end_date`: ISO 8601 date (default: now)
- `granularity`: hour, day, week, month

**Response:**
```json
{
  "workflow_id": "wf_67890",
  "period": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-15T23:59:59Z"
  },
  "metrics": {
    "total_executions": 147,
    "successful_executions": 141,
    "success_rate": 0.96,
    "avg_execution_time": 185.2,
    "total_time_saved_hours": 73.5,
    "estimated_cost_savings": 3675.00
  },
  "timeline": [
    {
      "date": "2024-01-01",
      "executions": 8,
      "success_rate": 1.0,
      "avg_duration": 178
    }
  ]
}
```

### Get Business ROI Metrics
```http
GET /analytics/roi
Authorization: Bearer {token}
```

**Response:**
```json
{
  "business_id": "biz_456",
  "period": {
    "start": "2024-01-01T00:00:00Z", 
    "end": "2024-01-15T23:59:59Z"
  },
  "roi_metrics": {
    "time_saved_hours": 245.5,
    "time_saved_value": 12275.00,
    "service_hero_cost": 398.00,
    "net_savings": 11877.00,
    "roi_percentage": 2984.67
  },
  "operational_improvements": {
    "response_time_improvement": 0.82,
    "customer_satisfaction_increase": 0.15,
    "no_show_reduction": 0.34
  }
}
```

---

## 🔔 Webhooks

### Register Webhook Endpoint
```http
POST /webhooks
Authorization: Bearer {token}
Content-Type: application/json

{
  "url": "https://your-server.com/webhook/servicehero",
  "events": [
    "workflow.execution.completed",
    "workflow.execution.failed",
    "integration.error"
  ],
  "secret": "your_webhook_secret"
}
```

### Webhook Event Examples

#### Workflow Execution Completed
```json
{
  "event": "workflow.execution.completed",
  "timestamp": "2024-01-15T15:46:30Z",
  "data": {
    "execution_id": "exec_abc123",
    "workflow_id": "wf_67890",
    "status": "completed",
    "duration_seconds": 90,
    "steps_completed": 3,
    "steps_failed": 0
  }
}
```

#### Integration Error
```json
{
  "event": "integration.error",
  "timestamp": "2024-01-15T16:22:10Z", 
  "data": {
    "integration": "twilio",
    "error_code": "authentication_failed",
    "error_message": "Invalid auth token",
    "affected_workflows": ["wf_67890", "wf_12345"]
  }
}
```

---

## 💼 Business Objects

### User Profile
```http
GET /user/profile
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "user_789",
  "email": "owner@plumbingco.com",
  "business": {
    "id": "biz_456",
    "name": "Downtown Plumbing Co",
    "type": "plumbing",
    "phone": "+1-555-123-4567",
    "address": "123 Business Ave, City, ST 12345"
  },
  "subscription": {
    "plan": "professional",
    "status": "active",
    "monthly_quota": 5000,
    "usage_current_month": 1247,
    "billing_date": "2024-01-28"
  },
  "preferences": {
    "timezone": "America/New_York",
    "notification_email": "owner@plumbingco.com",
    "dashboard_layout": "compact"
  }
}
```

---

## 🎯 SDKs and Code Examples

### Python SDK
```python
from service_hero import ServiceHero

# Initialize client
client = ServiceHero(
    api_key="your_jwt_token",
    base_url="https://api.servicehero.com/v1"
)

# Execute workflow
execution = client.workflows.execute(
    workflow_id="wf_67890",
    trigger_data={
        "customer_phone": "+1-555-987-6543",
        "location": "123 Main St",
        "issue": "Burst pipe flooding basement", 
        "urgency": "critical"
    }
)

print(f"Execution started: {execution.id}")

# Check status
status = client.executions.get(execution.id)
print(f"Status: {status.status}")
```

### JavaScript SDK
```javascript
import ServiceHero from '@servicehero/sdk';

const client = new ServiceHero({
  apiKey: 'your_jwt_token',
  baseUrl: 'https://api.servicehero.com/v1'
});

// Execute workflow
const execution = await client.workflows.execute('wf_67890', {
  trigger_data: {
    customer_phone: '+1-555-987-6543',
    location: '123 Main St',
    issue: 'Burst pipe flooding basement',
    urgency: 'critical'
  }
});

console.log(`Execution started: ${execution.id}`);
```

### cURL Examples
```bash
# Get all workflows
curl -X GET "https://api.servicehero.com/v1/workflows" \
  -H "Authorization: Bearer your_jwt_token"

# Execute workflow  
curl -X POST "https://api.servicehero.com/v1/workflows/wf_67890/execute" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_data": {
      "customer_phone": "+1-555-987-6543",
      "location": "123 Main St", 
      "issue": "Burst pipe flooding basement",
      "urgency": "critical"
    }
  }'
```

---

## ❌ Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "WORKFLOW_NOT_FOUND",
    "message": "Workflow with ID 'wf_invalid' not found",
    "details": {
      "workflow_id": "wf_invalid",
      "suggestion": "Check workflow ID or create new workflow"
    },
    "timestamp": "2024-01-15T16:30:00Z",
    "request_id": "req_xyz789"
  }
}
```

### Common Error Codes
- `AUTHENTICATION_FAILED`: Invalid or expired token
- `RATE_LIMIT_EXCEEDED`: API rate limit reached
- `WORKFLOW_NOT_FOUND`: Workflow ID doesn't exist
- `INVALID_TEMPLATE`: Template ID not recognized
- `INTEGRATION_ERROR`: Third-party service error
- `VALIDATION_ERROR`: Request data validation failed
- `QUOTA_EXCEEDED`: Monthly usage limit reached

---

## 📈 Rate Limits

### Current Limits
- **Free Trial**: 100 requests/hour
- **Starter Plan**: 500 requests/hour  
- **Professional Plan**: 2000 requests/hour
- **Enterprise Plan**: 10000 requests/hour

### Rate Limit Headers
```http
X-RateLimit-Limit: 2000
X-RateLimit-Remaining: 1847
X-RateLimit-Reset: 1642275600
X-RateLimit-Retry-After: 3600
```

---

## 🔄 API Versioning

### Current Version: v1
- **Stable**: Full backward compatibility
- **Deprecation Notice**: 6 months advance notice
- **Version Header**: `Accept: application/vnd.servicehero.v1+json`

### Upcoming v2 Features
- GraphQL endpoint
- Real-time subscriptions
- Batch operations
- Enhanced filtering

---

## 🛡️ Security

### Authentication Best Practices
- Store JWT tokens securely
- Implement token refresh logic
- Use HTTPS for all requests
- Rotate API keys regularly

### Webhook Security
- Verify webhook signatures
- Use HTTPS endpoints only
- Implement idempotency checks
- Store webhook secrets securely

### Data Privacy
- All data encrypted in transit (TLS 1.2+)
- Data encrypted at rest (AES-256)
- GDPR compliant data handling
- SOC 2 Type II certified

---

## 📞 Support

- **API Documentation**: https://docs.servicehero.com/api
- **SDKs**: https://github.com/servicehero/sdks
- **Developer Support**: api-support@servicehero.com
- **Status Page**: https://status.servicehero.com
- **Community**: https://community.servicehero.com/developers

---

*Last Updated: 2024-01-15 | API Version: 1.0*