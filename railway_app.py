# railway_app.py - Complete Power BI MCP Server
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
#endregion

#region Helper Functions
def make_request(url, method="GET", data=None):
    """Simple HTTP request helper. Returns JSON response or error dict"""
    if not ensure_token():
        return {"error": "Failed to obtain access token"}
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers, json=data)
        
        if response.ok:
            return response.json()
        else:
            # If token expired, try to refresh once
            if response.status_code == 401:
                if get_access_token():
                    headers["Authorization"] = f"Bearer {TOKEN}"
                    if method == "GET":
                        response = requests.get(url, headers=headers)
                    else:
                        response = requests.post(url, headers=headers, json=data)
                    
                    if response.ok:
                        return response.json()
            
            return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def wait_for_operation(location_url, retry_seconds=30):
    """Wait for a long-running operation to complete"""
    if not ensure_token():
        return {"error": "Failed to obtain access token"}
        
    headers = {"Authorization": f"Bearer {TOKEN}"}
    max_retries = 5
    retries = 0
    
    while retries < max_retries:
        time.sleep(retry_seconds)
        response = requests.get(location_url, headers=headers)
        
        if response.ok:
            data = response.json()
            status = data.get('status', '')
            
            if status == 'Succeeded':
                result_response = requests.get(f"{location_url}/result", headers=headers)
                return result_response.json() if result_response.ok else {"error": "Failed to get result"}
            elif status == 'Failed':
                return {"error": data.get('error', 'Operation failed')}
        else:
            return {"error": f"Failed to check status: {response.status_code}"}
        
        retries += 1
    
    return {"error": "Operation timed out"}
#endregion

#region Power BI Tool Functions
def list_workspaces() -> str:
    """List all Power BI workspaces you have access to"""
    result = make_request(f"{POWERBI_API}/groups")
    
    if "error" in result:
        return f"Error: {result['error']}"
    
    workspaces = result.get("value", [])
    if not workspaces:
        return "No workspaces found"
    
    output = f"Found {len(workspaces)} workspaces:\n\n"
    for ws in workspaces:
        output += f"• {ws['name']} (ID: {ws['id']})\n"
    
    return output

def list_datasets(workspace_id: str) -> str:
    """List all datasets in a specific workspace"""
    result = make_request(f"{POWERBI_API}/groups/{workspace_id}/datasets")
    
    if "error" in result:
        return f"Error: {result['error']}"
    
    datasets = result.get("value", [])
    if not datasets:
        return "No datasets found in this workspace"
    
    output = f"Found {len(datasets)} datasets:\n\n"
    for ds in datasets:
        output += f"• {ds['name']} (ID: {ds['id']})\n"
    
    return output

def get_model_definition(workspace_id: str, dataset_id: str) -> str:
    """Get the complete TMDL definition of a semantic model"""
    if not ensure_token():
        return "Error: Failed to obtain access token"
    
    url = f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels/{dataset_id}/getDefinition"
    response = requests.post(url, headers={"Authorization": f"Bearer {TOKEN}"})
    
    if response.status_code == 202:
        location = response.headers.get('Location')
        retry_after = int(response.headers.get('Retry-After', 30))
        result = wait_for_operation(location, retry_after)
    elif response.ok:
        result = response.json()
    else:
        return f"Error: HTTP {response.status_code}"
    
    if "error" in result:
        return f"Error: {result['error']}"
    
    parts = result.get("definition", {}).get("parts", [])
    if not parts:
        return "No model definition found"
    
    output = f"Dataset Model Definition (TMDL Format)\n{'='*40}\n\n"
    
    for part in parts:
        path = part.get("path", "")
        payload = part.get("payload", "")
        
        if not path.endswith('.tmdl'):
            continue
            
        try:
            content = base64.b64decode(payload).decode('utf-8')
            output += f"\n{'-'*40}\n"
            output += f"File: {path}\n"
            output += f"{'-'*40}\n"
            output += content
            output += "\n"
        except Exception as e:
            output += f"\nError decoding {path}: {str(e)}\n"
    
    return output

def execute_dax_query(workspace_id: str, dataset_id: str, query: str) -> str:
    """Execute a DAX query against a Power BI dataset"""
    data = {"queries": [{"query": query}]}
    url = f"{POWERBI_API}/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
    result = make_request(url, method="POST", data=data)
    
    if "error" in result:
        return f"Error: {result['error']}"
    
    results = result.get("results", [])
    if results and "tables" in results[0]:
        return json.dumps(results[0]["tables"], indent=2)
    else:
        return "No data returned"

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
        # LOGGING DETALLADO PARA DEBUGGING
        print("="*50)
        print("INCOMING REQUEST FROM COPILOT STUDIO:")
        print(f"Request type: {type(request)}")
        print(f"Request content: {json.dumps(request, indent=2)}")
        print("="*50)

        method = request.get('method')
        
        if method == "list_tools":
            result = get_available_tools()
        elif method == "call_tool":
            params = request.get('params', {})
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            result = call_powerbi_tool(tool_name, arguments)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def call_powerbi_tool(tool_name: str, arguments: Dict[str, Any]):
    """Execute a specific Power BI tool"""
    try:
        if tool_name == "list_workspaces":
            result_text = list_workspaces()
            
        elif tool_name == "list_datasets":
            workspace_id = arguments.get('workspace_id')
            if not workspace_id:
                return {"error": "workspace_id is required for list_datasets"}
            result_text = list_datasets(workspace_id)
            
        elif tool_name == "get_model_definition":
            workspace_id = arguments.get('workspace_id')
            dataset_id = arguments.get('dataset_id')
            if not workspace_id or not dataset_id:
                return {"error": "workspace_id and dataset_id are required for get_model_definition"}
            result_text = get_model_definition(workspace_id, dataset_id)
            
        elif tool_name == "execute_dax_query":
            workspace_id = arguments.get('workspace_id')
            dataset_id = arguments.get('dataset_id')
            query = arguments.get('query')
            if not workspace_id or not dataset_id or not query:
                return {"error": "workspace_id, dataset_id, and query are required for execute_dax_query"}
            result_text = execute_dax_query(workspace_id, dataset_id, query)
            
        elif tool_name == "test_connection":
            result_text = test_connection()
            
        else:
            return {"error": f"Unknown tool: {tool_name}"}
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        }
        
    except Exception as e:
        return {"error": f"Error calling tool {tool_name}: {str(e)}"}

def get_available_tools():
    """List available tools in the Power BI MCP"""
    return {
        "tools": [
            {
                "name": "list_workspaces",
                "description": "List all Power BI workspaces you have access to. Returns formatted list of workspace names and IDs."
            },
            {
                "name": "list_datasets",
                "description": "List all datasets in a specific workspace. Returns formatted list of dataset names and IDs."
            },
            {
                "name": "get_model_definition",
                "description": "Get the complete TMDL definition of a semantic model including tables, columns, measures, and relationships."
            },
            {
                "name": "execute_dax_query",
                "description": "Execute a DAX query against a Power BI dataset. Returns query results as JSON data."
            },
            {
                "name": "test_connection",
                "description": "Test the connection and authentication to Power BI API. Returns connection status and basic info."
            }
        ]
    }
#endregion