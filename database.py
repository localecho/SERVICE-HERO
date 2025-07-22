#!/usr/bin/env python3
"""
SERVICE-HERO Database Layer
SQLite database with proper schema for production use
"""

import sqlite3
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from contextlib import asynccontextmanager

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration"""
    def __init__(self, db_path: str = "service_hero.db"):
        self.db_path = db_path
        self.connection_pool_size = 10


class UserRecord(BaseModel):
    """User record model"""
    id: Optional[int] = None
    email: str
    password_hash: str
    business_name: str
    business_type: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowRecord(BaseModel):
    """Workflow record model"""
    id: Optional[int] = None
    user_id: int
    template_id: str
    name: str
    configuration: Dict[str, Any] = {}
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ExecutionRecord(BaseModel):
    """Execution record model"""
    id: Optional[str] = None  # UUID
    workflow_id: int
    user_id: int
    status: str
    trigger_data: Dict[str, Any] = {}
    step_results: List[Dict[str, Any]] = []
    current_step_id: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class DatabaseManager:
    """SQLite database manager with async operations"""
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self.db_path = self.config.db_path
        self._connection = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database and create tables"""
        if self._initialized:
            return
        
        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create connection
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Create tables
        await self._create_tables()
        
        self._initialized = True
        logger.info(f"Database initialized: {self.db_path}")
    
    async def _create_tables(self):
        """Create database tables"""
        cursor = self._connection.cursor()
        
        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            business_name TEXT NOT NULL,
            business_type TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Workflows table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            template_id TEXT NOT NULL,
            name TEXT NOT NULL,
            configuration TEXT DEFAULT '{}',  -- JSON
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Executions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY,  -- UUID
            workflow_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            trigger_data TEXT DEFAULT '{}',  -- JSON
            step_results TEXT DEFAULT '[]',  -- JSON array
            current_step_id TEXT,
            error_message TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workflow_id) REFERENCES workflows (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Integrations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service_name TEXT NOT NULL,
            configuration TEXT DEFAULT '{}',  -- JSON (encrypted credentials)
            is_active BOOLEAN DEFAULT TRUE,
            last_used_at TIMESTAMP,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, service_name)
        )
        """)
        
        # Analytics table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metadata TEXT DEFAULT '{}',  -- JSON
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_user_id ON executions (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_status ON executions (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_created_at ON executions (created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_user_id ON workflows (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_template_id ON workflows (template_id)")
        
        self._connection.commit()
        logger.info("Database tables created successfully")
    
    async def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._initialized = False
    
    @asynccontextmanager
    async def get_cursor(self):
        """Get database cursor context manager"""
        if not self._initialized:
            await self.initialize()
        
        cursor = self._connection.cursor()
        try:
            yield cursor
        except Exception as e:
            self._connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        else:
            self._connection.commit()
        finally:
            cursor.close()
    
    # User operations
    async def create_user(self, user_data: UserRecord) -> int:
        """Create new user and return user ID"""
        async with self.get_cursor() as cursor:
            cursor.execute("""
            INSERT INTO users (email, password_hash, business_name, business_type)
            VALUES (?, ?, ?, ?)
            """, (user_data.email, user_data.password_hash, user_data.business_name, user_data.business_type))
            
            return cursor.lastrowid
    
    async def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        """Get user by email"""
        async with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = TRUE", (email,))
            row = cursor.fetchone()
            
            if row:
                return UserRecord(
                    id=row['id'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    business_name=row['business_name'],
                    business_type=row['business_type'],
                    is_active=row['is_active'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[UserRecord]:
        """Get user by ID"""
        async with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = ? AND is_active = TRUE", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return UserRecord(
                    id=row['id'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    business_name=row['business_name'],
                    business_type=row['business_type'],
                    is_active=row['is_active'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
            return None
    
    # Workflow operations
    async def create_workflow(self, workflow_data: WorkflowRecord) -> int:
        """Create new workflow and return workflow ID"""
        async with self.get_cursor() as cursor:
            config_json = json.dumps(workflow_data.configuration)
            cursor.execute("""
            INSERT INTO workflows (user_id, template_id, name, configuration)
            VALUES (?, ?, ?, ?)
            """, (workflow_data.user_id, workflow_data.template_id, workflow_data.name, config_json))
            
            return cursor.lastrowid
    
    async def get_workflows_by_user(self, user_id: int, active_only: bool = True) -> List[WorkflowRecord]:
        """Get workflows by user ID"""
        async with self.get_cursor() as cursor:
            query = "SELECT * FROM workflows WHERE user_id = ?"
            params = [user_id]
            
            if active_only:
                query += " AND is_active = TRUE"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            workflows = []
            for row in rows:
                workflows.append(WorkflowRecord(
                    id=row['id'],
                    user_id=row['user_id'],
                    template_id=row['template_id'],
                    name=row['name'],
                    configuration=json.loads(row['configuration']),
                    is_active=row['is_active'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            
            return workflows
    
    # Execution operations
    async def create_execution(self, execution_data: ExecutionRecord) -> str:
        """Create new execution and return execution ID"""
        async with self.get_cursor() as cursor:
            trigger_data_json = json.dumps(execution_data.trigger_data)
            step_results_json = json.dumps(execution_data.step_results)
            
            cursor.execute("""
            INSERT INTO executions (id, workflow_id, user_id, status, trigger_data, step_results, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_data.id,
                execution_data.workflow_id,
                execution_data.user_id,
                execution_data.status,
                trigger_data_json,
                step_results_json,
                execution_data.started_at
            ))
            
            return execution_data.id
    
    async def update_execution(self, execution_id: str, updates: Dict[str, Any]):
        """Update execution record"""
        async with self.get_cursor() as cursor:
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in ['step_results', 'trigger_data'] and isinstance(value, (list, dict)):
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            values.append(execution_id)
            
            query = f"UPDATE executions SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)
    
    async def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get execution by ID"""
        async with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM executions WHERE id = ?", (execution_id,))
            row = cursor.fetchone()
            
            if row:
                return ExecutionRecord(
                    id=row['id'],
                    workflow_id=row['workflow_id'],
                    user_id=row['user_id'],
                    status=row['status'],
                    trigger_data=json.loads(row['trigger_data']),
                    step_results=json.loads(row['step_results']),
                    current_step_id=row['current_step_id'],
                    error_message=row['error_message'],
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    created_at=datetime.fromisoformat(row['created_at'])
                )
            return None
    
    async def get_executions_by_user(self, user_id: int, limit: int = 50) -> List[ExecutionRecord]:
        """Get recent executions by user"""
        async with self.get_cursor() as cursor:
            cursor.execute("""
            SELECT * FROM executions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            executions = []
            
            for row in rows:
                executions.append(ExecutionRecord(
                    id=row['id'],
                    workflow_id=row['workflow_id'],
                    user_id=row['user_id'],
                    status=row['status'],
                    trigger_data=json.loads(row['trigger_data']),
                    step_results=json.loads(row['step_results']),
                    current_step_id=row['current_step_id'],
                    error_message=row['error_message'],
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    created_at=datetime.fromisoformat(row['created_at'])
                ))
            
            return executions
    
    # Analytics operations
    async def record_metric(self, user_id: int, metric_name: str, metric_value: float, metadata: Dict[str, Any] = None):
        """Record analytics metric"""
        async with self.get_cursor() as cursor:
            metadata_json = json.dumps(metadata or {})
            cursor.execute("""
            INSERT INTO analytics (user_id, metric_name, metric_value, metadata)
            VALUES (?, ?, ?, ?)
            """, (user_id, metric_name, metric_value, metadata_json))
    
    async def get_user_metrics(self, user_id: int, metric_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get user metrics for the last N days"""
        async with self.get_cursor() as cursor:
            cursor.execute("""
            SELECT metric_value, metadata, recorded_at
            FROM analytics 
            WHERE user_id = ? AND metric_name = ? 
            AND recorded_at >= datetime('now', '-{} days')
            ORDER BY recorded_at DESC
            """.format(days), (user_id, metric_name))
            
            rows = cursor.fetchall()
            return [
                {
                    'value': row['metric_value'],
                    'metadata': json.loads(row['metadata']),
                    'recorded_at': row['recorded_at']
                }
                for row in rows
            ]


# Global database manager instance
db_manager = DatabaseManager()


async def init_database():
    """Initialize database for the application"""
    await db_manager.initialize()
    logger.info("Database initialization complete")


async def close_database():
    """Close database connections"""
    await db_manager.close()
    logger.info("Database connections closed")