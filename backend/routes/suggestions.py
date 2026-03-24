from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List
from utils.llm import llm
from utils.route_utils import handle_error

router = APIRouter(prefix="/suggestions", tags=["ai-suggestions"])

# Pydantic Models for Structured Output
class SuggestionResponse(BaseModel):
    """AI-generated academic and side hustle suggestions"""
    subjects: List[str] = Field(description="List of 6 core academic subjects for this major", min_items=6, max_items=6)
    side_hustle_interests: List[str] = Field(description="List of 6 marketable skills/technologies", min_items=6, max_items=6)

# Request Model
class SuggestionRequest(BaseModel):
    degree: str
    major: str

@router.post("/generate", response_model=SuggestionResponse)
async def generate_suggestions(request: SuggestionRequest):
    """
    Generate academic subjects and side hustle interests based on degree/major using AI
    """
    try:
        # Create structured output LLM
        structured_llm = llm.with_structured_output(SuggestionResponse)
        
        # Concise prompt
        prompt = f"""You are an academic advisor AI. Based on the student's degree and major, suggest relevant subjects and side hustle interests.

Degree: {request.degree}
Major: {request.major}

Requirements:
1. Suggest EXACTLY 6 core subjects typically studied in this major
2. Suggest EXACTLY 6 marketable skills/technologies that complement this degree
3. Be specific and practical
4. Consider current industry trends

Example for Computer Science:
- Subjects: Data Structures, Algorithms, Database Systems, Operating Systems, Computer Networks, Software Engineering
- Side Hustle: Web Development, Mobile App Development, AI/ML, Cloud Computing, Cybersecurity, UI/UX Design"""

        try:
            # Get structured output
            suggestions: SuggestionResponse = structured_llm.invoke(prompt)
            return suggestions
        
        except Exception as e:
            print(f"Structured output error: {e}")
            # Return fallback
            return create_fallback_suggestions(request.major)
    
    except Exception as e:
        raise handle_error(e, "AI Suggestion")


@router.get("/health")
async def health_check():
    """Check if the suggestions service is running"""
    return {
        "status": "healthy",
        "service": "AI Suggestions (Structured Output)",
        "model": "gemini-1.5-flash"
    }


def create_fallback_suggestions(major: str) -> SuggestionResponse:
    """Create fallback suggestions if LLM fails"""
    # Basic fallback based on common majors
    common_subjects = [
        f"{major} Fundamentals",
        f"Advanced {major}",
        f"{major} Theory",
        f"{major} Applications",
        "Research Methods",
        "Capstone Project"
    ]
    
    common_interests = [
        "Web Development",
        "Data Analysis",
        "Content Creation",
        "Freelancing",
        "Consulting",
        "Online Teaching"
    ]
    
    return SuggestionResponse(
        subjects=common_subjects,
        side_hustle_interests=common_interests
    )
