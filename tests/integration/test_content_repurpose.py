import pytest
import os
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy import delete

from src.main import app
from src.db import get_session
from src.models.content import ContentMemory, ContentSourceType

client = TestClient(app)

# Skip if no database configured or in CI without DB
pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DB_TESTS", "false").lower() == "true" or 
    not os.environ.get("DATABASE_URL"),
    reason="Database tests require DATABASE_URL and running PostgreSQL"
)

@pytest.mark.asyncio
async def test_repurpose_api_flow():
    # 1. Seed Data
    content_id = str(uuid4())
    async with get_session() as session:
        # Check if table exists (it should if migrations ran)
        cm = ContentMemory(
            id=content_id,
            source_type=ContentSourceType.YOUTUBE.value,
            source_id="VIDEO_123",
            content="This is a transcript of a video about Sales AI. It is very important to use AI agents.",
            title="Test Video",
            content_metadata={"author": "Casey"}
        )
        session.add(cm)
        await session.commit()

    try:
        # 2. Mock LLM
        # We patch where the class is IMPORTED in the route or agent
        # The route imports LLMConnector from src.connectors.llm
        # The agent imports it too. Ideally we pass it in.
        # In the route: agent = ContentRepurposeAgent(llm_connector=llm)
        # So we patch src.routes.content_repurpose.LLMConnector
        
        with patch("src.routes.content_repurpose.LLMConnector") as MockLLM:
            mock_instance = MockLLM.return_value
            # Make generate_text async
            async def mock_generate(*args, **kwargs):
                return "🚀 AI Agents are the future! #SalesAI ---POST--- 🤖 distinct post 2"
            
            mock_instance.generate_text.side_effect = mock_generate
            
            # 3. Call API
            response = client.post(
                "/api/content/repurpose/",
                json={
                    "content_memory_id": content_id,
                    "formats": ["linkedin"],
                    "tone": "exciting"
                }
            )

            # Debug output if fail
            if response.status_code != 200:
                print(f"API Error: {response.text}")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "linkedin" in data["outputs"]
            items = data["outputs"]["linkedin"]["items"]
            assert len(items) >= 1
            assert "AI Agents" in items[0]

    finally:
        # Cleanup
        async with get_session() as session:
            await session.execute(
                delete(ContentMemory).where(ContentMemory.id == content_id)
            )
            await session.commit()
