from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from datetime import datetime
from typing import Dict, List
from utils.llm import llm
import os
import json

router = APIRouter(prefix="/resume", tags=["resume"])
db = firestore.client()

@router.post("/generate/{uid}")
async def generate_resume(uid: str):
    """
    Generate a professional resume using AI based on user profile, skills, and projects
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        profile_doc = user_ref.get()
        
        if not profile_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile_data = profile_doc.to_dict()
        
        # Get email from profile or Firebase auth
        email = profile_data.get('email')
        if not email:
            # Try to get from Firebase Auth
            from firebase_admin import auth
            try:
                user = auth.get_user(uid)
                email = user.email or 'Not provided'
            except:
                email = 'Not provided'
        
        # Check if profile is complete (only name, college, course are required)
        required_fields = ['name', 'college', 'course']
        missing_fields = [field for field in required_fields if not profile_data.get(field)]
        
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Profile incomplete. Missing: {', '.join(missing_fields)}"
            )
        
        # Fetch skills
        skills_ref = user_ref.collection("skills")
        skills = [doc.to_dict() for doc in skills_ref.stream()]
        
        # Fetch completed projects
        projects_ref = user_ref.collection("projects").where("status", "==", "completed")
        projects = [doc.to_dict() for doc in projects_ref.stream()]
        
        # Prepare context for AI
        context = f"""
Generate a professional resume for the following candidate:

**Personal Information:**
- Name: {profile_data.get('name')}
- Email: {email}
- Phone: {profile_data.get('phone', 'Not provided')}
- Website: {profile_data.get('website', 'Not provided')}
- College: {profile_data.get('college')}
- Course/Major: {profile_data.get('course')}

**Skills:**
{chr(10).join([f"- {skill.get('name', 'Unknown')}: {skill.get('mastery', 0)}% mastery" for skill in skills]) if skills else "No skills recorded"}

**Completed Projects:**
{chr(10).join([f"- {proj.get('title', 'Untitled')}: {proj.get('description', 'No description')}" for proj in projects]) if projects else "No completed projects"}

**Side Hustle Interests:**
{', '.join(profile_data.get('side_hustle_interests', [])) if profile_data.get('side_hustle_interests') else 'Not specified'}

Please generate a professional resume with the following sections in JSON format:
1. summary: A compelling professional summary (2-3 sentences)
2. experience: Array of work/project experiences with title, description, and key achievements
3. skills: Categorized skills (technical, soft skills, tools)
4. projects: Detailed project descriptions with technologies used
5. education: Education details

Return ONLY valid JSON with this structure:
{{
  "summary": "string",
  "experience": [
    {{
      "title": "string",
      "organization": "string",
      "duration": "string",
      "description": "string",
      "achievements": ["string"]
    }}
  ],
  "skills": {{
    "technical": ["string"],
    "tools": ["string"],
    "soft": ["string"]
  }},
  "projects": [
    {{
      "name": "string",
      "description": "string",
      "technologies": ["string"],
      "highlights": ["string"]
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "institution": "string",
      "duration": "string"
    }}
  ]
}}
"""
        
        # Generate resume using Gemini via langchain
        response = llm.invoke(context)
        
        # Parse the response
        resume_text = response.content.strip()
        
        # Remove markdown code blocks if present
        if resume_text.startswith("```json"):
            resume_text = resume_text[7:]
        if resume_text.startswith("```"):
            resume_text = resume_text[3:]
        if resume_text.endswith("```"):
            resume_text = resume_text[:-3]
        
        resume_data = json.loads(resume_text.strip())
        
        # Add personal info to resume data
        resume_data['personal_info'] = {
            'name': profile_data.get('name'),
            'email': email,
            'phone': profile_data.get('phone', ''),
            'website': profile_data.get('website', ''),
            'location': f"{profile_data.get('college', '')}"
        }
        
        # Store the generated resume
        resume_ref = user_ref.collection("resumes").document()
        resume_data['id'] = resume_ref.id
        resume_data['generated_at'] = datetime.now().isoformat()
        resume_ref.set(resume_data)
        
        return {
            "success": True,
            "resume": resume_data
        }
    
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {str(e)}")
        print(f"Response text: {resume_text}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        print(f"Resume Generation Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{uid}")
async def get_latest_resume(uid: str):
    """
    Get the most recently generated resume for a user
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        resumes_ref = user_ref.collection("resumes").order_by("generated_at", direction=firestore.Query.DESCENDING).limit(1)
        
        resumes = list(resumes_ref.stream())
        
        if not resumes:
            raise HTTPException(status_code=404, detail="No resume found. Please generate one first.")
        
        resume_data = resumes[0].to_dict()
        return {
            "success": True,
            "resume": resume_data
        }
    
    except Exception as e:
        print(f"Resume Fetch Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
