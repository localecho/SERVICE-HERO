# Service Hero Deployment Guide

## 🚀 Production Deployment Checklist

### Pre-Deployment Requirements
- [ ] Python 3.8+ installed
- [ ] Docker and Docker Compose installed
- [ ] SSL certificates obtained
- [ ] Database backups configured
- [ ] Monitoring tools configured
- [ ] Environment variables secured

---

## 🏗️ Infrastructure Architecture

### Recommended Production Stack
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Application   │    │    Database     │
│   (nginx/AWS)   │────│   (FastAPI)     │────│  (PostgreSQL)   │
│                 │    │                 │    │                 │
│ • SSL Termination│   │ • Auto-scaling  │    │ • Read replicas │
│ • Rate Limiting │    │ • Health checks │    │ • Backups       │
│ • Caching       │    │ • Log shipping  │    │ • Monitoring    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │     Redis       │
                       │   (Caching)     │
                       │                 │
                       │ • Session store │
                       │ • Rate limiting │
                       │ • Task queues   │
                       └─────────────────┘
```

---

## 🐳 Docker Deployment

### Production Dockerfile
```dockerfile
# Production-optimized Dockerfile
FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r servicehero && useradd -r -g servicehero servicehero

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=servicehero:servicehero . .

# Security: Switch to non-root user
USER servicehero

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Docker Compose (Production)
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/servicehero
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    depends_on:
      - db
      - redis
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: servicehero
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    deploy:
      restart_policy:
        condition: on-failure

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

---

## ☁️ Cloud Platform Deployment

### AWS Deployment (Recommended)

#### ECS with Fargate
```yaml
# ecs-task-definition.json
{
  "family": "servicehero-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/serviceHeroTaskRole",
  "containerDefinitions": [
    {
      "name": "servicehero-app",
      "image": "your-account.dkr.ecr.us-west-2.amazonaws.com/servicehero:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:password@rds-endpoint:5432/servicehero"
        },
        {
          "name": "REDIS_URL", 
          "value": "redis://elasticache-endpoint:6379"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:ACCOUNT:secret:servicehero/secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/servicehero",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### Terraform Infrastructure
```hcl
# main.tf
provider "aws" {
  region = "us-west-2"
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "servicehero-vpc"
  }
}

resource "aws_subnet" "private" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name = "servicehero-private-${count.index + 1}"
  }
}

# RDS Database
resource "aws_db_instance" "main" {
  identifier = "servicehero-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.large"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_encrypted     = true
  
  db_name  = "servicehero"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  deletion_protection = true
  skip_final_snapshot = false
  
  tags = {
    Name = "servicehero-database"
  }
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "main" {
  name       = "servicehero-cache-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "servicehero-redis"
  description                = "Redis cluster for Service Hero"
  
  node_type            = "cache.r6g.large"
  port                 = 6379
  parameter_group_name = "default.redis7"
  
  num_cache_clusters = 2
  
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_password
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "servicehero-cluster"
  
  capacity_providers = ["FARGATE"]
  
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 1
  }
}
```

---

## 🔧 Configuration Management

### Environment Variables
```bash
# .env.production
DATABASE_URL=postgresql://user:password@localhost:5432/servicehero
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=super-secure-secret-key-change-in-production
ENVIRONMENT=production

# External Service Credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxx

# Monitoring
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
DATADOG_API_KEY=your_datadog_key

# Security
CORS_ORIGINS=https://app.servicehero.com,https://servicehero.com
ALLOWED_HOSTS=api.servicehero.com,servicehero.com
```

### Configuration Class
```python
# config/production.py
import os
from pydantic import BaseSettings

class ProductionConfig(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL")
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL")
    redis_pool_size: int = 10
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY")
    cors_origins: list = os.getenv("CORS_ORIGINS", "").split(",")
    allowed_hosts: list = os.getenv("ALLOWED_HOSTS", "").split(",")
    
    # External Services
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN")
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY")
    
    # Monitoring
    sentry_dsn: str = os.getenv("SENTRY_DSN")
    datadog_api_key: str = os.getenv("DATADOG_API_KEY")
    
    # Performance
    worker_processes: int = 4
    max_requests: int = 1000
    max_requests_jitter: int = 100
    
    class Config:
        env_file = ".env.production"
```

---

## 📊 Monitoring & Observability

### Health Check Endpoint
```python
# health.py
from fastapi import APIRouter
from datetime import datetime
import psutil
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check for load balancer"""
    
    # Check database connection
    try:
        await db_manager.initialize()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Redis connection
    try:
        redis_client = redis.Redis.from_url(REDIS_URL)
        redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    return {
        "status": "healthy" if all([
            db_status == "healthy",
            redis_status == "healthy",
            cpu_percent < 80,
            memory.percent < 85
        ]) else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": db_status,
            "redis": redis_status,
            "cpu_usage": f"{cpu_percent}%",
            "memory_usage": f"{memory.percent}%"
        },
        "version": "1.0.0"
    }
```

### Prometheus Metrics
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# Metrics
workflow_executions = Counter('workflow_executions_total', 'Total workflow executions', ['template', 'status'])
execution_duration = Histogram('workflow_execution_duration_seconds', 'Workflow execution duration')
active_workflows = Gauge('active_workflows', 'Number of active workflows')

@router.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")
```

### Logging Configuration
```python
# logging_config.py
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "json": {
            "format": '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s","module":"%(module)s","function":"%(funcName)s","line":%(lineno)d}',
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "formatter": "json",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "level": "INFO",
            "formatter": "json",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/servicehero/app.log",
            "maxBytes": 10485760,
            "backupCount": 5
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}
```

---

## 🔒 Security Checklist

### SSL/TLS Configuration
```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.servicehero.com;
    
    ssl_certificate /etc/ssl/certs/servicehero.crt;
    ssl_certificate_key /etc/ssl/private/servicehero.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Security Headers
```python
# security.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

def configure_security(app):
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://app.servicehero.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"]
    )
    
    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["api.servicehero.com", "servicehero.com"]
    )
    
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      
      - name: Run tests
        run: pytest test_service_hero.py test_integration.py -v
      
      - name: Security scan
        run: |
          pip install bandit safety
          bandit -r . -x tests/
          safety check

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-west-2
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: servicehero
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster servicehero-cluster \
            --service servicehero-app \
            --force-new-deployment
```

---

## 🔧 Maintenance & Operations

### Database Migrations
```python
# migrations/migrate.py
import asyncio
from alembic import command
from alembic.config import Config

async def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    asyncio.run(run_migrations())
```

### Backup Strategy
```bash
#!/bin/bash
# backup.sh

# PostgreSQL backup
pg_dump $DATABASE_URL | gzip > /backups/servicehero-$(date +%Y%m%d-%H%M%S).sql.gz

# Upload to S3
aws s3 cp /backups/ s3://servicehero-backups/ --recursive

# Cleanup old backups (keep 30 days)
find /backups -name "*.sql.gz" -mtime +30 -delete
```

### Scaling Guidelines
```yaml
# Auto-scaling configuration
auto_scaling:
  target_cpu_utilization: 70
  min_replicas: 2
  max_replicas: 10
  scale_up_cooldown: 300
  scale_down_cooldown: 300
```

---

## 🚨 Incident Response

### Runbook Template
```markdown
# Incident Response Runbook

## Database Connection Issues
1. Check RDS status in AWS Console
2. Verify security group rules
3. Check application logs for connection errors
4. Test connection from application server

## High CPU Usage
1. Check ECS service metrics
2. Scale up service if needed: `aws ecs update-service --desired-count 6`
3. Investigate slow queries in database
4. Check for memory leaks in application

## Integration Failures
1. Check third-party service status (Twilio, SendGrid)
2. Verify API credentials haven't expired
3. Check rate limits and quotas
4. Review error logs for specific failure patterns
```

---

## 📈 Performance Optimization

### Database Optimization
```sql
-- Index creation for common queries
CREATE INDEX CONCURRENTLY idx_executions_user_status ON executions(user_id, status);
CREATE INDEX CONCURRENTLY idx_executions_created_at ON executions(created_at);
CREATE INDEX CONCURRENTLY idx_workflows_template_active ON workflows(template_id) WHERE is_active = true;

-- Query optimization
ANALYZE executions;
ANALYZE workflows;
ANALYZE users;
```

### Caching Strategy
```python
# cache.py
import redis
from functools import wraps

redis_client = redis.Redis.from_url(REDIS_URL)

def cache_result(expiration=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try cache first
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            redis_client.setex(cache_key, expiration, json.dumps(result))
            return result
        return wrapper
    return decorator
```

This comprehensive deployment guide ensures Service Hero can be deployed securely and reliably in production environments with proper monitoring, scaling, and maintenance procedures.