from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
from db.firebase import db
from datetime import datetime
from utils.llm import llm
from firebase_admin import firestore
import json
import os
from utils.timeline_logger import log_timeline_event

router = APIRouter(prefix="/jobs", tags=["jobs"])

class JobRole(BaseModel):
    title: str
    description: str
    match_score: int
    demand: str = "High"
    avg_salary: str = "₹0"
    url: Optional[str] = None
    company: Optional[str] = None

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
        
        CRITICAL RULES:
        1. DO NOT suggest overlapping or parent/child skill pairs (e.g., if you suggest "Full Stack Developer", DO NOT also suggest "Frontend Developer"). Make sure all 3 roles are distinct paths.
        2. Pick roles that actually exist in the current job market.
        
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
            return [
                JobRole(title="Freelance Developer", description="General web development", match_score=50, avg_salary="₹500/hr"),
                JobRole(title="Content Creator", description="Creating tech content", match_score=40, avg_salary="₹10k/mo")
            ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/")
async def search_jobs(query: str, uid: str):
    """
    Search real jobs using TheirStack API.
    Provides India-specific results and maps them to JobRole.
    """
    api_key = os.getenv("THEIRSTACK_API_KEY")
    if not api_key:
        return []

    try:
        import httpx
        url = "https://api.theirstack.com/v1/jobs/search"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # TheirStack POST body requirements:
        # Require at least one filter like job_title_or
        # and we can add country_code_or for India
        payload = {
            "job_title_or": [query],
            "company_country_code_or": ["IN"],
            "posted_at_max_age_days": 30,
            "limit": 3
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=15.0)
            
        if response.status_code != 200:
            print(f"TheirStack API Error: {response.text}")
            return []
            
        data = response.json()
        jobs_list = data.get("data", [])
        
        # Prepare data for LLM Enhancement
        extracted_jobs = []
        for job in jobs_list:
            title = job.get("job_title", job.get("title", "Unknown Role"))
            company = job.get("company_name", job.get("company", "Unknown Company"))
            job_url = job.get("url", job.get("link", ""))
            extracted_jobs.append({"title": title, "company": company, "url": job_url})
            
        # Enhance with LLM for salary and description
        results = []
        if extracted_jobs:
            llm_prompt = f"""
            I have {len(extracted_jobs)} job listings from India. 
            For each, provide a 1-sentence engaging description emphasizing the value of this role, and a realistic estimated average salary range in INR (e.g. "₹8-12 LPA" or "₹50k/mo").
            
            Jobs:
            {json.dumps([{"title": j["title"], "company": j["company"]} for j in extracted_jobs])}
            
            Return ONLY valid JSON format as an array of objects matching exactly the input order:
            [
                {{ "description": "...", "salary": "₹8-12 LPA" }}
            ]
            """
            
            try:
                llm_res = llm.invoke(llm_prompt).content
                if "```json" in llm_res:
                    llm_res = llm_res.split("```json")[1].split("```")[0]
                elif "```" in llm_res:
                    llm_res = llm_res.split("```")[1].split("```")[0]
                    
                enhanced_data = json.loads(llm_res.strip())
                
                for idx, job in enumerate(extracted_jobs):
                    enhanced = enhanced_data[idx] if idx < len(enhanced_data) else {}
                    results.append(JobRole(
                        title=job["title"],
                        description=enhanced.get("description", f"Hiring Company: {job['company']}. Click to view details."),
                        match_score=0,
                        demand="Live",
                        avg_salary=enhanced.get("salary", "N/A"),
                        url=job["url"],
                        company=job["company"]
                    ))
            except Exception as e:
                print(f"LLM Enhancement Error: {e}")
                for job in extracted_jobs:
                    results.append(JobRole(
                        title=job["title"],
                        description=f"Hiring Company: {job['company']}. Click to view details.",
                        match_score=0,
                        demand="Live",
                        avg_salary="N/A",
                        url=job["url"],
                        company=job["company"]
                    ))
            
        return results
        
    except Exception as e:
        print(f"Search API Error: {e}")
        return []

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
