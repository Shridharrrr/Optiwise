from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List
from utils.llm import llm
from utils.route_utils import handle_error
from firebase_admin import firestore
import uuid
from utils.timeline_logger import log_timeline_event

router = APIRouter(prefix="/assessment", tags=["assessment"])
db = firestore.client()

# Pydantic Models for Structured Output
class MCQuestion(BaseModel):
    """Multiple choice question"""
    question: str = Field(description="The question text")
    options: List[str] = Field(description="Four answer options", min_items=4, max_items=4)
    correct_answer: int = Field(description="Index of correct option (0-3)", ge=0, le=3)
    topic_tag: str = Field(description="Specific topic this question tests")

class AssessmentQuestions(BaseModel):
    """Collection of assessment questions"""
    questions: List[MCQuestion] = Field(description="List of 10 MCQ questions", min_items=10, max_items=10)

# Request Models
class GenerateRequest(BaseModel):
    subject: str
    topics: List[str]
    set_number: int  # 1, 2, or 3

class Question(BaseModel):
    id: str
    question: str
    options: List[str]
    correct_answer: int
    topic_tag: str

class SubmitRequest(BaseModel):
    uid: str
    exam_id: str
    set_number: int
    answers: List[dict]  # [{question_id: "id", selected: 0}]
    questions: List[Question]

@router.post("/generate", response_model=List[Question])
async def generate_assessment(request: GenerateRequest):
    """Generate 10 MCQ questions using structured output with retry logic"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Create structured output LLM with include_raw for better error handling
            structured_llm = llm.with_structured_output(AssessmentQuestions, include_raw=True)
            
            topics_str = ", ".join(request.topics)
            
            # More explicit prompt emphasizing completion
            prompt = f"""Generate EXACTLY 10 complete Multiple Choice Questions for "{request.subject}".

Topics to cover: {topics_str}

CRITICAL REQUIREMENTS:
1. Generate EXACTLY 10 questions - no more, no less
2. EVERY question MUST have ALL of these fields:
   - question: The question text
   - options: EXACTLY 4 answer choices
   - correct_answer: Index 0-3 of the correct option
   - topic_tag: Which topic this tests
3. DO NOT truncate or leave any question incomplete
4. Mix difficulty levels (easy, medium, hard)
5. Test understanding, not just memorization

IMPORTANT: Complete ALL 10 questions fully before finishing!"""

            # Get structured output
            result = structured_llm.invoke(prompt)
            
            # Extract the parsed object
            if isinstance(result, dict) and 'parsed' in result:
                assessment = result['parsed']
            else:
                assessment = result
            
            # Validate we got exactly 10 questions
            if not hasattr(assessment, 'questions') or len(assessment.questions) != 10:
                print(f"Attempt {attempt + 1}: Got {len(assessment.questions) if hasattr(assessment, 'questions') else 0} questions, retrying...")
                continue
            
            # Validate each question is complete
            all_complete = True
            for i, q in enumerate(assessment.questions):
                if not all([
                    hasattr(q, 'question') and q.question,
                    hasattr(q, 'options') and len(q.options) == 4,
                    hasattr(q, 'correct_answer') and 0 <= q.correct_answer <= 3,
                    hasattr(q, 'topic_tag') and q.topic_tag
                ]):
                    print(f"Attempt {attempt + 1}: Question {i+1} incomplete, retrying...")
                    all_complete = False
                    break
            
            if not all_complete:
                continue
            
            # All questions are complete, format and return
            questions = []
            for q in assessment.questions:
                questions.append({
                    "id": str(uuid.uuid4()),
                    "question": q.question,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "topic_tag": q.topic_tag
                })
            
            print(f"Successfully generated {len(questions)} complete questions on attempt {attempt + 1}")
            return questions
        
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                # Last attempt failed, use fallback
                print("All attempts failed, using fallback questions")
                return create_fallback_questions(request.subject, request.topics)
            continue
    
    # If we somehow get here, return fallback
    return create_fallback_questions(request.subject, request.topics)


@router.post("/submit")
async def submit_assessment(request: SubmitRequest):
    """Submit and grade assessment"""
    try:
        correct_count = 0
        total = len(request.questions)
        weak_topics = []
        
        # Grade answers
        for q in request.questions:
            user_ans = next((a['selected'] for a in request.answers if a['question_id'] == q.id), -1)
            if user_ans == q.correct_answer:
                correct_count += 1
            else:
                weak_topics.append(q.topic_tag)
        
        accuracy = (correct_count / total) * 100
        
        # Update Firestore
        user_ref = db.collection("user_profiles").document(request.uid)
        exam_ref = user_ref.collection("exams").document(request.exam_id)
        
        # Update exam readiness
        exam_ref.update({
            "readiness_score": accuracy,
            "last_assessment_date": firestore.SERVER_TIMESTAMP
        })
        
        # Update weak areas
        profile_doc = user_ref.get()
        current_weak_areas = profile_doc.to_dict().get('weak_areas', []) if profile_doc.exists else []
        updated_weak_areas = (current_weak_areas + weak_topics)[-50:]  # Keep last 50
        
        user_ref.update({"weak_areas": updated_weak_areas})
        
        # Log performance history
        user_ref.collection("stats_history").add({
            "date": firestore.SERVER_TIMESTAMP,
            "exam_subject": request.exam_id,
            "score": accuracy,
            "type": "assessment"
        })

        # Log to Timeline
        if weak_topics:
            await log_timeline_event(
                uid=request.uid,
                type="detection",
                title="Weak Topics Identified",
                description=f"Assessment revealed {len(weak_topics)} weak areas",
                icon="AlertTriangle",
                details=[f"Topics: {', '.join(list(set(weak_topics))[:3])}", f"Score: {int(accuracy)}%"]
            )
        else:
             await log_timeline_event(
                uid=request.uid,
                type="insight",
                title="Assessment Completed",
                description=f"Strong performance on {request.exam_id}",
                icon="Trophy",
                details=[f"Score: {int(accuracy)}%", "No weak areas detected"]
            )

        return {
            "score": correct_count,
            "total": total,
            "accuracy": accuracy,
            "readiness": accuracy,
            "weak_areas": list(set(weak_topics))
        }

    except Exception as e:
        raise handle_error(e, "Assessment Submission")


def create_fallback_questions(subject: str, topics: List[str]) -> List[Question]:
    """Create fallback questions if LLM fails"""
    questions = []
    for i in range(10):
        topic = topics[i % len(topics)]
        questions.append({
            "id": str(uuid.uuid4()),
            "question": f"Sample question {i+1} about {topic} in {subject}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "topic_tag": topic
        })
    return questions
