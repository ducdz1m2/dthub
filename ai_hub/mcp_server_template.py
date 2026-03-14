from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import time

app = FastAPI(title="Dynamic MCP Server Template")

# Token bảo mật để AI Hub kết nối
AUTH_TOKEN = "your_secret_token_here"

class ToolMetadata(BaseModel):
    name: str
    display_name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema của tham số

class ExecuteRequest(BaseModel):
    tool: str
    parameters: Dict[str, Any]

@app.get("/metadata")
async def get_metadata(x_token: Optional[str] = Header(None)):
    """Trả về Schema của tất cả tools"""
    if x_token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    return {
        "server_name": "My Custom MCP Server",
        "tools": [
            {
                "name": "echo_tool",
                "display_name": "Echo Tool",
                "description": "Trả lại nội dung bạn đã gửi",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Nội dung cần lặp lại"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "calculate_sum",
                "display_name": "Sum Calculator",
                "description": "Tính tổng hai số",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["a", "b"]
                }
            }
        ]
    }

@app.post("/execute")
async def execute_tool(request: ExecuteRequest, x_token: Optional[str] = Header(None)):
    """Thực thi tool cụ thể"""
    if x_token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    tool_name = request.tool
    params = request.parameters
    
    start_time = time.time()
    
    try:
        if tool_name == "echo_tool":
            result = f"You said: {params.get('text')}"
        elif tool_name == "calculate_sum":
            result = params.get('a', 0) + params.get('b', 0)
        else:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        return {
            "status": "success",
            "result": result,
            "execution_time": time.time() - start_time
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "execution_time": time.time() - start_time
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
