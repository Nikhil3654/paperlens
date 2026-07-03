from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.paper_service import PaperLensService
from api.schemas import SearchRequest


app = FastAPI(title="PaperLens API")

service = PaperLensService()

app.mount("/static", StaticFiles(directory="web"), name="static")


@app.on_event("startup")
def startup():
    service.build_sample_index()


@app.get("/")
def home():
    return FileResponse(Path("web") / "index.html")


@app.get("/api/health")
def health():
    return service.stats()


@app.get("/api/papers")
def papers():
    return {
        "papers": service.papers(),
    }


@app.post("/api/search")
def search(request: SearchRequest):
    return service.search(
        question=request.question,
        paper_titles=request.paper_titles,
        search_mode=request.search_mode,
    )


@app.get("/api/benchmark")
def benchmark():
    return {
        "questions": 15,
        "top1_paper_routing": 1.0,
        "top5_paper_routing": 1.0,
        "strict_page_hit_rate": 0.867,
    }