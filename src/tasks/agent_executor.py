"""
Agent Executor Celery Task.

Sprint 42.4: Async execution of agents with tracking.

Provides background execution of any registered agent with
full tracking via the ExecutionService.
"""

import asyncio
import importlib
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)


def _run_async(coro):
    """Run async coroutine in sync context for Celery."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new loop if current one is running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _execute_agent_async(
    execution_id: int,
    agent_class_name: str,
    module_path: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Async implementation of agent execution.
    
    Args:
        execution_id: ID of the execution record
        agent_class_name: Class name of the agent to execute
        module_path: Python module path for the agent
        context: Execution context/payload
        
    Returns:
        Execution result dictionary
    """
    from src.db import get_session
    from src.services.execution_service import ExecutionService
    
    async with get_session() as db:
        service = ExecutionService(db)
        
        try:
            # Import and instantiate the agent
            module = importlib.import_module(module_path)
            agent_class = getattr(module, agent_class_name)
            agent = agent_class()
            
            # Validate input if method exists
            if hasattr(agent, 'validate_input'):
                is_valid = await agent.validate_input(context)
                if not is_valid:
                    raise ValueError(f"Invalid input context for {agent_class_name}")
            
            # Execute the agent
            logger.info(f"Executing agent {agent_class_name} for execution {execution_id}")
            result = await agent.execute(context)
            
            # Mark as successful
            await service.complete_execution(execution_id, result)
            
            log_event(
                "celery_agent_execution_success",
                execution_id=execution_id,
                agent_name=agent_class_name,
            )
            
            return {
                "status": "success",
                "execution_id": execution_id,
                "result": result,
            }
            
        except SoftTimeLimitExceeded:
            # Handle timeout
            logger.warning(f"Agent {agent_class_name} timed out for execution {execution_id}")
            await service.timeout_execution(execution_id)
            
            log_event(
                "celery_agent_execution_timeout",
                execution_id=execution_id,
                agent_name=agent_class_name,
            )
            
            return {
                "status": "timed_out",
                "execution_id": execution_id,
                "error": "Agent execution timed out",
            }
            
        except Exception as e:
            # Handle failure
            error_msg = str(e)
            error_tb = traceback.format_exc()
            
            logger.error(f"Agent {agent_class_name} failed for execution {execution_id}: {error_msg}")
            await service.fail_execution(execution_id, error_msg, error_tb)
            
            log_event(
                "celery_agent_execution_failed",
                execution_id=execution_id,
                agent_name=agent_class_name,
                error=error_msg,
            )
            
            return {
                "status": "failed",
                "execution_id": execution_id,
                "error": error_msg,
                "traceback": error_tb,
            }


@shared_task(
    name="src.tasks.agent_executor.execute_agent",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 0},  # Don't auto-retry agents, let service handle it
    soft_time_limit=300,  # 5 minutes soft limit
    time_limit=360,  # 6 minutes hard limit
)
def execute_agent(
    self,
    execution_id: int,
    agent_class_name: str,
    module_path: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute an agent asynchronously.
    
    This task is triggered when an agent needs to run in the background.
    It tracks execution via the ExecutionService.
    
    Args:
        execution_id: ID of the execution record (already created)
        agent_class_name: Class name of the agent to execute
        module_path: Python module path for the agent
        context: Execution context/payload
        
    Returns:
        Execution result dictionary
    """
    logger.info(
        f"Celery task started: executing {agent_class_name} "
        f"(execution_id={execution_id}, task_id={self.request.id})"
    )
    
    # Update execution with celery task ID
    try:
        _update_celery_task_id(execution_id, self.request.id)
    except Exception as e:
        logger.warning(f"Failed to update celery_task_id: {e}")
    
    return _run_async(
        _execute_agent_async(execution_id, agent_class_name, module_path, context)
    )


def _update_celery_task_id(execution_id: int, task_id: str):
    """Update execution record with Celery task ID."""
    _run_async(_update_celery_task_id_async(execution_id, task_id))


async def _update_celery_task_id_async(execution_id: int, task_id: str):
    """Async implementation to update celery task ID."""
    from src.db import get_session
    from src.models.agent_execution import AgentExecution
    from sqlalchemy import update
    
    async with get_session() as db:
        await db.execute(
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(celery_task_id=task_id)
        )
        await db.commit()


def queue_agent_execution(
    execution_id: int,
    agent_class_name: str,
    module_path: str,
    context: Dict[str, Any],
) -> str:
    """
    Queue an agent for async execution.
    
    This is the main entry point for triggering async agent execution.
    
    Args:
        execution_id: ID of the execution record (must already exist)
        agent_class_name: Class name of the agent
        module_path: Python module path for the agent
        context: Execution context
        
    Returns:
        Celery task ID
    """
    task = execute_agent.delay(
        execution_id=execution_id,
        agent_class_name=agent_class_name,
        module_path=module_path,
        context=context,
    )
    
    logger.info(f"Queued agent execution: {agent_class_name} -> task {task.id}")
    return task.id
