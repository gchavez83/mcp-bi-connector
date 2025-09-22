# railway_app.py - Pure FastAPI version for Railway (no grpcio dependencies)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
import os
import time
import base64
from typing import Dict, Any

app = FastAPI(title="Power BI MCP Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug: Print environment variables on startup
print(f"CLIENT_ID: {os.environ.get('CLIENT_ID', 'NOT_FOUND')}")
print(f"CLIENT_SECRET: {'***' if os.environ.get('CLIENT_SECRET') else 'NOT_FOUND'}")
print(f"TENANT_ID: {os.environ.get('TENANT_ID', 'NOT_FOUND')}")

# Configuration - Power BI MCP
POWERBI_API = "https://api.powerbi.com/v1.0/myorg"
FABRIC_API = "https://api.fabric.microsoft.com/v1"

# Azure App Registration - Variables de entorno requeridas
CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
TENANT_ID = os.environ.get("TENANT_ID", "")

# Power BI scope
SCOPE = "https://analysis.windows.net/powerbi/api/.default"

# Global token variable
TOKEN = ""

#region Authentication Functions
def get_access_token():
    """Get OAuth2 token using client credentials flow"""
    global TOKEN
    
    if not CLIENT_ID or not CLIENT_SECRET or not TENANT_ID:
        print("Missing required environment variables")
        return False
    
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': SCOPE
    }
    
    try:
        response = requests.post(token_url, data=data)
        if response.ok:
            token_data = response.json()
            TOKEN = token_data['access_token']
            print(f"Token obtained successfully. Expires in {token_data.get('expires_in', 'unknown')} seconds")
            return True
        else:
            print(f"Token error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Token exception: {str(e)}")
        return False

def ensure_token():
    """Ensure we have a valid token"""
    if not TOKEN:
        return get_access_token()
    return True

def test_connection() -> str:
    """Test the connection and authentication to Power BI API"""
    if get_access_token():
        return "Authentication successful! Token obtained and ready to use."
    else:
        return "Authentication failed! Check your client credentials."
#endregion

#region FastAPI Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Power BI MCP Server is running",
        "version": "1.0.0",
        "endpoints": {
            "main": "/api/mcp-endpoint (POST)",
            "health": "/api/health (GET)",
            "test": "/api/test (GET)"
        },
        "environment_check": {
            "CLIENT_ID": "SET" if CLIENT_ID else "MISSING",
            "CLIENT_SECRET": "SET" if CLIENT_SECRET else "MISSING", 
            "TENANT_ID": "SET" if TENANT_ID else "MISSING"
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Power BI MCP Server"}

@app.get("/api/test")
async def test_powerbi_connection():
    """Test endpoint to verify Power BI connection"""
    connection_result = test_connection()
    return {
        "service": "Power BI MCP Server",
        "connection_test": connection_result
    }

@app.post("/api/mcp-endpoint")
async def mcp_endpoint(request: dict):
    """Main endpoint for MCP interactions"""
    try:
        method = request.get('method')
        
        if method == "list_tools":
            result = {
                "tools": [
                    {
                        "name": "test_connection",
                        "description": "Test the connection and authentication to Power BI API"
                    }
                ]
            }
        elif method == "call_tool":
            params = request.get('params', {})
            tool_name = params.get('name')
            
            if tool_name == "test_connection":
                result = {"content": [{"type": "text", "text": test_connection()}]}
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
#endregion