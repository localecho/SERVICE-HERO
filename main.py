#!/usr/bin/env python3
"""
SERVICE-HERO: Automation Templates for Service Businesses
"""

from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uvicorn

app = FastAPI(title="Service Hero", version="1.0.0")

class BusinessType(BaseModel):
    id: str
    name: str
    description: str
    icon: str

class Template(BaseModel):
    id: str
    name: str
    description: str
    business_type: str
    setup_time: int

business_types = [
    {"id": "plumbing", "name": "Plumbing", "description": "Emergency response automation", "icon": "🔧"},
    {"id": "dental", "name": "Dental", "description": "Appointment management", "icon": "🦷"},
    {"id": "salon", "name": "Salon", "description": "Rebooking automation", "icon": "💇"}
]

templates = [
    {
        "id": "emergency_response",
        "name": "Emergency Response",
        "description": "Automated emergency dispatch and follow-up",
        "business_type": "plumbing",
        "setup_time": 8
    },
    {
        "id": "appointment_flow",
        "name": "Appointment Flow", 
        "description": "Complete appointment lifecycle automation",
        "business_type": "dental",
        "setup_time": 12
    }
]

workflows = []

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head><title>Service Hero</title></head>
    <body style="font-family: Arial; margin: 40px;">
        <h1>🛠️ Service Hero</h1>
        <p>Automation Templates for Service Businesses</p>
        <a href="/templates" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Browse Templates</a>
        <a href="/dashboard" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-left: 10px;">Dashboard</a>
    </body>
    </html>
    """

@app.get("/templates", response_class=HTMLResponse)
def templates_page():
    template_html = ""
    for template in templates:
        template_html += f"""
        <div style="border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 8px;">
            <h3>{template["name"]}</h3>
            <p>{template["description"]}</p>
            <p>Business Type: {template["business_type"].title()}</p>
            <p>Setup Time: {template["setup_time"]} minutes</p>
            <button onclick="deployTemplate('{template["id"]}')" style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Deploy</button>
        </div>
        """
    
    return f"""
    <html>
    <head><title>Templates - Service Hero</title></head>
    <body style="font-family: Arial; margin: 40px;">
        <h1>🚀 Automation Templates</h1>
        <a href="/" style="color: #007bff; text-decoration: none;">← Back to Home</a>
        {template_html}
        <script>
        function deployTemplate(templateId) {{
            const name = prompt('Enter workflow name:');
            if (name) {{
                fetch('/api/workflows', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                    body: 'template_id=' + templateId + '&name=' + name
                }}).then(() => {{
                    alert('Workflow created!');
                    window.location.href = '/dashboard';
                }});
            }}
        }}
        </script>
    </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse) 
def dashboard():
    workflow_html = ""
    if workflows:
        for workflow in workflows:
            workflow_html += f"""
            <div style="padding: 15px; border-bottom: 1px solid #eee;">
                <strong>{workflow["name"]}</strong><br>
                <small>Template: {workflow["template_id"]} | Status: {workflow["status"]}</small>
            </div>
            """
    else:
        workflow_html = '<p>No workflows yet. <a href="/templates">Create your first workflow</a></p>'
    
    return f"""
    <html>
    <head><title>Dashboard - Service Hero</title></head>
    <body style="font-family: Arial; margin: 40px;">
        <h1>📊 Dashboard</h1>
        <a href="/" style="color: #007bff; text-decoration: none;">← Back to Home</a>
        <h3>Your Workflows ({len(workflows)})</h3>
        <div style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px;">
            {workflow_html}
        </div>
    </body>
    </html>
    """

@app.get("/api/business-types")
def get_business_types():
    return {"business_types": business_types}

@app.get("/api/templates")
def get_templates(business_type: Optional[str] = None):
    filtered = templates
    if business_type:
        filtered = [t for t in templates if t["business_type"] == business_type]
    return {"templates": filtered}

@app.post("/api/workflows")
def create_workflow(template_id: str = Form(...), name: str = Form(...)):
    template = next((t for t in templates if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    workflow = {
        "id": f"workflow_{len(workflows) + 1}",
        "template_id": template_id,
        "name": name,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }
    
    workflows.append(workflow)
    return {"workflow": workflow}

@app.get("/api/workflows")
def get_workflows():
    return {"workflows": workflows}

def main():
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()