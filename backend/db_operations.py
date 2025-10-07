from supabase_client import get_supabase_client
from datetime import datetime
from typing import Optional, Dict, Any

supabase = get_supabase_client()

class DBOperations:
    
    @staticmethod
    def create_or_get_user(user_id: str) -> Dict[str, Any]:
        """Create user if doesn't exist, return user data"""
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        
        if not result.data:
            result = supabase.table("users").insert({"user_id": user_id}).execute()
        
        return result.data[0] if result.data else None
    
    @staticmethod
    def save_document(user_id: str, filename: str, file_path: str, 
                      doc_type: str, file_size: int, ip_address: str) -> Dict[str, Any]:
        """Save document metadata to database"""
        data = {
            "user_id": user_id,
            "filename": filename,
            "file_path": file_path,
            "document_type": doc_type,
            "file_size": file_size,
            "ip_address": ip_address
        }
        result = supabase.table("documents").insert(data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def create_meeting(user_id: str, room_id: str, ip_address: str) -> Dict[str, Any]:
        """Create meeting record"""
        data = {
            "user_id": user_id,
            "room_id": room_id,
            "ip_address": ip_address
        }
        result = supabase.table("meetings").insert(data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def save_frame(meeting_id: str, user_id: str, 
                   filename: str, file_path: str) -> Dict[str, Any]:
        """Save captured frame metadata"""
        data = {
            "meeting_id": meeting_id,
            "user_id": user_id,
            "filename": filename,
            "file_path": file_path
        }
        result = supabase.table("frames").insert(data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def log_audit(user_id: str, action: str, details: Dict, ip_address: str):
        """Log audit event"""
        data = {
            "user_id": user_id,
            "action": action,
            "details": details,
            "ip_address": ip_address
        }
        supabase.table("audit_logs").insert(data).execute()
    
    @staticmethod
    def check_user_has_documents(user_id: str) -> bool:
        """Check if user has uploaded any documents"""
        result = supabase.table("documents").select("id").eq("user_id", user_id).execute()
        return len(result.data) > 0
    
    @staticmethod
    def get_user_documents(user_id: str):
        """Get all documents for a user"""
        result = supabase.table("documents").select("*").eq("user_id", user_id).execute()
        return result.data