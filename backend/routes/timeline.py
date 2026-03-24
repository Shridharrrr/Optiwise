from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from datetime import datetime, timedelta
from typing import List, Dict

router = APIRouter(prefix="/timeline", tags=["timeline"])
db = firestore.client()

@router.get("/events/{uid}")
async def get_timeline_events(uid: str, mode: str = "academic"):
    """
    Get AI agent timeline events based on user activity and agent decisions
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        profile_doc = user_ref.get()
        
        if not profile_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        events = []
        event_id = 1
        
        # Fetch Logged Events
        # Optimization: Filter by mode in-memory to avoid Firestore Composite Index requirement
        events_ref = user_ref.collection("timeline_events").order_by("created_at", direction=firestore.Query.DESCENDING).limit(50)
        
        try:
             stream = events_ref.stream()
             for doc in stream:
                 data = doc.to_dict()
                 
                 # Manual Filter
                 if data.get('mode') != mode:
                     continue
                 
                 created_at = data.get('created_at')
                 
                 # Handle timestamp
                 if not created_at:
                      created_at = datetime.now()
                 elif hasattr(created_at, 'timestamp'):
                      created_at = datetime.fromtimestamp(created_at.timestamp())
                 
                 events.append({
                     "id": doc.id,
                     "type": data.get('type', 'info'),
                     "icon": data.get('icon', 'Bot'),
                     "title": data.get('title', 'Event'),
                     "description": data.get('description', ''),
                     "time": get_time_ago(created_at),
                     "date": "Today" if is_today(created_at) else "Yesterday" if is_yesterday(created_at) else created_at.strftime('%Y-%m-%d'),
                     "details": data.get('details', [])
                 })
        except Exception as e:
             print(f"Error fetching timeline events from collection: {e}")

        # If empty, add default welcome event
        if not events:
            events.append({
                "id": "welcome",
                "type": "schedule",
                "icon": "Bot",
                "title": "AI Agent Initialized",
                "description": "Your personalized learning assistant is now active and monitoring your progress.",
                "time": "Just now",
                "date": "Today",
                "details": [
                    "Ready to create study plans",
                    "Tracking your progress",
                    "Optimizing learning path"
                ]
            })
        
        return {"events": events}
    
    except Exception as e:
        print(f"Timeline Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_time_ago(dt: datetime) -> str:
    """Convert datetime to human-readable time ago"""
    now = datetime.now()
    diff = now - dt
    
    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        days = int(diff.total_seconds() / 86400)
        return f"{days}d ago"


def is_today(dt: datetime) -> bool:
    """Check if datetime is today"""
    return dt.date() == datetime.now().date()

def is_yesterday(dt: datetime) -> bool:
    """Check if datetime is yesterday"""
    return dt.date() == (datetime.now() - timedelta(days=1)).date()
