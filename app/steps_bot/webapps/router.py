import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse

router = APIRouter()

webapps_dir = os.path.dirname(__file__)

@router.get("/map", response_class=HTMLResponse)
async def map_page():
    with open(os.path.join(webapps_dir, "map.html"), encoding="utf-8") as f:
        return f.read()


@router.get("/map.js")
async def map_js():
    return FileResponse(os.path.join(webapps_dir, "map.js"), media_type="application/javascript")


@router.get("/map.css")
async def map_css():
    return FileResponse(os.path.join(webapps_dir, "map.css"), media_type="text/css")


def mount_static(app: FastAPI):
    static_path = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_path), name="static")