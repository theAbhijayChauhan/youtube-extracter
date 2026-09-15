import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import (
    APP_TITLE,
    APP_DESCRIPTION,
    APP_VERSION,
    STATIC_DIR,
    TEMPLATES_DIR,
)
from app.routes.info import router as info_router
from app.routes.download import router as download_router
from app.routes.health import router as health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("yt_converter.main")

# Initialize FastAPI App
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Disposition", "Content-Type"],
)

# Static & Templates Mount
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API Routers
app.include_router(info_router)
app.include_router(download_router)
app.include_router(health_router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render home page with complete SEO metadata and schema tags."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_title": APP_TITLE,
            "app_description": APP_DESCRIPTION,
            "app_version": APP_VERSION,
        }
    )

@app.get("/robots.txt", response_class=HTMLResponse)
async def robots_txt():
    """SEO robots.txt file."""
    content = "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"
    return HTMLResponse(content=content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap_xml(request: Request):
    """SEO XML Sitemap."""
    base_url = str(request.base_url).rstrip("/")
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return HTMLResponse(content=xml_content, media_type="application/xml")
