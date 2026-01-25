"""
MCP (Model Context Protocol) Server for CaseyOS.

Exposes CaseyOS capabilities to Claude Desktop and other MCP clients.
Tools enable AI assistants to interact with the command queue, execute actions,
search contacts, create drafts, and get proactive notifications.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MCPErrorCode(Enum):
    """Standard MCP error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class MCPError(Exception):
    """MCP protocol error."""
    code: int
    message: str
    data: Optional[Any] = None


@dataclass
class MCPRequest:
    """Incoming MCP request."""
    jsonrpc: str
    method: str
    id: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResponse:
    """Outgoing MCP response."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        response = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            response["id"] = self.id
        if self.error is not None:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response


class MCPServer:
    """
    MCP Server implementation for CaseyOS.
    
    Handles JSON-RPC 2.0 protocol with MCP extensions for:
    - Tool listing and execution
    - Resource access
    - Prompt templates
    """
    
    SERVER_NAME = "caseyos-mcp-server"
    SERVER_VERSION = "1.0.0"
    PROTOCOL_VERSION = "2024-11-05"
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tool_handlers: Dict[str, callable] = {}
        self._initialized = False
        
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: callable
    ):
        """Register a tool with its handler."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema
        }
        self._tool_handlers[name] = handler
        logger.info(f"Registered MCP tool: {name}")
        
    async def handle_message(self, message: str) -> str:
        """Handle incoming MCP message and return response."""
        try:
            data = json.loads(message)
            request = MCPRequest(
                jsonrpc=data.get("jsonrpc", "2.0"),
                method=data.get("method", ""),
                id=data.get("id"),
                params=data.get("params", {})
            )
            
            result = await self._dispatch(request)
            
            response = MCPResponse(
                id=request.id,
                result=result
            )
            
        except MCPError as e:
            response = MCPResponse(
                id=data.get("id") if 'data' in dir() else None,
                error={
                    "code": e.code,
                    "message": e.message,
                    "data": e.data
                }
            )
        except json.JSONDecodeError:
            response = MCPResponse(
                error={
                    "code": MCPErrorCode.PARSE_ERROR.value,
                    "message": "Invalid JSON"
                }
            )
        except Exception as e:
            logger.exception("MCP internal error")
            response = MCPResponse(
                id=data.get("id") if 'data' in dir() else None,
                error={
                    "code": MCPErrorCode.INTERNAL_ERROR.value,
                    "message": str(e)
                }
            )
            
        return json.dumps(response.to_dict())
    
    async def _dispatch(self, request: MCPRequest) -> Any:
        """Dispatch request to appropriate handler."""
        method = request.method
        params = request.params
        
        if method == "initialize":
            return await self._handle_initialize(params)
        elif method == "initialized":
            return await self._handle_initialized()
        elif method == "tools/list":
            return await self._handle_tools_list()
        elif method == "tools/call":
            return await self._handle_tools_call(params)
        elif method == "resources/list":
            return await self._handle_resources_list()
        elif method == "prompts/list":
            return await self._handle_prompts_list()
        elif method == "ping":
            return {}
        else:
            raise MCPError(
                code=MCPErrorCode.METHOD_NOT_FOUND.value,
                message=f"Method not found: {method}"
            )
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        client_info = params.get("clientInfo", {})
        logger.info(f"MCP client connecting: {client_info.get('name', 'unknown')}")
        
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION
            },
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            }
        }
    
    async def _handle_initialized(self) -> None:
        """Handle initialized notification."""
        self._initialized = True
        logger.info("MCP session initialized")
        return None
    
    async def _handle_tools_list(self) -> Dict[str, Any]:
        """Return list of available tools."""
        return {
            "tools": list(self._tools.values())
        }
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return result."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self._tool_handlers:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS.value,
                message=f"Unknown tool: {tool_name}"
            )
        
        handler = self._tool_handlers[tool_name]
        
        try:
            result = await handler(**arguments)
            
            # Format as MCP tool result
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str)
                    }
                ]
            }
        except Exception as e:
            logger.exception(f"Tool execution error: {tool_name}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"error": str(e)})
                    }
                ],
                "isError": True
            }
    
    async def _handle_resources_list(self) -> Dict[str, Any]:
        """Return list of available resources."""
        # Future: expose HubSpot contacts, Gmail threads, etc. as resources
        return {"resources": []}
    
    async def _handle_prompts_list(self) -> Dict[str, Any]:
        """Return list of available prompt templates."""
        # Future: expose email templates, follow-up prompts, etc.
        return {"prompts": []}


# Singleton server instance
_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    """Get or create MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
        # Register tools on first access
        from src.mcp.tools import register_caseyos_tools
        register_caseyos_tools(_mcp_server)
    return _mcp_server
