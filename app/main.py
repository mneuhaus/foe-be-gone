"""
FastAPI application for Foe Be Gone - Wildlife Detection & Deterrent System
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Initialize FastAPI app
app = FastAPI(
    title="Foe Be Gone",
    description="AI-powered wildlife detection and deterrent system",
    version="2.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/public", StaticFiles(directory="public"), name="public")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with dashboard overview"""
    context = {
        "request": request,
        "title": "Foe Be Gone",
        "page": "home"
    }
    return templates.TemplateResponse(request, "home.html", context)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)