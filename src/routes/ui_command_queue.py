"""Minimal UI for Command Queue v0."""
from typing import List

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from src.db import get_db
from src.models.command_queue import CommandQueueItem

router = APIRouter(prefix="/ui", tags=["UI"])


@router.get("/command-queue", response_class=HTMLResponse)
async def command_queue_page(db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    stmt = select(CommandQueueItem).order_by(desc(CommandQueueItem.priority_score)).limit(10)
    result = await db.execute(stmt)
    items: List[CommandQueueItem] = result.scalars().all()

    rows = "".join(
        f"<tr><td>{i.priority_score:.1f}</td><td>{i.action_type}</td><td>{i.owner}</td><td>{i.status}</td><td>{i.due_by or ''}</td></tr>"
        for i in items
    )
    html = f"""
    <html>
      <head>
        <title>Today's Moves</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 2rem; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; }}
          th {{ background-color: #f2f2f2; }}
        </style>
      </head>
      <body>
        <h1>Today's Moves</h1>
        <table>
          <thead>
            <tr>
              <th>APS</th><th>Action</th><th>Owner</th><th>Status</th><th>Due By</th>
            </tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
      </body>
    </html>
    """
    return HTMLResponse(html)
