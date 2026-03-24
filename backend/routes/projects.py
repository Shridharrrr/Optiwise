from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from utils.llm import llm as vision_llm # Use the vision capable LLM (Gemini 2.5 Flash)
from utils.llm2 import llm # Use secondary for generation if needed, or stick to one.
from db.firebase import db
from datetime import datetime
import uuid
import base64
from langchain_core.messages import HumanMessage
from utils.timeline_logger import log_timeline_event

router = APIRouter(prefix="/projects", tags=["projects"])

class Project(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    estimated_time: str
    skills: List[str]
    status: str = "assigned"  # assigned, in_progress, completed
    created_at: Optional[str] = None
    xp_reward: int = 100
    grade: Optional[int] = None
    feedback: Optional[str] = None

class GenerateProjectRequest(BaseModel):
    uid: str

class ProjectSubmission(BaseModel):
    uid: str
    project_id: str
    image: str # Base64 encoded image

class GradingResult(BaseModel):
    passed: bool
    grade: int
    feedback: str
    xp_awarded: int

async def generate_project_internal(uid: str, skill_name: str = None, difficulty_override: str = None) -> Project:
    """
    Internal helper to generate a project.
    Can be called by /generate endpoint or automatic triggers.
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        
        # Determine context
        skill_context = ""
        if skill_name:
             skill_context = f"Focus primarily on {skill_name}. "
        
        # If no specific skill, look at roadmaps (fallback logic)
        if not skill_name:
            roadmaps_ref = user_ref.collection("roadmaps")
            roadmaps = [doc.to_dict() for doc in roadmaps_ref.stream()]
            if roadmaps:
                 # Simple selection for now
                 skill_context = f"Focus on {roadmaps[0].get('skill')}."
            else:
                 skill_context = "General coding project."

        difficulty = difficulty_override or "Beginner"

        structured_llm = llm.with_structured_output(Project)
        
        prompt = f"""Generate a practical side hustle project.
        Context: {skill_context}
        Difficulty: {difficulty}
        
        The project should:
        1. Be realistic and clearly defined.
        2. Have a clear visual component (UI/Output) that can be verified via screenshot.
        3. Be capable of being completed in 5-20 hours.
        
        Important: The 'description' must be detailed. It should strictly follow this format:
        "Build a [E-commerce Dashboard] that allows users to [manage inventory]. Key Features: 1. [Feature A] 2. [Feature B] 3. [Feature C]. Tech Stack Hint: [React, Tailwind, Charts]."
        
        Output must match Project schema.
        - id: generate a random string
        - status: "assigned"
        - xp_reward: {100 if difficulty == 'Beginner' else 300 if difficulty == 'Intermediate' else 500}
        """
        
        project_data = structured_llm.invoke(prompt)
        
        # Save to Firestore
        new_project = project_data.model_dump()
        new_project['id'] = str(uuid.uuid4())
        new_project['created_at'] = datetime.now().isoformat()
        new_project['in_portfolio'] = False
        
        user_ref.collection("projects").document(new_project['id']).set(new_project)
        
        # Log to Timeline
        await log_timeline_event(
            uid=uid,
            type="project",
            title="New Project Assigned",
            description=f"Generated: {new_project['title']}",
            icon="Rocket",
            details=[f"Difficulty: {difficulty}", f"XP Reward: {new_project['xp_reward']}"],
            mode="side-hustle"
        )
        
        return new_project

    except Exception as e:
        print(f"Internal generation error: {e}")
        raise e

@router.post("/generate")
async def generate_projects(request: GenerateProjectRequest):
    """
    Manual trigger (keeping for fallback/testing).
    """
    try:
        project = await generate_project_internal(request.uid)
        return {"status": "success", "project": project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit")
async def submit_project(submission: ProjectSubmission):
    """
    Grade a project submission using Vision AI.
    """
    try:
        # 1. Fetch project details
        project_ref = db.collection("user_profiles").document(submission.uid).collection("projects").document(submission.project_id)
        doc = project_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Project not found")
            
        project_data = doc.to_dict()
        
        # 2. Prepare Vision prompt
        # We need to strip the header if present (e.g. "data:image/jpeg;base64,")
        image_data = submission.image
        if "," in image_data:
            image_data = image_data.split(",")[1]
            
        message = HumanMessage(
            content=[
                {
                    "type": "text", 
                    "text": f"""You are a strict code project grader. 
                    Project Title: {project_data.get('title')}
                    Description: {project_data.get('description')}
                    
                    Grade this submission based on the screenshot provided.
                    1. Does it look like the requested project?
                    2. Is the UI substantial/complete?
                    
                    Return a JSON object ONLY with the following structure:
                    {{
                        "passed": boolean, (true if it looks correct and substantial)
                        "grade": int, (0-100)
                        "feedback": "string (constructive feedback, max 2 sentences)"
                    }}
                    """
                },
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{image_data}"
                }
            ]
        )
        
        # 3. Call Vision LLM
        # Note: We need a structured output, but for Vision input with LangChain, 
        # mixing structured output + image_url can sometimes be tricky depending on the wrapper.
        # We'll try direct invocation processing the json string if needed, or strict prompt.
        
        # Using the json_mode or structured output if supported for multimodal
        # For simplicity/safety, we'll try a standard invoke and parse.
        response = vision_llm.invoke([message])
        content = response.content.replace('```json', '').replace('```', '').strip()
        
        import json
        result = json.loads(content)
        
        # 4. Handle Result
        if result.get('passed'):
            project_ref.update({
                "status": "completed",
                "in_portfolio": True,
                "completed_at": datetime.now().isoformat(),
                "grade": result.get('grade'),
                "feedback": result.get('feedback')
            })
            
            # Log activity
            try:
                db.collection("user_profiles").document(submission.uid).collection("activity_alerts").add({
                    "message": f"Completed project: {project_data.get('title')}",
                    "type": "success",
                    "created_at": datetime.now().isoformat()
                })

                # Log Practice Session (Update Weekly Stats)
                est_time_str = project_data.get('estimated_time', '0')
                import re
                numbers = [int(n) for n in re.findall(r'\d+', str(est_time_str))]
                hours = 0
                if numbers:
                    # If range "5-10 hours", take average. If "8 hours", take 8.
                    hours = sum(numbers) / len(numbers)
                
                if hours > 0:
                    db.collection("user_profiles").document(submission.uid).collection("practice_sessions").add({
                        "date": datetime.now(),
                        "duration": int(hours * 60), # Convert to minutes
                        "type": "project",
                        "description": f"Completed Project: {project_data.get('title')}"
                    })

            except Exception as e:
                print(f"Failed to log project activity/stats: {e}")

            # Log to Timeline
            await log_timeline_event(
                uid=submission.uid,
                type="project",
                title="Project Completed",
                description=f"Submitted: {project_data.get('title')}",
                icon="Check",
                details=[f"Grade: {result.get('grade')}/100", f"XP Earned: {project_data.get('xp_reward', 100)}"],
                mode="side-hustle"
            )

            return {
                "passed": True,
                "grade": result.get('grade'),
                "feedback": result.get('feedback'),
                "xp_awarded": project_data.get('xp_reward', 100)
            }
        else:
            return {
                "passed": False,
                "grade": result.get('grade'),
                "feedback": result.get('feedback'),
                "xp_awarded": 0
            }

    except Exception as e:
        print(f"Grading error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
