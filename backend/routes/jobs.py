from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
from db.firebase import db
from datetime import datetime
from utils.llm import llm
from firebase_admin import firestore
import json
from utils.timeline_logger import log_timeline_event

router = APIRouter(prefix="/jobs", tags=["jobs"])

class JobRole(BaseModel):
    title: str
    description: str
    match_score: int
    demand: str = "High"
    avg_salary: str = "₹0"

class SkillGap(BaseModel):
    missing_skill: str
    reason: str
    recommended_resource: str = "Coursera/Udemy"

class GapAnalysisResponse(BaseModel):
    role: str
    missing_skills: List[SkillGap]

class JobAnalysisRequest(BaseModel):
    uid: str

class GapAnalysisRequest(BaseModel):
    uid: str
    role: str

class AddSkillRequest(BaseModel):
    uid: str
    skill_name: str

@router.get("/{uid}", response_model=List[JobRole])
async def get_jobs(uid: str):
    """
    Get stored job recommendations
    """
    try:
        user_ref = db.collection('user_profiles').document(uid)
        suggestions_ref = user_ref.collection('job_suggestions')
        # Assuming latest suggestion set or just list all? For simplicity let's stick to a single list stored in a main doc or subcollection documents
        # Storing as a single document 'latest' in subcollection 'job_suggestions' for easy overwrite/retrieval
        suggestion_doc = suggestions_ref.document('latest').get()
        
        if suggestion_doc.exists:
            data = suggestion_doc.to_dict()
            jobs_data = data.get('jobs', [])
            return [JobRole(**job) for job in jobs_data]
        return []

    except Exception as e:
         print(f"Get Jobs Error: {e}")
         return []

@router.post("/analyze", response_model=List[JobRole])
async def analyze_jobs(request: JobAnalysisRequest):
    """
    Analyze profile and suggest job roles
    """
    try:
        # Get user profile
        user_ref = db.collection('user_profiles').document(request.uid)
        profile_doc = user_ref.get()
        
        if not profile_doc.exists:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        profile_data = profile_doc.to_dict()
        interests = profile_data.get('side_hustle_interests', [])
        
        # Get current skills
        skills_ref = user_ref.collection('skills')
        skills = [doc.to_dict().get('name') for doc in skills_ref.stream()]
        
        if not interests and not skills:
             return []

        # LLM Generation
        prompt = f"""
        Based on the following user profile, suggest 3 specific and realistic side hustle job roles or freelance descriptions they could target in the Indian market.
        
        User Interests: {', '.join(interests)}
        Current Skills: {', '.join(skills)}
        
        For each role, provide:
        1. Title
        2. Brief description (max 1 sentence)
        3. Match score (0-100) based on current skills
        4. Market Demand (High, Medium, Low)
        5. Estimated Average Salary/Rate in INR (e.g. ₹500/hr or ₹6 LPA)
        
        Return ONLY valid JSON format:
        [
            {{
                "title": "Role Title",
                "description": "Description...",
                "match_score": 85,
                "demand": "High",
                "avg_salary": "₹500/hr"
            }}
        ]
        """
        
        try:
            response = llm.invoke(prompt).content
            
            # Clean response if markdown
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            jobs_data = json.loads(response.strip())
            
            # Save to Firestore
            suggestions_ref = user_ref.collection('job_suggestions')
            suggestions_ref.document('latest').set({
                "jobs": jobs_data,
                "updated_at": datetime.utcnow().isoformat()
            })
            
            # Log to Timeline
            await log_timeline_event(
                uid=request.uid,
                type="insight",
                title="Job Market Analysis",
                description="Analyzed profile for side hustle opportunities",
                icon="Briefcase",
                details=[f"Suggested {len(jobs_data)} roles"],
                mode="side-hustle"
            )

            return [JobRole(**job) for job in jobs_data]
            
        except Exception as e:
            print(f"LLM Error: {e}")
            # Fallback
            return [
                JobRole(title="Freelance Developer", description="General web development", match_score=50, avg_salary="₹500/hr"),
                JobRole(title="Content Creator", description="Creating tech content", match_score=40, avg_salary="₹10k/mo")
            ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gap", response_model=GapAnalysisResponse)
async def analyze_gap(request: GapAnalysisRequest):
    """
    Analyze skill gap for a specific role
    """
    try:
        user_ref = db.collection('user_profiles').document(request.uid)
        skills_ref = user_ref.collection('skills')
        current_skills = [doc.to_dict().get('name') for doc in skills_ref.stream()]
        
        prompt = f"""
        Target Role: {request.role}
        User's Current Skills: {', '.join(current_skills)}
        
        Identify the top 3-5 critical skills the user is MISSING to be successful in this role.
        For each missing skill, provide a reason why it's needed and a recommended resource type.
        
        Return ONLY valid JSON format:
        {{
            "role": "{request.role}",
            "missing_skills": [
                {{
                    "missing_skill": "Skill Name",
                    "reason": "Why it is needed",
                    "recommended_resource": "e.g. Coursera Specialization"
                }}
            ]
        }}
        """
        
        try:
            response = llm.invoke(prompt).content
            
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            gap_data = json.loads(response.strip())
            
            # Log to Timeline
            await log_timeline_event(
                uid=request.uid,
                type="detection",
                title="Skill Gap Detected",
                description=f"Analysis for {request.role}",
                icon="AlertTriangle",
                details=[f"Missing: {len(gap_data.get('missing_skills', []))} skills"],
                mode="side-hustle"
            )

            return GapAnalysisResponse(**gap_data)
        except Exception as e:
            print(f"LLM Error: {e}")
            return GapAnalysisResponse(role=request.role, missing_skills=[])

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-skill")
async def add_skill(request: AddSkillRequest):
    """
    Add a skill to user's roadmap
    """
    try:
        user_ref = db.collection('user_profiles').document(request.uid)
        
        # Check if skill already exists
        skills_ref = user_ref.collection('skills')
        existing = skills_ref.where('name', '==', request.skill_name).get()
        
        if len(existing) > 0:
            return {"message": "Skill already exists"}
            
        # Add new skill
        new_skill = {
            "name": request.skill_name,
            "status": "not_started",
            "mastery": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        skills_ref.add(new_skill)
        
        # Log to Timeline
        await log_timeline_event(
            uid=request.uid,
            type="roadmap",
            title="Skill Added to Roadmap",
            description=f"Started learning: {request.skill_name}",
            icon="Book",
            details=["Added to skill tracker"],
            mode="side-hustle"
        )
        
        # Sync with Profile Interests
        try:
            user_ref.update({
                "side_hustle_interests": firestore.ArrayUnion([request.skill_name])
            })
        except Exception as e:
            print(f"Failed to sync interest: {e}")

        return {"message": "Skill added successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
