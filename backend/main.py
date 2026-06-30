from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from backend.ingest import ingest_md, delete_subject, list_subjects
from backend.rag import query_rag
import tempfile
import os
import shutil

app = FastAPI(title="Academic Slides Q&A")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []


# ── Frontend static files ─────────────────────────────────────────────────────

@app.get("/")
def serve_index():
    return FileResponse("frontend/index.html")

@app.get("/style.css")
def serve_css():
    return FileResponse("frontend/style.css", media_type="text/css")

@app.get("/app.js")
def serve_js():
    return FileResponse("frontend/app.js", media_type="application/javascript")


# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/materials")
def get_materials():
    subjects = list_subjects()
    return {"subjects": subjects}


@app.post("/ingest/{subject}")
async def upload_material(subject: str, file: UploadFile = File(...)):
    if not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are accepted.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        count = ingest_md(tmp_path, subject)
    finally:
        os.unlink(tmp_path)
    return {"status": "success", "subject": subject, "filename": file.filename, "chunks": count}


@app.post("/chat/{subject}")
async def chat(subject: str, req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    subjects = list_subjects()
    if subject not in subjects:
        raise HTTPException(status_code=404, detail=f"Subject '{subject}' not found.")
    answer = query_rag(subject, req.question, req.history)
    return {"answer": answer}


@app.delete("/materials/{subject}")
def remove_material(subject: str):
    success = delete_subject(subject)
    if not success:
        raise HTTPException(status_code=404, detail=f"Subject '{subject}' not found.")
    return {"status": "deleted", "subject": subject}