# backend/main.py
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from db_operations import DBOperations
from supabase_client import get_supabase_client
from datetime import datetime
import os

app = FastAPI(title="Video KYC Backend")
supabase = get_supabase_client()
db = DBOperations()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Video KYC Backend is running!", "status": "active"}


@app.post("/upload_document")
async def upload_document(file: UploadFile = File(...), request: Request = None):
    """Upload KYC document (Aadhaar/PAN/PDF)"""
    
    # Get user_id from query params
    user_id = request.query_params.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, PDF allowed")
    
    try:
        # Ensure user exists in database
        db.create_or_get_user(user_id)
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Determine document type
        if file.content_type == "application/pdf":
            doc_type = "pdf"
        elif "aadhaar" in file.filename.lower():
            doc_type = "aadhaar"
        elif "pan" in file.filename.lower():
            doc_type = "pan"
        else:
            doc_type = "image"
        
        # Create unique storage path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        storage_path = f"{user_id}/{timestamp}_{file.filename}"
        
        # Upload to Supabase Storage
        supabase.storage.from_("kyc-documents").upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL (for preview)
        file_url = supabase.storage.from_("kyc-documents").get_public_url(storage_path)
        
        # Save metadata to database
        ip_address = get_client_ip(request)
        doc_record = db.save_document(
            user_id=user_id,
            filename=file.filename,
            file_path=storage_path,
            doc_type=doc_type,
            file_size=file_size,
            ip_address=ip_address
        )
        
        # Log audit event
        db.log_audit(
            user_id=user_id,
            action="DOCUMENT_UPLOAD",
            details={
                "filename": file.filename,
                "type": doc_type,
                "size": file_size
            },
            ip_address=ip_address
        )
        
        return {
            "message": "Document uploaded successfully",
            "filename": file.filename,
            "url": file_url,
            "document_id": doc_record["id"],
            "document_type": doc_type
        }
    
    except Exception as e:
        print(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/create_meeting")
async def create_meeting(user_id: str, request: Request):
    """Create Jitsi meeting room"""
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    try:
        # Check if user has uploaded documents
        has_docs = db.check_user_has_documents(user_id)
        if not has_docs:
            raise HTTPException(
                status_code=403, 
                detail="Please upload a document before starting the meeting"
            )
        
        # Create unique room ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        room_id = f"kyc_{user_id}_{timestamp}"
        
        # Save meeting to database
        ip_address = get_client_ip(request)
        meeting = db.create_meeting(user_id, room_id, ip_address)
        
        # Log audit event
        db.log_audit(
            user_id=user_id,
            action="MEETING_CREATED",
            details={"room_id": room_id},
            ip_address=ip_address
        )
        
        return {
            "room": room_id,
            "domain": "meet.jit.si",
            "token": None,  # Can add JWT token later for security
            "meeting_id": meeting["id"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Meeting creation failed: {str(e)}")


@app.post("/analyze_frame")
async def analyze_frame(file: UploadFile = File(...), request: Request = None):
    """Capture and store video frame from meeting"""
    
    # Get meeting_id and user_id from query params
    meeting_id = request.query_params.get("meeting_id")
    user_id = request.query_params.get("user_id")
    
    if not meeting_id or not user_id:
        raise HTTPException(status_code=400, detail="meeting_id and user_id are required")
    
    try:
        # Read frame content
        frame_content = await file.read()
        
        # Create storage path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        storage_path = f"{user_id}/{meeting_id}/{timestamp}_frame.png"
        
        # Upload to Supabase Storage
        supabase.storage.from_("kyc-frames").upload(
            path=storage_path,
            file=frame_content,
            file_options={"content-type": "image/png"}
        )
        
        # Get public URL
        frame_url = supabase.storage.from_("kyc-frames").get_public_url(storage_path)
        
        # Save frame metadata to database
        frame_record = db.save_frame(
            meeting_id=meeting_id,
            user_id=user_id,
            filename=f"{timestamp}_frame.png",
            file_path=storage_path
        )
        
        # Log audit event
        ip_address = get_client_ip(request)
        db.log_audit(
            user_id=user_id,
            action="FRAME_CAPTURE",
            details={
                "meeting_id": meeting_id,
                "filename": f"{timestamp}_frame.png"
            },
            ip_address=ip_address
        )
        
        return {
            "message": "Frame captured successfully",
            "filename": f"{timestamp}_frame.png",
            "url": frame_url,
            "frame_id": frame_record["id"]
        }
    
    except Exception as e:
        print(f"Error capturing frame: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Frame capture failed: {str(e)}")


@app.get("/user/{user_id}/documents")
async def get_user_documents(user_id: str):
    """Get all documents uploaded by a user"""
    try:
        documents = db.get_user_documents(user_id)
        return {"user_id": user_id, "documents": documents, "count": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Detailed health check with database connectivity"""
    try:
        # Test database connection
        result = supabase.table("users").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)