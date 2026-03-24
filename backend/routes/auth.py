from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from firebase_admin import auth
from typing import Optional

router = APIRouter(prefix="/auth", tags=["authentication"])

class GoogleAuthRequest(BaseModel):
    id_token: str

class UserResponse(BaseModel):
    uid: str
    email: Optional[str]
    display_name: Optional[str]
    photo_url: Optional[str]

@router.post("/google/verify", response_model=UserResponse)
async def verify_google_token(request: GoogleAuthRequest):
    """
    Verify Google ID token and return user information
    """
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(request.id_token)
        uid = decoded_token['uid']
        
        # Get user information
        user = auth.get_user(uid)
        
        return UserResponse(
            uid=user.uid,
            email=user.email,
            display_name=user.display_name,
            photo_url=user.photo_url
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.get("/user/{uid}")
async def get_user_info(uid: str):
    """
    Get user information by UID
    """
    try:
        user = auth.get_user(uid)
        return UserResponse(
            uid=user.uid,
            email=user.email,
            display_name=user.display_name,
            photo_url=user.photo_url
        )
    except auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")

@router.delete("/user/{uid}")
async def delete_user(uid: str):
    """
    Delete a user account
    """
    try:
        auth.delete_user(uid)
        return {"message": f"User {uid} deleted successfully"}
    except auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")
