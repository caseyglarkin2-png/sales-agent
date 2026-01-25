from typing import Dict, Any, List
from sqlalchemy import select, or_

from src.agents.base import BaseAgent
from src.connectors.drive import DriveConnector
from src.connectors.gemini import GeminiConnector
from src.logger import get_logger
from src.db import get_session
from src.models.content import ContentMemory

logger = get_logger(__name__)

class DeepResearchAgent(BaseAgent):
    """
    Agent for deep research using Google Drive 'treasure troves', Internal DB, and Gemini 1.5 Pro.
    
    Capabilities:
    1. Search specific Drive folders (Pesti, Yardflow, Dude).
    2. Search internal ContentMemory (Slack history, YouTube transcripts).
    3. Analyze massive context logic with Gemini 1.5 Pro.
    """
    
    def __init__(self):
        super().__init__(
            name="Deep Research Agent",
            description="Performs deep research on internal Drive documents using Gemini 1.5 Pro."
        )
        self.drive = DriveConnector()
        self.gemini = GeminiConnector()
        
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Required: query. Optional: folder (pesti|yardflow|dude|all)."""
        return "query" in context
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query")
        folder_alias = context.get("folder", "all").lower()
        max_files = context.get("max_files", 5)
        
        logger.info(f"Deep Research starting: query='{query}', folder='{folder_alias}'")
        
        # 1. Map folder alias to search query/config
        # Note: DriveConnector handles the allowlisted folders. 
        # We can pass specific company names to narrow it down if needed.
        company_filter = None
        if folder_alias in ["pesti", "pesti_sales"]:
            company_filter = "pesti"
        elif folder_alias in ["yardflow", "freightroll"]:
            company_filter = "yardflow" # Might need to add this to DriveConnector config later if not present
            
        # 2. Search Drive Assets
        assets = await self.drive.search_assets(
            query=query, # Use the query key terms as search
            company_name=company_filter, # This maps to filtering inside connector if logic exists
            max_results=max_files
        )
            
        # 3. Build Knowledge Context
        knowledge_block = []
        sources = []
        
        # 3a. From Drive
        if assets:
            for asset in assets:
                file_id = asset["id"]
                name = asset["name"]
                link = asset["link"]
                
                content = await self.drive.get_file_content(file_id)
                if content and not content.startswith("["): # Skip binary/errors
                    knowledge_block.append(f"--- DOCUMENT: {name} ---\n{content}\n")
                    sources.append({"name": name, "link": link})
                else:
                    logger.warning(f"Skipped file {name} (no text content)")
        
        # 3b. From ContentMemory (Slack/YouTube)
        try:
            async with get_session() as session:
                # Simple keyword search on content or title
                stmt = select(ContentMemory).where(
                    or_(
                        ContentMemory.content.ilike(f"%{query}%"),
                        ContentMemory.title.ilike(f"%{query}%")
                    )
                ).limit(5)
                
                result = await session.execute(stmt)
                db_items = result.scalars().all()
                
                if db_items:
                    logger.info(f"Found {len(db_items)} items in ContentMemory matching '{query}'")
                    for item in db_items:
                        snippet = item.content[:25000] # Limit char count per item
                        knowledge_block.append(f"--- INTERNAL MEMORY ({item.source_type.upper()}): {item.title} ---\n{snippet}\n")
                        sources.append({"name": f"[{item.source_type}] {item.title}", "link": item.source_url})
        except Exception as e:
            logger.error(f"Error searching ContentMemory: {e}")
                 
        if not knowledge_block:
             return {
                "result": "Found documents but could not extract text (likely PDFs not yet supported).",
                "sources": [s["name"] for s in sources] # Just names
            }
            
        full_context = "\n".join(knowledge_block)
        
        # 4. Analyze with Gemini 1.5 Pro
        logger.info(f"Sending {len(full_context)} chars to Gemini 1.5 Pro...")
        analysis = await self.gemini.analyze_context(full_context, query)
        
        return {
            "result": analysis,
            "sources": sources,
            "stats": {
                "files_read": len(sources),
                "context_chars": len(full_context)
            }
        }
