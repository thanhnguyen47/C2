from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from config import templates

router = APIRouter()    
@router.get("/admin/dashboard")
async def get_dashboard(request: Request):
    return templates.TemplateResponse("admin/admin_dashboard.html", context={"request": request, "active_page": "dashboard"})