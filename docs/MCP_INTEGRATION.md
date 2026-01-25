# MCP (Model Context Protocol) Integration

CaseyOS exposes an MCP server that allows AI assistants like Claude Desktop to interact with the platform.

## Available Tools

| Tool | Description |
|------|-------------|
| `read_command_queue` | Get Today's Moves - prioritized action recommendations |
| `execute_action` | Execute a command queue action (with dry-run support) |
| `search_contacts` | Search HubSpot contacts by email/name/company |
| `create_email_draft` | Create a personalized email draft in Gmail |
| `get_notifications` | Get proactive notifications and alerts |
| `record_outcome` | Record outcome for closed-loop learning |
| `get_deal_pipeline` | Get deal pipeline status from HubSpot |
| `schedule_followup` | Schedule a follow-up action for later |

## Endpoints

### MCP Info
```bash
curl https://web-production-a6ccf.up.railway.app/mcp/info
```

### List Tools
```bash
curl https://web-production-a6ccf.up.railway.app/mcp/tools
```

### WebSocket Connection
```
wss://web-production-a6ccf.up.railway.app/mcp/ws
```

### HTTP Message (for testing)
```bash
curl -X POST https://web-production-a6ccf.up.railway.app/mcp/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'
```

### Direct Tool Execution
```bash
curl -X POST https://web-production-a6ccf.up.railway.app/mcp/tools/read_command_queue \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

## Claude Desktop Setup

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "caseyos": {
      "command": "npx",
      "args": [
        "-y", 
        "@anthropics/mcp-remote",
        "wss://web-production-a6ccf.up.railway.app/mcp/ws"
      ]
    }
  }
}
```

Alternatively, use the HTTP transport:

```json
{
  "mcpServers": {
    "caseyos": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropics/mcp-remote", 
        "https://web-production-a6ccf.up.railway.app/mcp/message"
      ]
    }
  }
}
```

After configuration:
1. Restart Claude Desktop
2. Look for the 🔧 icon in the chat input area
3. CaseyOS tools should appear when you click it

## Example Usage in Claude

Once configured, you can ask Claude things like:

- "What's on my command queue for today?"
- "Search for contacts at Acme Corp"
- "Create a follow-up email draft for john@example.com about our proposal"
- "Show me the deal pipeline"
- "Schedule a follow-up with jane@company.com in 3 days"

## MCP Protocol Flow

```
Claude Desktop → WebSocket Connect → /mcp/ws
                                        ↓
                               initialize request
                                        ↓
                               tools/list request
                                        ↓
                               tools/call request
                                        ↓
                            CaseyOS executes tool
                                        ↓
                               Returns result
```

## Security Notes

- MCP endpoints are read-only by default for queue/notifications
- Execute actions require the kill switch to be OFF
- Dry-run mode available for safe testing
- All actions are logged via audit trail
