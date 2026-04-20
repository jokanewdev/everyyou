from fastapi import FastAPI, BackgroundTasks, HTTPException
from backend.downloader import analyze_media, download_task, PROGRESS_STORE
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os

DOWNLOAD_DIR = "/tmp/downloads" 
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
app = FastAPI(title="EveryYou API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_id: str

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        data = analyze_media(req.url)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao analisar URL: {str(e)}")

@app.post("/api/download")
async def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    PROGRESS_STORE[task_id] = {
        "status": "downloading",
        "percent": 0,
        "speed": "Calculando...",
        "eta": "Calculando...",
        "filepath": None
    }
    
    background_tasks.add_task(download_task, task_id, req.url, req.format_id)
    return {"task_id": task_id}

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    if task_id not in PROGRESS_STORE:
        raise HTTPException(status_code=404, detail="Task não encontrada")
    return PROGRESS_STORE[task_id]

def delete_file(filepath: str):
    try:
        os.remove(filepath)
    except:
        pass

@app.get("/api/file/{task_id}")
async def get_file(task_id: str, background_tasks: BackgroundTasks):
    task_data = PROGRESS_STORE.get(task_id)
    if not task_data or task_data['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Arquivo não está pronto ou houve falha")
    
    filepath = task_data['filepath']
    filename = os.path.basename(filepath)
    
    # Remove o arquivo do servidor logo após ser enviado para economizar espaço
    background_tasks.add_task(delete_file, filepath)
    
    return FileResponse(path=filepath, filename=filename, media_type='application/octet-stream')

# Monta o frontend estático para a raiz
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")