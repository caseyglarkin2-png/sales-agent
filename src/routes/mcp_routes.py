"""
MCP (Model Context Protocol) Routes.

Exposes MCP WebSocket endpoint for Claude Desktop and other MCP clients.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from src.mcp.server import get_mcp_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.get("/info")
async def mcp_info():
    """Get MCP server information and available tools."""
    server = get_mcp_server()
    
    return {
        "server": {
            "name": server.SERVER_NAME,
            "version": server.SERVER_VERSION,
            "protocol_version": server.PROTOCOL_VERSION
        },
        "tools": list(server._tools.keys()),
        "tool_count": len(server._tools),
        "status": "ready"
    }


@router.get("/tools")
async def list_tools():
    """List all available MCP tools with schemas."""
    server = get_mcp_server()
    
    return {
        "tools": list(server._tools.values())
    }


@router.websocket("/ws")
async def mcp_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for MCP protocol communication.
    
    Clients connect here and send JSON-RPC 2.0 messages.
    Used by Claude Desktop and other MCP-compatible clients.
    """
    await websocket.accept()
    server = get_mcp_server()
    
    logger.info("MCP WebSocket client connected")
    
    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            logger.debug(f"MCP received: {message[:200]}...")
            
            # Process through MCP server
            response = await server.handle_message(message)
            
            # Send response
            await websocket.send_text(response)
            logger.debug(f"MCP sent: {response[:200]}...")
            
    except WebSocketDisconnect:
        logger.info("MCP WebSocket client disconnected")
    except Exception as e:
        logger.exception("MCP WebSocket error")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception as close_error:
            logger.debug(f"WebSocket close failed: {close_error}")


@router.post("/message")
async def mcp_http_message(request: dict):
    """
    HTTP endpoint for MCP messages (alternative to WebSocket).
    
    Useful for testing and simple integrations that don't need
    persistent connections.
    """
    import json
    
    server = get_mcp_server()
    message = json.dumps(request)
    
    response = await server.handle_message(message)
    return JSONResponse(content=json.loads(response))


@router.post("/tools/{tool_name}")
async def execute_tool_directly(tool_name: str, arguments: dict = {}):
    """
    Execute a tool directly via HTTP (convenience endpoint).
    
    This bypasses the full MCP protocol for simple integrations.
    """
    server = get_mcp_server()
    
    if tool_name not in server._tool_handlers:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    handler = server._tool_handlers[tool_name]
    
    try:
        result = await handler(**arguments)
        return {"result": result}
    except Exception as e:
        logger.exception(f"Tool execution error: {tool_name}")
        raise HTTPException(status_code=500, detail=str(e))
