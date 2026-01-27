from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Initialize router
router = APIRouter(tags=["UI"])

# Initialize templates
# Ensure the directory matches where you created the templates folder
templates = Jinja2Templates(directory="src/templates")

@router.get("/caseyos/queue", response_class=HTMLResponse)
async def queue_dashboard(request: Request):
    """
    Renders the Command Queue using the new Jinja2 template.
    """
    return templates.TemplateResponse("queue.html", {"request": request, "active_tab": "queue"})

@router.get("/caseyos", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Main Dashboard (formerly Jarvis)
    """
    return templates.TemplateResponse("dashboard.html", {"request": request, "active_tab": "dashboard"})


@router.get("/caseyos/gemini", response_class=HTMLResponse)
async def gemini_portal(request: Request):
    """
    Gemini AI Portal - Sprint 34
    Interactive chat with Gemini AI, model selection, grounding support.
    """
    return templates.TemplateResponse("gemini.html", {"request": request, "active_tab": "gemini"})


@router.get("/caseyos/drive", response_class=HTMLResponse)
async def drive_browser(request: Request):
    """
    Google Drive Browser - Sprint 35
    Browse and search Google Drive files.
    """
    return templates.TemplateResponse("drive.html", {"request": request, "active_tab": "drive"})
