from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from utils.llm import llm
from datetime import datetime, timedelta
from firebase_admin import firestore
from utils.timeline_logger import log_timeline_event

router = APIRouter(prefix="/planner", tags=["planner"])
db = firestore.client()

# Pydantic Models for Structured Output
from agents.schemas import Task, DaySchedule, ScheduleResponse

# Request Models
class PlannerSettings(BaseModel):
    uid: str
    available_hours: int
    start_time: str
    end_time: str
    constraints: str
    view_mode: str = "daily"  # 'daily' or 'weekly'

@router.post("/generate", response_model=ScheduleResponse)
async def generate_plan(settings: PlannerSettings):
    try:
        # Fetch user profile to get subjects
        user_ref = db.collection("user_profiles").document(settings.uid).get()
        if not user_ref.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_ref.to_dict()
        subjects = user_data.get("academic_subjects", [])
        
        if not subjects:
            subjects = ["General Study"]

        # ------------------------------------------------------------------
        # DYNAMIC PRIORITIZATION LOGIC
        # ------------------------------------------------------------------
        priority_instructions = ""
        crunch_mode = False
        
        try:
            # Fetch upcoming exams
            exams_ref = db.collection("user_profiles").document(settings.uid).collection("exams")
            # Get all exams and filter in python (or minimal query)
            all_exams = exams_ref.stream()
            
            today_date = datetime.now().date()
            
            upcoming_exams = []
            for doc in all_exams:
                data = doc.to_dict()
                if 'date' in data:
                    try:
                        exam_date = datetime.strptime(data['date'], "%Y-%m-%d").date()
                        days_until = (exam_date - today_date).days
                        
                        if 0 <= days_until <= 7:
                            # Check syllabus completion
                            total = data.get('total_topics', 0)
                            completed = data.get('completed_topics', 0)
                            
                            # Skip if fully completed
                            if total > 0 and completed >= total:
                                continue

                            upcoming_exams.append({
                                "subject": data.get('subject', 'Unknown'),
                                "days": days_until,
                                "title": data.get('title', 'Exam')
                            })
                    except:
                        continue
            
            # Sort by urgency
            upcoming_exams.sort(key=lambda x: x['days'])
            
            if upcoming_exams:
                # ------------------------------------------------------------------
                # MULTI-EXAM LOGIC
                # ------------------------------------------------------------------
                
                # 1. Calculate Weights
                total_weight = 0
                for exam in upcoming_exams:
                    # Formula: Closer deadline = Higher weight
                    # Add 0.1 to avoid division by zero if days=0
                    weight = 1 / (exam['days'] + 0.5)
                    exam['weight'] = weight
                    total_weight += weight
                
                # 2. Determine Strategy
                most_urgent = upcoming_exams[0]
                days = most_urgent['days']
                subject = most_urgent['subject']
                
                # CRUNCH MODE (< 2 days)
                if days <= 1:
                    crunch_mode = True
                    
                    if len(upcoming_exams) == 1:
                        # SINGLE EXAM CRUNCH
                        priority_instructions += f"""
                        *** CRITICAL ALERT: {subject} EXAM IN {days} DAYS ***
                        MANDATORY REQUIREMENT:
                        1. EVERY SINGLE STUDY SLOT MUST BE FOR "{subject}".
                        2. DO NOT SCHEDULE ANY OTHER SUBJECT.
                        3. Focus on: Rapid Revision, Mock Tests, and Key Concepts for "{subject}".
                        """
                        # Log
                        await log_timeline_event(
                            uid=settings.uid,
                            type="priority",
                            title=f"⚠️ Crunch Mode: {subject}",
                            description=f"Exam is imminent! Full focus activated.",
                            icon="AlertTriangle",
                            details=[f"Exam in {days} days", "100% Focus Allocation"],
                            mode="academic"
                        )
                    else:
                        # MULTI-EXAM CRUNCH
                        allocations = []
                        details_log = []
                        
                        for exam in upcoming_exams:
                            # Calculate percentage share
                            share = int((exam['weight'] / total_weight) * 100)
                            allocations.append(f"- {exam['subject']}: {share}% of time")
                            details_log.append(f"{exam['subject']}: {share}%")
                            
                        priority_instructions += f"""
                        *** CRITICAL MULTI-EXAM CRUNCH ***
                        User has multiple upcoming exams. You MUST allocate time proportionally:
                        {chr(10).join(allocations)}
                        
                        INSTRUCTIONS:
                        1. Strictly follow the percentage splits above.
                        2. Do NOT schedule non-exam subjects.
                        3. Interleave subjects to avoid burnout (e.g. Subject A -> Subject B -> Subject A).
                        """
                        
                        await log_timeline_event(
                            uid=settings.uid,
                            type="priority",
                            title=f"⚠️ Multi-Exam Crunch",
                            description=f"Balancing multiple upcoming exams.",
                            icon="Layers",
                            details=details_log,
                            mode="academic"
                        )

                # HIGH PRIORITY (< 1 week)
                else:
                    allocations = []
                    for exam in upcoming_exams:
                         share = int((exam['weight'] / total_weight) * 100)
                         # Cap max share for non-crunch to allow some general study
                         share = min(share, 90) 
                         allocations.append(f"- {exam['subject']}: ~{share}%")
                    
                    priority_instructions += f"""
                    *** HIGH PRIORITY SCHEDULE ***
                    Upcoming exams detected. prioritize accordingly:
                    {chr(10).join(allocations)}
                    
                    - Fill remaining time with other subjects if any slots are left.
                    """
                    
                    await log_timeline_event(
                        uid=settings.uid,
                        type="priority",
                        title=f"Exam Prep Mode",
                        description=f"{len(upcoming_exams)} exams coming up this week.",
                        icon="TrendingUp",
                        details=[f"Top Priority: {subject}"] + allocations[:2],
                        mode="academic"
                    )
                    
        except Exception as ex:
            print(f"Error in prioritization logic: {ex}")
        
        # ------------------------------------------------------------------

        # Create structured output LLM
        structured_llm = llm.with_structured_output(ScheduleResponse)

        # Construct optimized prompt
        common_instructions = f"""
User Profile:
- Subjects: {', '.join(subjects)}
- Study Goal: {settings.available_hours} hours/day
- Time Window: {settings.start_time} to {settings.end_time}
- Constraints: {settings.constraints} (STRICTLY FOLLOW)
- Priority Instructions: {priority_instructions}

Requirements:
1. Create time slots strictly within {settings.start_time} - {settings.end_time}
2. Distribute subjects evenly
3. Include short breaks between study sessions
4. Respect user constraints (Priority #1)

Meal Logic:
- IF time window covers 13:00, schedule "Lunch Break" (13:00-14:00)
- IF time window covers 21:00, schedule "Dinner Break" (21:00-22:00)
- ELSE exclude them.

IMPORTANT OUTPUT FORMAT:
For every slot, you MUST include:
- "time": "HH:MM-HH:MM"
- "task": "Description"
- "type": "study" OR "break" OR "other"
- "duration": duration in minutes (integer)
- "subject": "Subject Name" (if study) or null"""

        if settings.view_mode == 'daily':
            today = datetime.now()
            prompt = f"""Create a detailed daily study schedule for {today.strftime('%A, %Y-%m-%d')}.
{common_instructions}

Generate a realistic, achievable daily schedule."""
        else:
            start_date = datetime.now()
            prompt = f"""Create a 7-day study schedule starting {start_date.strftime('%Y-%m-%d')}.
{common_instructions}

Additional Weekly Requirements:
- Generate schedule for 7 consecutive days
- Use 2-3 hour study blocks per session
- Rotate subjects across the week
- Keep it balanced and sustainable

Generate a realistic weekly schedule."""

        try:
            # Get structured output directly
            schedule_data: ScheduleResponse = structured_llm.invoke(prompt)
            
            # Convert to dict for storage
            plan_data = schedule_data.model_dump()
            
        except Exception as e:
            print(f"Structured output error: {e}")
            # Fallback schedule
            plan_data = create_fallback_schedule(settings, subjects)
        
        # Save to Firestore
        try:
            plan_data['created_at'] = datetime.utcnow().isoformat()
            plan_data['view_mode'] = settings.view_mode
            plan_data['settings'] = {
                'available_hours': settings.available_hours,
                'start_time': settings.start_time,
                'end_time': settings.end_time,
                'constraints': settings.constraints
            }
            
            plan_ref = db.collection("user_profiles").document(settings.uid).collection("generated_plans").add(plan_data)
            print(f"Plan saved to Firestore with ID: {plan_ref[1].id}")
            
            # Log to Timeline
            await log_timeline_event(
                uid=settings.uid,
                type="schedule",
                title="Study Plan Generated",
                description=f"Created daily optimized schedule",
                icon="Calendar",
                details=[
                    f"Total: {settings.available_hours}h",
                    f"Mode: {settings.view_mode}",
                    f"Constraints: {settings.constraints[:20]}..." if settings.constraints else "No constraints"
                ]
            )
        except Exception as e:
            print(f"Failed to save plan to Firestore: {str(e)}")

        return plan_data

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Planner Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest/{uid}", response_model=ScheduleResponse)
async def get_latest_plan(uid: str):
    try:
        plans_ref = db.collection("user_profiles").document(uid).collection("generated_plans")
        docs = plans_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).get()
        
        if not docs:
            return {"schedule": []}
              
        return docs[0].to_dict()

    except Exception as e:
        print(f"Error fetching latest plan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def create_fallback_schedule(settings: PlannerSettings, subjects: List[str]) -> dict:
    """Create a simple fallback schedule if LLM fails"""
    today = datetime.now()
    
    if settings.view_mode == 'daily':
        days = 1
    else:
        days = 7
    
    schedule = []
    
    for i in range(days):
        current_date = today + timedelta(days=i)
        day_name = current_date.strftime('%A')
        date_str = current_date.strftime('%Y-%m-%d')
        
        slots = []
        
        # Morning session
        slots.append({
            "time": "09:00-11:00",
            "task": f"{subjects[i % len(subjects)]} - Study Session",
            "type": "study",
            "subject": subjects[i % len(subjects)],
            "duration": 120
        })
        
        # Lunch break
        slots.append({
            "time": "13:00-14:00",
            "task": "Lunch Break",
            "type": "break",
            "subject": None,
            "duration": 60
        })
        
        # Afternoon session
        slots.append({
            "time": "14:00-16:00",
            "task": f"{subjects[(i+1) % len(subjects)]} - Practice",
            "type": "study",
            "subject": subjects[(i+1) % len(subjects)],
            "duration": 120
        })
        
        # Evening session
        slots.append({
            "time": "17:00-19:00",
            "task": f"{subjects[(i+2) % len(subjects)]} - Review",
            "type": "study",
            "subject": subjects[(i+2) % len(subjects)],
            "duration": 120
        })

        # Dinner break (Added)
        slots.append({
            "time": "21:00-22:00",
            "task": "Dinner Break",
            "type": "break",
            "subject": None,
            "duration": 60
        })
        
        schedule.append({
            "day": day_name,
            "date": date_str,
            "slots": slots
        })
    
    return {"schedule": schedule}
