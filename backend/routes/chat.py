from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from utils.llm import llm
from utils.rag_utils import search_documents
from firebase_admin import firestore
from datetime import datetime, timedelta
from routes.planner import PlannerSettings, generate_plan

router = APIRouter(prefix="/chat", tags=["chat"])
db = firestore.client()

# How many previous turns to include for context
HISTORY_TURNS = 10


class ChatRequest(BaseModel):
    message: str
    uid: str
    mode: str = "academic"
    user_name: Optional[str] = "Student"
    session_id: Optional[str] = "default"   # allows multiple chat sessions later


# ---------------------------------------------------------------------------
# History helpers
# ---------------------------------------------------------------------------

def _history_ref(uid: str, session_id: str):
    return (
        db.collection("user_profiles")
        .document(uid)
        .collection("chat_sessions")
        .document(session_id)
        .collection("messages")
    )


def _load_history(uid: str, session_id: str) -> list:
    """
    Fetch the last HISTORY_TURNS * 2 messages and convert them to
    LangChain message objects (HumanMessage / AIMessage).
    """
    ref = _history_ref(uid, session_id)
    docs = (
        ref.order_by("ts", direction=firestore.Query.ASCENDING)
        .limit_to_last(HISTORY_TURNS * 2)
        .get()
    )
    messages = []
    for doc in docs:
        data = doc.to_dict()
        role = data.get("role")
        content = data.get("content", "")
        if role == "human":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))
    return messages


def _save_turn(uid: str, session_id: str, user_msg: str, ai_msg: str):
    """Persist a user + AI turn to Firestore."""
    ref = _history_ref(uid, session_id)
    now = datetime.utcnow()
    ref.add({"role": "human", "content": user_msg, "ts": now})
    # AI message gets +1ms so ordering by ts is always human → ai
    ref.add({"role": "ai",    "content": ai_msg,   "ts": now + timedelta(milliseconds=1)})


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
async def get_my_schedule(uid: str) -> str:
    """Fetch the user's latest study schedule / plan."""
    try:
        plans_ref = (
            db.collection("user_profiles")
            .document(uid)
            .collection("generated_plans")
        )
        docs = (
            plans_ref
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .get()
        )
        if not docs:
            return "No schedule found. You haven't generated one yet."

        data = docs[0].to_dict()
        schedule = data.get("schedule", [])
        if not schedule:
            return "Schedule is empty."

        formatted = "Here is your latest schedule:\n"
        for day in schedule:
            formatted += f"Day: {day.get('day')} ({day.get('date')})\n"
            for slot in day.get("slots", []):
                formatted += (
                    f"  - {slot.get('time')}: {slot.get('task')} ({slot.get('type')})\n"
                )
            formatted += "\n"
        return formatted
    except Exception as e:
        return f"Error fetching schedule: {str(e)}"


@tool
async def generate_new_schedule(uid: str, instructions: str) -> str:
    """
    Generate or update a study schedule based on user instructions.
    Pass any constraints such as 'start at 9am', 'focus on math', or
    'switch Monday math to biology'. Defaults: weekly, 1 hour per day.
    """
    try:
        settings = PlannerSettings(
            uid=uid,
            available_hours=1,
            start_time="09:00",
            end_time="21:00",
            constraints=instructions,
            view_mode="weekly",
        )
        await generate_plan(settings)
        return "New schedule generated! Tell the user to check their planner view."
    except Exception as e:
        return f"Failed to generate schedule: {str(e)}"


@tool
async def add_event(
    uid: str,
    title: str,
    date: str,
    subject: str = "General",
    event_type: str = "deadline",
    topics: str = "",
) -> str:
    """
    Add any academic event for the user.

    event_type options:
      - "deadline"  → assignment, homework, project, or generic task
      - "exam"      → exam, test, midterm, final, quiz

    date must be in YYYY-MM-DD format.
    topics (optional, comma-separated) lists syllabus topics — only for exams.
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        now_iso = datetime.utcnow().isoformat()

        if event_type == "exam":
            syllabus_list = []
            if topics:
                syllabus_list = [
                    {"name": t.strip(), "completed": False}
                    for t in topics.split(",")
                    if t.strip()
                ]
            exam_data = {
                "uid": uid,
                "title": title,
                "date": date,
                "subject": subject,
                "syllabus": syllabus_list,
                "total_topics": len(syllabus_list),
                "completed_topics": 0,
                "created_at": now_iso,
            }
            user_ref.collection("exams").add(exam_data)
            return (
                f"Added exam '{title}' for {subject} on {date}"
                + (f" with {len(syllabus_list)} topics." if syllabus_list else ".")
            )
        else:
            deadline_data = {
                "title": title,
                "due_date": date,
                "subject": subject,
                "completed": False,
                "created_at": now_iso,
            }
            user_ref.collection("deadlines").add(deadline_data)
            return f"Added deadline '{title}' for {subject} on {date}."

    except Exception as e:
        return f"Error adding event: {str(e)}"


@tool
async def get_upcoming_deadlines(uid: str) -> str:
    """Fetch the user's upcoming incomplete deadlines."""
    try:
        deadlines_ref = (
            db.collection("user_profiles")
            .document(uid)
            .collection("deadlines")
        )
        docs = deadlines_ref.where("completed", "==", False).stream()

        deadlines = []
        for doc in docs:
            d = doc.to_dict()
            deadlines.append(
                f"  - {d.get('due_date')}: {d.get('title')} ({d.get('subject')})"
            )

        if not deadlines:
            return "No upcoming deadlines found."
        return "Upcoming Deadlines:\n" + "\n".join(deadlines)
    except Exception as e:
        return f"Error fetching deadlines: {str(e)}"


@tool
async def search_my_notes(uid: str, query: str) -> str:
    """
    Search through the user's uploaded documents and notes for information
    relevant to the query. Use this when the user asks about something that
    could be in their study materials, notes, or uploaded PDFs.
    """
    try:
        passages = search_documents(uid=uid, query=query, k=4)
        if not passages:
            return (
                "No relevant information found in your documents. "
                "You can upload study materials via the Documents section."
            )
        result = "Found relevant information from your notes:\n\n"
        result += "\n\n---\n\n".join(passages)
        return result
    except Exception as e:
        return f"Error searching notes: {str(e)}"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Optiwise, an intelligent academic assistant.
Your goal is to help the student manage their studies, schedule, and deadlines.

You have access to these tools:
1. get_my_schedule        – View the user's current study schedule.
2. generate_new_schedule  – Create or modify the schedule based on instructions.
3. add_event              – Add any academic event:
     • event_type="deadline" for assignments, homework, projects, generic tasks.
     • event_type="exam"     for exams, tests, midterms, finals, quizzes.
     • Always pass uid and date in YYYY-MM-DD format.
     • For exams: ask for syllabus topics if not yet given, but proceed without them if the user says to skip.
4. get_upcoming_deadlines – View all upcoming incomplete deadlines.
5. search_my_notes        – Search the user's uploaded PDFs / study notes.

MEMORY & MULTI-TURN RULES (IMPORTANT):
- You receive the full recent conversation history before the latest message.
- Use it. If the user previously started adding an event and you asked a follow-up
  question (e.g. "what are the topics?"), and they now answer it, piece things
  together from history and complete the action immediately — do NOT ask again.
- Never ask for information the user already gave in a previous turn.

Other rules:
- If the user asks about their schedule, call get_my_schedule first.
- If the user adds a task/assignment/project → add_event with event_type="deadline".
- If the user adds an exam/test/midterm/final/quiz → add_event with event_type="exam".
- If the user asks a study/content question, call search_my_notes first.
- Always confirm actions back to the user.
- Be friendly, concise, and encouraging.
"""

tools = [
    get_my_schedule,
    generate_new_schedule,
    add_event,
    get_upcoming_deadlines,
    search_my_notes,
]
agent_executor = create_react_agent(llm, tools)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("/message")
async def chat_message(request: ChatRequest):
    try:
        now = datetime.now().isoformat()

        # 1. Fetch user profile for subjects
        user_ref = db.collection("user_profiles").document(request.uid).get()
        subjects_list = "General"
        if user_ref.exists:
            user_data = user_ref.to_dict()
            subjects = user_data.get("academic_subjects", [])
            if subjects:
                subjects_list = ", ".join(subjects)

        dynamic_prompt = f"""{SYSTEM_PROMPT}

CRITICAL:
The user is enrolled in: [{subjects_list}].
When adding events or schedules, ONLY use subjects from this list.
If the user mentions a topic not in the list, map it to the closest subject or ask.
"""

        # 2. Load conversation history
        history = _load_history(request.uid, request.session_id or "default")

        # 3. Build message list:  system → history → current user message
        current_human_msg = (
            f"Current Date/Time: {now}\n"
            f"User ID: {request.uid}\n"
            f"User Name: {request.user_name}\n"
            f"Request: {request.message}"
        )

        inputs = {
            "messages": [
                SystemMessage(content=dynamic_prompt),
                *history,
                HumanMessage(content=current_human_msg),
            ]
        }

        # 4. Run agent
        result = await agent_executor.ainvoke(inputs)

        for m in result["messages"]:
            print(f" [{m.type}]: {str(m.content)[:200]}")

        last_message = result["messages"][-1]
        response_text = last_message.content

        # Fallback if agent stopped after tool without a final message
        if not response_text or response_text.strip() == "":
            for m in reversed(result["messages"]):
                if m.type == "tool":
                    response_text = f"Done: {m.content}"
                    break

        # 5. Persist this turn to Firestore
        _save_turn(
            uid=request.uid,
            session_id=request.session_id or "default",
            user_msg=request.message,
            ai_msg=response_text,
        )

        return {"response": response_text}

    except Exception as e:
        print(f"Chat Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{uid}")
async def get_chat_history(uid: str, session_id: str = "default"):
    """
    Return recent chat messages for a user session.
    Used by the frontend to restore history on page load/refresh.
    """
    try:
        ref = _history_ref(uid, session_id)
        docs = (
            ref.order_by("ts", direction=firestore.Query.ASCENDING)
            .limit_to_last(HISTORY_TURNS * 2)
            .get()
        )
        messages = []
        for doc in docs:
            data = doc.to_dict()
            ts = data.get("ts")
            messages.append({
                "role": data.get("role"),       # "human" | "ai"
                "content": data.get("content", ""),
                "ts": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            })
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{uid}")
async def clear_chat_history(uid: str, session_id: str = "default"):
    """Clear a user's chat history for a given session."""
    try:
        ref = _history_ref(uid, session_id)
        docs = ref.stream()
        batch = db.batch()
        count = 0
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
        batch.commit()
        return {"success": True, "deleted": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
