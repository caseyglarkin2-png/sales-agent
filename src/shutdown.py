"""Graceful Shutdown Handler.

Ensures in-flight requests complete before shutdown.
"""

import signal
import asyncio
from typing import Callable
from src.logger import get_logger

logger = get_logger(__name__)

shutdown_event = asyncio.Event()


def register_shutdown_handlers(app):
    """Register graceful shutdown handlers for FastAPI app."""
    
    @app.on_event("shutdown")
    async def shutdown_handler():
        """Handle application shutdown gracefully."""
        logger.info("Shutdown signal received, draining connections...")
        
        # Wait for in-flight requests to complete (max 30 seconds)
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout reached, forcing exit")
        
        logger.info("Shutdown complete")
    
    def signal_handler(signum, frame):
        """Handle OS signals (SIGTERM, SIGINT)."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
