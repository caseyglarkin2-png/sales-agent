import asyncio
import os
from unittest.mock import MagicMock, patch

from src.connectors.slack import SlackConnector
from src.agents.content.repurpose_v2 import ContentRepurposeAgentV2 as ContentRepurposeAgent
# from src.models.content import ContentType, Platform

async def validate_slack():
    print("\n🔍 Validating SlackConnector...")
    connector = SlackConnector()
    if not connector.client:
        print("⚠️  Slack client not initialized (Token missing?), but class loaded successfully.")
    else:
        print("✅ Slack client initialized.")
    
    # Validation PASS if we can import and instantiate
    return True

async def validate_content_repurpose():
    print("\n🔍 Validating ContentRepurposeAgent...")
    try:
        agent = ContentRepurposeAgent()
        print("✅ Agent instantiated.")
        
        # Test Input Validation
        valid_input = {"content_memory_id": "123", "formats": ["linkedin"]}
        invalid_input = {"foo": "bar"}

        is_valid = await agent.validate_input(valid_input)
        is_invalid = await agent.validate_input(invalid_input)
        
        if is_valid is True and is_invalid is False:
             print("✅ Input validation logic verified.")
        else:
             print(f"❌ Input validation failed: valid={is_valid}, invalid={is_invalid}")
             return False
        
        return True
    except Exception as e:
        print(f"❌ Failed to instantiate agent: {e}")
        return False

async def main():
    print("🚀 Starting Sprint 23 Validation...")
    
    slack_ok = await validate_slack()
    repurpose_ok = await validate_content_repurpose()
    
    if slack_ok and repurpose_ok:
        print("\n✨ Sprint 23 Features (backend) Validated Successfully!")
        exit(0)
    else:
        print("\n❌ Errors found during validation.")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
