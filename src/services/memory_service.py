"""
Memory Service for Jarvis Persistent Memory.

This service provides the core memory operations that enable
Jarvis to remember conversations across sessions.

Key capabilities:
- remember(): Store messages with embeddings
- recall(): Get recent conversation history
- search_similar(): Semantic search for relevant context
- summarize_old(): Compress old messages into summaries
- forget(): Clear session memory (GDPR compliance)
"""

import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.memory import JarvisSession, ConversationMemory, MemorySummary
from src.connectors.llm import get_llm
from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)


class MemoryService:
    """
    Persistent memory service for Jarvis.
    
    Enables Henry-style memory where conversations persist
    across sessions and relevant context is recalled semantically.
    """
    
    # Configuration
    MAX_MESSAGES_PER_SESSION = 1000
    SUMMARIZE_AFTER_DAYS = 7
    MAX_RECALL_MESSAGES = 20
    EMBEDDING_MODEL = "text-embedding-3-small"
    
    def __init__(self, db_session: AsyncSession):
        """Initialize with database session."""
        self.db = db_session
        self.llm = get_llm()
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    async def get_or_create_session(
        self,
        user_id: str,
        session_name: str = "default"
    ) -> JarvisSession:
        """
        Get existing session or create new one.
        
        Args:
            user_id: User identifier
            session_name: Named session (e.g., "morning_standup", "deal_review")
            
        Returns:
            JarvisSession object
        """
        # Try to find existing active session
        result = await self.db.execute(
            select(JarvisSession).where(
                and_(
                    JarvisSession.user_id == user_id,
                    JarvisSession.session_name == session_name,
                    JarvisSession.is_active == True
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if session:
            # Update last active
            session.last_active = datetime.utcnow()
            await self.db.commit()
            return session
        
        # Create new session
        session = JarvisSession(
            user_id=user_id,
            session_name=session_name,
            active_context={},
            preferences={},
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        log_event("memory_session_created", user_id=user_id, session_name=session_name)
        logger.info(f"Created new Jarvis session for user {user_id}: {session_name}")
        
        return session
    
    async def list_sessions(
        self, 
        user_id: str, 
        include_inactive: bool = False
    ) -> List[JarvisSession]:
        """List all sessions for a user.
        
        Args:
            user_id: User identifier
            include_inactive: Whether to include inactive sessions
            
        Returns:
            List of JarvisSession objects
        """
        query = select(JarvisSession).where(JarvisSession.user_id == user_id)
        
        if not include_inactive:
            query = query.where(JarvisSession.is_active == True)
        
        result = await self.db.execute(
            query.order_by(desc(JarvisSession.last_active))
        )
        return list(result.scalars().all())
    
    async def update_session_context(
        self,
        session_id: str,
        context_updates: Dict[str, Any],
        current_focus: Optional[str] = None,
        last_topic: Optional[str] = None
    ) -> JarvisSession:
        """
        Update session's active context.
        
        Args:
            session_id: Session UUID
            context_updates: Dict of context keys to update
            current_focus: Optional new focus area
            last_topic: Optional topic for resume
        """
        result = await self.db.execute(
            select(JarvisSession).where(JarvisSession.id == uuid.UUID(session_id))
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Merge context updates
        current = session.active_context or {}
        current.update(context_updates)
        session.active_context = current
        
        if current_focus:
            session.current_focus = current_focus
        if last_topic:
            session.last_topic = last_topic
        
        session.last_active = datetime.utcnow()
        await self.db.commit()
        
        return session
    
    # =========================================================================
    # Memory Operations
    # =========================================================================
    
    async def remember(
        self,
        session_id: str,
        content: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
        importance: int = 50,
        generate_embedding: bool = True
    ) -> ConversationMemory:
        """
        Store a message in memory with optional embedding.
        
        Args:
            session_id: Session UUID
            content: Message content
            role: "user", "assistant", or "system"
            metadata: Optional metadata (agent used, action taken, etc.)
            importance: 0-100 importance score
            generate_embedding: Whether to generate embedding for semantic search
            
        Returns:
            ConversationMemory object
        """
        # Generate embedding if requested
        embedding = None
        if generate_embedding and self.llm:
            try:
                embedding = await self._generate_embedding(content)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
        
        # Estimate token count
        token_count = len(content.split()) * 1.3  # Rough estimate
        
        # Create memory record
        memory = ConversationMemory(
            session_id=uuid.UUID(session_id),
            role=role,
            content=content,
            embedding=embedding,
            message_metadata=metadata or {},
            importance=importance,
            token_count=int(token_count),
        )
        self.db.add(memory)
        
        # Update session message count
        result = await self.db.execute(
            select(JarvisSession).where(JarvisSession.id == uuid.UUID(session_id))
        )
        session = result.scalar_one_or_none()
        if session:
            session.message_count = (session.message_count or 0) + 1
            session.last_active = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(memory)
        
        log_event("memory_remember", session_id=session_id, role=role, importance=importance)
        
        return memory
    
    async def recall(
        self,
        session_id: str,
        limit: int = 20,
        min_importance: int = 0,
        include_system: bool = False
    ) -> List[ConversationMemory]:
        """
        Get recent conversation history.
        
        Args:
            session_id: Session UUID
            limit: Maximum messages to return
            min_importance: Minimum importance score
            include_system: Whether to include system messages
            
        Returns:
            List of ConversationMemory ordered by created_at DESC
        """
        query = select(ConversationMemory).where(
            and_(
                ConversationMemory.session_id == uuid.UUID(session_id),
                ConversationMemory.importance >= min_importance
            )
        )
        
        if not include_system:
            query = query.where(ConversationMemory.role != "system")
        
        query = query.order_by(desc(ConversationMemory.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        
        # Return in chronological order
        return list(reversed(messages))
    
    async def search_similar(
        self,
        session_id: str,
        query: str,
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[ConversationMemory]:
        """
        Semantic search for relevant past context.
        
        Uses cosine similarity on embeddings to find messages
        that are semantically related to the query.
        
        Args:
            session_id: Session UUID
            query: Query text to search for
            limit: Maximum results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of ConversationMemory sorted by relevance
        """
        # Generate query embedding
        query_embedding = await self._generate_embedding(query)
        if not query_embedding:
            # Fall back to keyword search
            return await self._keyword_search(session_id, query, limit)
        
        # Get all messages with embeddings for this session
        result = await self.db.execute(
            select(ConversationMemory).where(
                and_(
                    ConversationMemory.session_id == uuid.UUID(session_id),
                    ConversationMemory.embedding.isnot(None)
                )
            )
        )
        messages = list(result.scalars().all())
        
        # Calculate similarities
        similarities = []
        for msg in messages:
            if msg.embedding:
                similarity = self._cosine_similarity(query_embedding, msg.embedding)
                if similarity >= threshold:
                    similarities.append((msg, similarity))
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        log_event("memory_search", session_id=session_id, query_length=len(query), results=len(similarities[:limit]))
        
        return [msg for msg, _ in similarities[:limit]]
    
    async def _keyword_search(
        self,
        session_id: str,
        query: str,
        limit: int
    ) -> List[ConversationMemory]:
        """Fallback keyword search when embeddings aren't available."""
        # Simple ILIKE search
        result = await self.db.execute(
            select(ConversationMemory).where(
                and_(
                    ConversationMemory.session_id == uuid.UUID(session_id),
                    ConversationMemory.content.ilike(f"%{query}%")
                )
            ).order_by(desc(ConversationMemory.created_at)).limit(limit)
        )
        return list(result.scalars().all())
    
    # =========================================================================
    # Memory Maintenance
    # =========================================================================
    
    async def summarize_old_messages(
        self,
        session_id: str,
        older_than_days: int = 7
    ) -> Optional[MemorySummary]:
        """
        Compress old messages into a summary.
        
        This prevents memory bloat while preserving key context.
        
        Args:
            session_id: Session UUID
            older_than_days: Summarize messages older than this
            
        Returns:
            MemorySummary if created, None if nothing to summarize
        """
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        
        # Get old messages
        result = await self.db.execute(
            select(ConversationMemory).where(
                and_(
                    ConversationMemory.session_id == uuid.UUID(session_id),
                    ConversationMemory.created_at < cutoff
                )
            ).order_by(ConversationMemory.created_at)
        )
        old_messages = list(result.scalars().all())
        
        if len(old_messages) < 10:
            # Not enough to summarize
            return None
        
        # Generate summary using LLM
        conversation_text = "\n".join([
            f"{msg.role}: {msg.content}" for msg in old_messages
        ])
        
        summary_prompt = f"""Summarize this conversation into key facts and context.
Focus on:
1. Important decisions made
2. Preferences expressed
3. Key entities mentioned (people, companies, deals)
4. Ongoing tasks or projects

Conversation:
{conversation_text[:10000]}  # Limit to avoid token overflow

Provide:
1. A 2-3 sentence summary
2. A list of 5-10 key facts (JSON array of strings)
"""
        
        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=500
            )
            summary_text = response.get("content", "")
            
            # Parse key facts (simple extraction)
            key_facts = []
            if "[" in summary_text and "]" in summary_text:
                import json
                start = summary_text.find("[")
                end = summary_text.find("]") + 1
                try:
                    key_facts = json.loads(summary_text[start:end])
                except (json.JSONDecodeError, ValueError) as e:
                    logger.debug(f"Could not parse key facts from summary: {e}")
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            summary_text = f"Conversation from {old_messages[0].created_at.date()} to {old_messages[-1].created_at.date()}"
            key_facts = []
        
        # Create summary
        summary = MemorySummary(
            session_id=uuid.UUID(session_id),
            summary=summary_text,
            key_facts=key_facts,
            start_date=old_messages[0].created_at,
            end_date=old_messages[-1].created_at,
            message_count=len(old_messages),
        )
        self.db.add(summary)
        
        # Delete old messages
        for msg in old_messages:
            await self.db.delete(msg)
        
        await self.db.commit()
        await self.db.refresh(summary)
        
        log_event("memory_summarized", session_id=session_id, message_count=len(old_messages))
        logger.info(f"Summarized {len(old_messages)} messages for session {session_id}")
        
        return summary
    
    async def forget(
        self,
        session_id: str,
        before: Optional[datetime] = None
    ) -> int:
        """
        Clear session memory (GDPR compliance).
        
        Args:
            session_id: Session UUID
            before: Optional cutoff - delete messages before this time
            
        Returns:
            Number of messages deleted
        """
        query = select(ConversationMemory).where(
            ConversationMemory.session_id == uuid.UUID(session_id)
        )
        
        if before:
            query = query.where(ConversationMemory.created_at < before)
        
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        
        for msg in messages:
            await self.db.delete(msg)
        
        await self.db.commit()
        
        log_event("memory_forget", session_id=session_id, deleted=len(messages))
        logger.info(f"Deleted {len(messages)} messages from session {session_id}")
        
        return len(messages)
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get memory statistics for a session."""
        result = await self.db.execute(
            select(func.count(ConversationMemory.id)).where(
                ConversationMemory.session_id == uuid.UUID(session_id)
            )
        )
        message_count = result.scalar() or 0
        
        result = await self.db.execute(
            select(func.sum(ConversationMemory.token_count)).where(
                ConversationMemory.session_id == uuid.UUID(session_id)
            )
        )
        token_count = result.scalar() or 0
        
        result = await self.db.execute(
            select(func.count(MemorySummary.id)).where(
                MemorySummary.session_id == uuid.UUID(session_id)
            )
        )
        summary_count = result.scalar() or 0
        
        return {
            "session_id": session_id,
            "message_count": message_count,
            "estimated_tokens": token_count,
            "summary_count": summary_count,
            "max_messages": self.MAX_MESSAGES_PER_SESSION,
            "utilization": message_count / self.MAX_MESSAGES_PER_SESSION,
        }
    
    # =========================================================================
    # Embedding Helpers
    # =========================================================================
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI."""
        if not self.llm:
            return None
        
        try:
            # Use LLM connector's embedding method if available
            if hasattr(self.llm, 'create_embedding'):
                return await self.llm.create_embedding(text)
            
            # Fallback: Use OpenAI directly
            from openai import AsyncOpenAI
            import os
            
            client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            response = await client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text[:8000]  # Limit input size
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)


# Convenience function for getting memory service
async def get_memory_service(db: AsyncSession) -> MemoryService:
    """Get memory service instance."""
    return MemoryService(db)
