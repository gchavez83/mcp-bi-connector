# main.py - Entry point for Railway deployment
import uvicorn
import os
from function_app import app

if __name__ == "__main__":
    # Railway provides PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Power BI MCP Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)