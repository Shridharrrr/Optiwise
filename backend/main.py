from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
import os
from routes.auth import router as auth_router
from routes.profile import router as profile_router
from routes.college import router as study_router
from routes.suggestions import router as suggestions_router
from routes.planner import router as planner_router
from routes.exams import router as exams_router
from routes.learning import router as learning_router
from routes.assessment import router as assessment_router
from routes.stats import router as stats_router
from routes.timeline import router as timeline_router

from routes.dashboard import router as dashboard_router
from routes.chat import router as chat_router
from routes.roadmap import router as roadmap_router
from routes.projects import router as projects_router
from routes.resume import router as resume_router
from routes.assignments import router as assignments_router
from routes.jobs import router as jobs_router
from routes.documents import router as documents_router

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Optiwise Backend",
    description="Backend API for Optiwise - College Learning Assistant",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(study_router)
app.include_router(suggestions_router)
app.include_router(planner_router)
app.include_router(exams_router)
app.include_router(learning_router)
app.include_router(assessment_router)
app.include_router(stats_router)
app.include_router(timeline_router)

app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(roadmap_router)
app.include_router(projects_router)
app.include_router(resume_router)
app.include_router(assignments_router)
app.include_router(jobs_router)
app.include_router(documents_router)

@app.get("/")
def read_root():
    return {
        "message": "Optiwise Backend API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "profile": "/profile",
            "study": "/study",
            "suggestions": "/suggestions",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Optiwise Backend"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
