from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from db.firebase import db
from datetime import datetime

router = APIRouter(prefix="/profile", tags=["user-profile"])

class UserProfile(BaseModel):
    uid: str
    name: str
    college: str
    course: str
    academic_subjects: List[str]
    side_hustle_interests: List[str]
    onboarded: bool = True

class UserProfileResponse(BaseModel):
    uid: str
    name: str
    college: str
    course: str
    academic_subjects: List[str]
    side_hustle_interests: List[str]
    onboarded: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@router.post("/create", response_model=UserProfileResponse)
async def create_user_profile(profile: UserProfile):
    """
    Create or update user profile after onboarding
    """
    try:
        profile_data = profile.model_dump()
        profile_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Check if profile exists
        doc_ref = db.collection('user_profiles').document(profile.uid)
        doc = doc_ref.get()
        
        if doc.exists:
            # Update existing profile
            doc_ref.update(profile_data)
        else:
            # Create new profile
            profile_data['created_at'] = datetime.utcnow().isoformat()
            doc_ref.set(profile_data)
        
        # Fetch and return the created/updated profile
        updated_doc = doc_ref.get()
        return UserProfileResponse(**updated_doc.to_dict())
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")

@router.get("/{uid}", response_model=UserProfileResponse)
async def get_user_profile(uid: str):
    """
    Get user profile by UID
    """
    try:
        doc_ref = db.collection('user_profiles').document(uid)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return UserProfileResponse(**doc.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

@router.put("/{uid}", response_model=UserProfileResponse)
async def update_user_profile(uid: str, profile: UserProfile):
    """
    Update user profile
    """
    try:
        if uid != profile.uid:
            raise HTTPException(status_code=400, detail="UID mismatch")
        
        doc_ref = db.collection('user_profiles').document(uid)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile_data = profile.model_dump()
        profile_data['updated_at'] = datetime.utcnow().isoformat()
        
        doc_ref.update(profile_data)
        
        # Fetch and return the updated profile
        updated_doc = doc_ref.get()
        return UserProfileResponse(**updated_doc.to_dict())
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

@router.delete("/{uid}")
async def delete_user_profile(uid: str):
    """
    Delete user profile
    """
    try:
        doc_ref = db.collection('user_profiles').document(uid)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        doc_ref.delete()
        return {"message": f"Profile for user {uid} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete profile: {str(e)}")
