from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from utils.llm2 import llm
from db.firebase import db
from datetime import datetime
from routes.projects import generate_project_internal

router = APIRouter(prefix="/roadmap", tags=["roadmap"])

class RoadmapItem(BaseModel):
    id: str
    title: str
    description: str
    estimated_time: str
    resources: List[str] = []
    completed: bool = False

class RoadmapPhase(BaseModel):
    id: str
    title: str
    items: List[RoadmapItem]

class RoadmapResponse(BaseModel):
    skill: str
    phases: List[RoadmapPhase]
    last_updated: Optional[str] = None

class GenerateRoadmapRequest(BaseModel):
    uid: str
    skill: str
    current_level: str = "Beginner" 

class UpdateProgressRequest(BaseModel):
    uid: str
    skill: str
    phase_id: str
    item_id: str
    item_id: str
    completed: bool

class ToggleResponse(BaseModel):
    status: str
    completed: bool
    project_unlocked: bool = False
    new_project: Optional[dict] = None

@router.post("/generate", response_model=RoadmapResponse)
async def generate_roadmap(request: GenerateRoadmapRequest):
    try:
        # Check if exists in DB
        doc_ref = db.collection("user_profiles").document(request.uid).collection("roadmaps").document(request.skill.lower())
        doc = doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()

        # Generate with LLM
        structured_llm = llm.with_structured_output(RoadmapResponse)
        
        prompt = f"""Create a detailed, step-by-step learning roadmap for "{request.skill}" for a {request.current_level} level learner.
        Break it down into 3-4 distinct phases (e.g., Fundamentals, Core Concepts, Advanced Topics, Projects).
        
        For each phase, provide 3-5 specific topics (RoadmapItems).
        Each Item must have:
        - id: unique string (e.g., "phase1-item1")
        - title: concise topic name
        - description: short explanation of what to learn
        - estimated_time: e.g. "2 hrs"
        - resources: list of 1-2 search terms for finding tutorials (e.g. "React hooks tutorial")
        
        Ensure the output matches the RoadmapResponse schema exactly.
        """
        
        # Invoke LLM
        result = structured_llm.invoke(prompt)
        
        # Prepare data for Firebase
        data = result.model_dump()
        data['skill'] = request.skill # Ensure skill name is correct
        data['last_updated'] = datetime.now().isoformat()
        
        # Ensure completed is False by default
        for phase in data['phases']:
            for item in phase['items']:
                item['completed'] = False
                
        # Save to Firebase
        doc_ref.set(data)
        
        return data

    except Exception as e:
        print(f"Roadmap generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

        raise HTTPException(status_code=500, detail=str(e))
 
@router.post("/toggle", response_model=ToggleResponse)
async def toggle_progress(request: UpdateProgressRequest):
    try:
        doc_ref = db.collection("user_profiles").document(request.uid).collection("roadmaps").document(request.skill.lower())
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Roadmap not found")
            
        data = doc.to_dict()
        
        # Find and toggle
        found = False
        for phase in data['phases']:
            if phase['id'] == request.phase_id:
                for item in phase['items']:
                    if item['id'] == request.item_id:
                        item['completed'] = request.completed
                        found = True
                        break
            if found: break
        
        if found:
            doc_ref.update(data)
            
            # Log activity if completed
            if request.completed:
                try:
                    # Find item title
                    item_title = "Topic"
                    for phase in data['phases']:
                        for item in phase['items']:
                            if item['id'] == request.item_id:
                                item_title = item['title']
                                break
                    
                    db.collection("user_profiles").document(request.uid).collection("activity_alerts").add({
                        "message": f"Completed topic: {item_title} in {request.skill}",
                        "type": "success",
                        "created_at": datetime.now().isoformat()
                    })
                except Exception as e:
                    print(f"Failed to log activity: {e}")

            # Update Skill Mastery
            try:
                total_items = 0
                completed_items = 0
                for phase in data.get('phases', []):
                    items = phase.get('items', [])
                    total_items += len(items)
                    completed_items += sum(1 for i in items if i.get('completed'))
                
                if total_items > 0:
                    mastery = int((completed_items / total_items) * 100)
                    
                    # Update or Create Skill in 'skills' collection
                    skills_ref = db.collection("user_profiles").document(request.uid).collection("skills")
                    
                    # Try to find existing skill
                    # We'll use a query since ID might differ from name
                    query = skills_ref.where("name", "==", request.skill).limit(1)
                    results = list(query.stream())
                    
                    if results:
                        # Update existing
                        results[0].reference.update({"mastery": mastery})
                    else:
                        # Create new
                        skills_ref.add({
                            "name": request.skill,
                            "mastery": mastery,
                            "status": "in_progress",
                            "icon": "Code" 
                        })
            except Exception as e:
                print(f"Failed to update skill mastery: {e}")
            
            # Check if this completion finished a phase
            project_unlocked = False
            new_project = None
            
            if request.completed:
                # Find the phase we just updated
                target_phase = None
                for phase in data['phases']:
                    if phase['id'] == request.phase_id:
                        target_phase = phase
                        break
                
                if target_phase:
                    # Check if all items in this phase are now completed
                    all_completed = all(item['completed'] for item in target_phase['items'])
                    
                    if all_completed:
                        # Determine difficulty based on phase index
                        phase_index = next((i for i, p in enumerate(data['phases']) if p['id'] == request.phase_id), 0)
                        
                        difficulty = "Beginner"
                        if phase_index == 1: difficulty = "Intermediate"
                        elif phase_index >= 2: difficulty = "Advanced"
                        
                        # Generate Project
                        try:
                            new_project = await generate_project_internal(
                                uid=request.uid, 
                                skill_name=request.skill,
                                difficulty_override=difficulty
                            )
                            project_unlocked = True
                        except Exception as e:
                            print(f"Auto-generate project failed: {e}")

            return {
                "status": "success", 
                "completed": request.completed,
                "project_unlocked": project_unlocked,
                "new_project": new_project
            }
        
        raise HTTPException(status_code=404, detail="Item not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
