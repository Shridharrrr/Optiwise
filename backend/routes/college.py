from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
from agents.schemas import ExamInfo, StudyPlan
from agents.college.exam_parser import parse_exam_info
from agents.college.planner_agent import create_study_plan
from utils.route_utils import handle_error

router = APIRouter(prefix="/study", tags=["study-planner"])

# Request/Response Models
class StudyPlanRequest(BaseModel):
    user_id: str
    input_text: str

class StudyPlanResponse(BaseModel):
    exam: Optional[dict]
    days_left: Optional[int]
    urgency: Optional[str]
    plan: Optional[dict]
    strategy: Optional[str]
    message: str

@router.post("/create-plan", response_model=StudyPlanResponse)
async def create_study_plan_route(request: StudyPlanRequest):
    """
    Create a personalized study plan using AI agents with structured output
    """
    try:
        # Step 1: Parse exam info using structured output agent
        exam_info: ExamInfo = parse_exam_info(request.input_text)
        
        # Step 2: Create study plan using structured output agent
        study_plan: StudyPlan = create_study_plan(exam_info)
        
        # Step 3: Format response
        return StudyPlanResponse(
            exam={
                "subject": exam_info.subject,
                "exam_date": exam_info.exam_date,
                "topics": exam_info.topics
            },
            days_left=exam_info.days_until_exam,
            urgency=exam_info.urgency,
            plan={
                "daily_plan": [
                    {"day": day.day_number, "tasks": day.tasks}
                    for day in study_plan.daily_breakdown
                ],
                "total_hours": study_plan.total_study_hours,
                "priority_topics": study_plan.priority_topics
            },
            strategy=study_plan.strategy,
            message="Study plan created successfully using AI agents"
        )
    
    except Exception as e:
        print(f"Study Plan Error: {str(e)}")
        # Return fallback plan
        return create_fallback_plan(request.input_text)


@router.get("/health")
async def health_check():
    """Check if the study planner service is running"""
    return {
        "status": "healthy",
        "service": "Study Planner (AI Agents with Structured Output)",
        "model": "gemini-1.5-flash",
        "features": [
            "AI-powered exam parsing",
            "Intelligent study planning",
            "Personalized recommendations",
            "Structured output validation"
        ]
    }


def create_fallback_plan(input_text: str) -> StudyPlanResponse:
    """Create a simple fallback plan if agents fail"""
    fallback_date = datetime.now() + timedelta(days=7)
    
    return StudyPlanResponse(
        exam={
            "subject": "Subject",
            "exam_date": fallback_date.strftime("%Y-%m-%d"),
            "topics": ["Topic 1", "Topic 2", "Topic 3"]
        },
        days_left=7,
        urgency="high",
        plan={
            "daily_plan": [
                {"day": i+1, "tasks": [f"Study session {i+1}", "Practice problems", "Review notes"]}
                for i in range(7)
            ],
            "total_hours": 28,
            "priority_topics": ["Topic 1", "Topic 2", "Topic 3"]
        },
        strategy="intensify",
        message="Study plan created (using fallback due to agent error)"
    )
