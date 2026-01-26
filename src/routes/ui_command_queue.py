# DEPRECATED IN SPRINT 24
# Replaced by src/templates/queue.html served via src/routes/ui.py
# 
# from fastapi import APIRouter
# from fastapi.responses import HTMLResponse
#
# router = APIRouter(prefix="/ui", tags=["UI"])
# 
# @router.get("/command-queue", response_class=HTMLResponse)
# async def command_queue_page():
#     return HTMLResponse("Deprecated. Go to /caseyos/queue")
