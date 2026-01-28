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


@router.get("/caseyos/queue/{item_id}", response_class=HTMLResponse)
async def queue_item_detail(request: Request, item_id: str):
    """
    Queue Item Detail Page - Sprint 40
    Shows full item details with draft editing capability.
    """
    return templates.TemplateResponse("queue_detail.html", {
        "request": request, 
        "active_tab": "queue",
        "item_id": item_id,
    })

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


@router.get("/caseyos/agents", response_class=HTMLResponse)
async def agents_hub(request: Request):
    """
    Agent Hub - Sprint 39A
    Shows all 38 specialized agents organized by category.
    Full functionality coming in Sprint 41.
    """
    return templates.TemplateResponse("agents.html", {"request": request, "active_tab": "agents"})


@router.get("/caseyos/executions", response_class=HTMLResponse)
async def executions_history(request: Request):
    """
    Execution History - Sprint 42
    Shows agent execution history with status, duration, and results.
    """
    return templates.TemplateResponse("executions.html", {"request": request, "active_tab": "executions"})


@router.get("/caseyos/signals", response_class=HTMLResponse)
async def signals_stream(request: Request):
    """
    Signals Stream - Sprint 8 UI
    Shows real-time signal ingestion from forms, HubSpot, Gmail.
    """
    return templates.TemplateResponse("signals.html", {"request": request, "active_tab": "signals"})


@router.get("/caseyos/overview", response_class=HTMLResponse)
async def overview_dashboard(request: Request):
    """
    Overview Dashboard - Sprint 43.5
    Real-time stats bar, pipeline health, agent performance, activity feed.
    """
    return templates.TemplateResponse("overview.html", {"request": request, "active_tab": "overview"})
