from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel, Field
from typing import List, Optional
from utils.llm import llm
from firebase_admin import firestore
import pypdf
import io
import uuid
from datetime import datetime

router = APIRouter(prefix="/assignments", tags=["assignments"])
db = firestore.client()

class TodoItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str = Field(description="Actionable task created from the assignment")
    estimated_time: str = Field(description="Estimated time to complete (e.g., '30 mins')")
    priority: str = Field(description="Priority level: High, Medium, or Low")
    completed: bool = Field(default=False, description="Whether the task is completed")

class AssignmentResponse(BaseModel):
    id: Optional[str] = None
    title: str = Field(description="Title of the assignment derived from content")
    summary: str = Field(description="Brief summary of what the assignment entails")
    todos: List[TodoItem] = Field(description="List of actionable todos")
    created_at: Optional[datetime] = None

@router.post("/upload", response_model=AssignmentResponse)
async def upload_assignment(
    file: UploadFile = File(...),
    uid: str = Form(...)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read file content
        content = await file.read()
        pdf_file = io.BytesIO(content)
        
        # Extract text using pypdf
        reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
        # Truncate text if too long (to fit context window)
        if len(text) > 20000:
            text = text[:20000] + "...(truncated)"
            
        # Process with LLM
        prompt = f"""
        Analyze the following assignment text and break it down into a clear, actionable checklist of todos.
        
        ASSIGNMENT TEXT:
        {text}
        
        Return the result as a JSON object with the following structure:
        {{
            "title": "Assignment Title",
            "summary": "Brief summary...",
            "todos": [
                {{
                    "task": "Specific actionable task",
                    "estimated_time": "30 mins",
                    "priority": "High"
                }}
            ]
        }}
        """
        
        structured_llm = llm.with_structured_output(AssignmentResponse)
        response = structured_llm.invoke(prompt)
        
        # Add metadata and IDs
        assignment_id = str(uuid.uuid4())
        response.id = assignment_id
        response.created_at = datetime.now()
        
        # Ensure completion status is set (LLM might omit it)
        for todo in response.todos:
            if not getattr(todo, 'id', None):
                todo.id = str(uuid.uuid4())
            todo.completed = False
            
        # Save to Firestore
        assignment_dict = response.model_dump()
        assignment_dict['created_at'] = datetime.now() # ensure datetime is preserved
        
        user_ref = db.collection('user_profiles').document(uid)
        assignment_ref = user_ref.collection('assignments').document(assignment_id)
        assignment_ref.set(assignment_dict)
        
        return response
        
    except Exception as e:
        print(f"Error processing assignment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process assignment: {str(e)}")

@router.get("/{uid}", response_model=List[AssignmentResponse])
async def get_assignments(uid: str):
    try:
        assignments_ref = db.collection('user_profiles').document(uid).collection('assignments')
        docs = assignments_ref.order_by('created_at', direction=firestore.Query.DESCENDING).get()
        
        assignments = []
        for doc in docs:
            data = doc.to_dict()
            assignments.append(AssignmentResponse(**data))
            
        return assignments
    except Exception as e:
        print(f"Error fetching assignments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch assignments: {str(e)}")

@router.patch("/{uid}/{assignment_id}/todo/{todo_id}")
async def update_todo_status(
    uid: str,
    assignment_id: str,
    todo_id: str,
    completed: bool = Body(..., embed=True)
):
    try:
        assignment_ref = db.collection('user_profiles').document(uid).collection('assignments').document(assignment_id)
        doc = assignment_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Assignment not found")
            
        data = doc.to_dict()
        updated = False
        
        # Find and update the specific todo
        for todo in data.get('todos', []):
            if todo.get('id') == todo_id:
                todo['completed'] = completed
                updated = True
                break
                
        if not updated:
            raise HTTPException(status_code=404, detail="Todo item not found")
            
        assignment_ref.update({'todos': data['todos']})
        return {"status": "success", "message": "Todo updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating todo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update todo: {str(e)}")
