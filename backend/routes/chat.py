from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from utils.llm import llm
from firebase_admin import firestore
from datetime import datetime
from routes.planner import PlannerSettings, generate_plan, get_latest_plan # Reuse existing logic

router = APIRouter(prefix="/chat", tags=["chat"])
db = firestore.client()

class ChatRequest(BaseModel):
    message: str
    uid: str
    mode: str = "academic"
    user_name: Optional[str] = "Student"

# --- Tools ---

@tool
async def get_my_schedule(uid: str) -> str:
    """Fetch the latest study schedule/plan for the user."""
    try:
        # We can reuse the logic from planner route, but need to handle async
        # For simplicity, let's just query the DB directly here similar to the route
        plans_ref = db.collection("user_profiles").document(uid).collection("generated_plans")
        docs = plans_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).get()
        
        if not docs:
            return "No schedule found. You haven't generated one yet."
            
        data = docs[0].to_dict()
        schedule = data.get("schedule", [])
        
        # Format explicitly for the LLM
        if not schedule:
            return "Schedule is empty."
            
        formatted = "Here is the user's latest schedule:\n"
        for day in schedule:
            formatted += f"Day: {day.get('day')} ({day.get('date')})\n"
            for slot in day.get('slots', []):
                formatted += f" - {slot.get('time')}: {slot.get('task')} ({slot.get('type')})\n"
            formatted += "\n"
        return formatted
    except Exception as e:
        return f"Error fetching schedule: {str(e)}"

@tool
async def generate_new_schedule(uid: str, instructions: str) -> str:
    """
    Generate/Update a study schedule based on user instructions. 
    instructions should contain things like 'start at 9am', 'focus on math', OR changes like 'switch Monday math to biology'.
    Default behavior: Weekly schedule, 1 hour per day, based on subjects.
    """
    try:
        # 1. Parse instructions to extract constraints/times using a quick LLM call or regex
        # For now, we'll just pass the raw instructions as constraints
        settings = PlannerSettings(
            uid=uid,
            available_hours=1, # Default as requested: 1 hr per day
            start_time="09:00",
            end_time="21:00",
            constraints=instructions,
            view_mode="weekly" # Default as requested: weekly schedule
        )
        
        # 2. Call the generator
        # Note: generate_plan is async, but tool might expect sync or we await it
        result = await generate_plan(settings)
        
        return "New schedule generated successfully! Tell the user to check their planner/schedule view."
    except Exception as e:
        return f"Failed to generate schedule: {str(e)}"

@tool
async def add_deadline(uid: str, title: str, date: str, subject: str = "General") -> str:
    """
    Add a new deadline/assignment. 
    date should be YYYY-MM-DD format.
    """
    try:
        deadline_data = {
            "title": title,
            "due_date": date,
            "subject": subject,
            "completed": False,
            "created_at": datetime.utcnow().isoformat()
        }
        db.collection("user_profiles").document(uid).collection("deadlines").add(deadline_data)
        return f"Added deadline: '{title}' for {subject} on {date}."
    except Exception as e:
        return f"Error adding deadline: {str(e)}"

@tool
async def add_exam(uid: str, title: str, date: str, subject: str = "General", topics: str = "") -> str:
    """
    Add a new exam/midterm/test.
    date should be YYYY-MM-DD format.
    topics: Optional comma-separated list of syllabus topics.
    """
    try:
        # distinct logic for exams
        syllabus_list = []
        if topics:
            syllabus_list = [{"name": t.strip(), "completed": False} for t in topics.split(",") if t.strip()]
            
        exam_data = {
            "uid": uid,
            "title": title,
            "date": date,
            "subject": subject,
            "syllabus": syllabus_list,
            "total_topics": len(syllabus_list),
            "completed_topics": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Add to 'exams' collection
        doc_ref = db.collection("user_profiles").document(uid).collection("exams").add(exam_data)
        return f"Added exam: '{title}' for {subject} on {date} with {len(syllabus_list)} topics."
    except Exception as e:
        return f"Error adding exam: {str(e)}"

@tool
async def get_upcoming_deadlines(uid: str) -> str:
    """Fetch upcoming deadlines."""
    try:
        deadlines_ref = db.collection("user_profiles").document(uid).collection("deadlines")
        docs = deadlines_ref.where("completed", "==", False).stream()
        
        deadlines = []
        for doc in docs:
            d = doc.to_dict()
            deadlines.append(f"- {d.get('due_date')}: {d.get('title')} ({d.get('subject')})")
            
        if not deadlines:
            return "No upcoming deadlines found."
            
        return "Upcoming Deadlines:\n" + "\n".join(deadlines)
    except Exception as e:
        return f"Error fetching deadlines: {str(e)}"

# --- Agent System ---

SYSTEM_PROMPT = """You are Optiwise, an intelligent academic assistant.
Your goal is to help the student manage their studies, schedule, and deadlines.
You have access to tools to:
1. View their schedule (`get_my_schedule`)
2. Generate/Modify schedule (`generate_new_schedule`) - Use this to create a fresh schedule OR to apply changes to the existing one (e.g. "change monday to math"). Defaults to Weekly, 1 hr/day.
3. Add deadlines (`add_deadline`) - Use this for ASSIGNMENTS, HOMEWORK, PROJECTS, or generic tasks.
4. Add exams (`add_exam`) - Use this specifically for EXAMS, MIDTERMS, FINALS, TESTS, or QUIZZES.
5. View deadlines (`get_upcoming_deadlines`)

Rules:
- If the user asks about their schedule, use `get_my_schedule` first.
- If the user adds a generic task or assignment, use `add_deadline`.
- If the user adds an exam, test, or midterm, use `add_exam`. Ask for topics/syllabus if not provided, but you can proceed without them.
- Be friendly and encouraging.
- If you perform an action (like adding a deadline), confirm it to the user.
- If the user asks for something outside your tools, answer to the best of your ability as a helpful AI assistant.
"""

tools = [get_my_schedule, generate_new_schedule, add_deadline, add_exam, get_upcoming_deadlines]
agent_executor = create_react_agent(llm, tools)

@router.post("/message")
async def chat_message(request: ChatRequest):
    try:
        # Convert conversation history or just send current message
        # For a truly stateful chat, we'd fetch history from DB. 
        # For now, we'll behave as a stateless agent per turn + context
        
        # Get current date/time for context
        now = datetime.now().isoformat()
        
        # Fetch user profile to get valid subjects
        user_ref = db.collection("user_profiles").document(request.uid).get()
        subjects_list = "General" # Default
        if user_ref.exists:
            user_data = user_ref.to_dict()
            subjects = user_data.get("academic_subjects", [])
            if subjects:
                subjects_list = ", ".join(subjects)

        # Dynamic System Prompt with Subjects
        dynamic_system_prompt = f"""{SYSTEM_PROMPT}

CRITICAL INSTRUCTION:
The user is enrolled in the following subjects: [{subjects_list}].
When adding deadlines, tasks, or generating schedules, you MUST ONLY select from these exact subjects.
Do not invent new subjects. If the user mentions a topic not in this list, try to map it to the closest valid subject or ask for clarification.
"""
        
        inputs = {
            "messages": [
                SystemMessage(content=dynamic_system_prompt),
                HumanMessage(content=f"Current Date/Time: {now}\nUser ID: {request.uid}\nUser Name: {request.user_name}\nRequest: {request.message}")
            ]
        }
        
        # Run agent
        result = await agent_executor.ainvoke(inputs)
        
        # Debugging: Print all messages
        print("DEBUG: Agent Messages:")
        for m in result["messages"]:
            print(f" - {m.type}: {m.content}")

        # Extract last message
        last_message = result["messages"][-1]
        response_text = last_message.content
        
        # Fallback: If response is empty, check if the previous message was a ToolMessage
        # This handles cases where the agent stops after the tool execution without a final summary
        if not response_text or response_text.strip() == "":
             # Check for tool message in the history
             for m in reversed(result["messages"]):
                 if m.type == "tool":
                     response_text = f"Action Completed: {m.content}"
                     break
        
        return {"response": response_text}

    except Exception as e:
        print(f"Chat Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
