---
name: askJarvis
description: Query CaseyOS through the Jarvis master orchestrator
---
Write code to query CaseyOS through Jarvis for the following:

## Query
${1:What would you like to ask Jarvis?}

## Implementation

```python
import asyncio
from src.agents.jarvis import get_jarvis

async def query_jarvis():
    jarvis = get_jarvis()
    
    # Natural language query
    result = await jarvis.ask("${query}")
    
    print(f"Status: {result.get('status')}")
    print(f"Response: {result.get('response')}")
    
    if result.get('agents_consulted'):
        print(f"Agents: {result['agents_consulted']}")
    
    return result

if __name__ == "__main__":
    asyncio.run(query_jarvis())
```

## Available Domains

| Domain | Agents | Example Queries |
|--------|--------|-----------------|
| **sales** | Prospecting, Nurturing, Research | "Research Acme Corp" |
| **content** | Repurpose, Social, Graphics | "Turn this into a LinkedIn post" |
| **fulfillment** | Deliverables, Approvals, Health | "What deliverables are at risk?" |
| **contracts** | Proposals, Reviews, Pricing | "Generate a proposal for Enterprise" |
| **ops** | Competitor, Revenue, Partners | "How's pipeline health?" |

## Direct Domain Routing

```python
result = await jarvis.execute({
    "action": "route",
    "domain": "ops",
    "agent": "revenue_ops",
    "context": {"action": "pipeline_health"}
})
```
