# ~/video-kyc/backend/main.py
from fastapi import FastAPI, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
import os
import shutil

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev, restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folders
FRAME_DIR = "frames"
DOC_DIR = "documents"
os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(DOC_DIR, exist_ok=True)

# Serve uploaded documents & frames
app.mount("/frames", StaticFiles(directory=FRAME_DIR), name="frames")
app.mount("/documents", StaticFiles(directory=DOC_DIR), name="documents")

@app.get("/")
def root():
    return {"message": "Hello, KYC backend is running!"}

@app.post("/create_meeting")
def create_meeting(user_id: str = Query(...)):
    """Create a Jitsi room for the given user_id"""
    room = f"kyc_{user_id}_{int(time.time())}"
    return {"room": room, "token": None, "domain": "meet.jit.si"}

@app.post("/analyze_frame")
async def analyze_frame(file: UploadFile = File(...)):
    """Receive a captured frame and save it"""
    timestamp = int(time.time())
    filename = f"frame_{timestamp}.png"
    path = os.path.join(FRAME_DIR, filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    return JSONResponse({"message": f"Frame saved as {filename}", "filename": f"frames/{filename}"})

@app.post("/upload_document")
async def upload_document(file: UploadFile = File(...)):
    """Upload and save Aadhaar/PAN/any KYC document"""
    timestamp = int(time.time())
    filename = f"doc_{timestamp}_{file.filename}"
    path = os.path.join(DOC_DIR, filename)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return JSONResponse({"message": f"Document saved as {filename}", "filename": f"documents/{filename}"})
