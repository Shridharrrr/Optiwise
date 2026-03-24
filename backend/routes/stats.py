from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from datetime import datetime
import statistics

router = APIRouter(prefix="/stats", tags=["stats"])
db = firestore.client()

@router.get("/academic/{uid}")
async def get_academic_stats(uid: str):
    try:
        user_ref = db.collection("user_profiles").document(uid)
        
        # Fetch Weak Areas
        profile_doc = user_ref.get()
        if not profile_doc.exists:
             raise HTTPException(status_code=404, detail="User not found")
        
        from collections import Counter
        
        profile_data = profile_doc.to_dict()
        weak_areas_list = profile_data.get('weak_areas', [])
        
        # Calculate frequency of each weak area to determine confidence
        # More occurrences = Higher confidence that it is a weak area
        area_counts = Counter(weak_areas_list)
        
        weak_areas = []
        for topic, count in area_counts.most_common(): # Take all
            # Formula: Base 30% + 15% per occurrence, max 95%
            # 1 mistake = 45%
            # 2 mistakes = 60%
            # 3 mistakes = 75%
            # 4 mistakes = 90%
            # 5+ mistakes = 95%
            confidence = min(30 + (count * 15), 95)
            
            weak_areas.append({
                "subject": "Topic", 
                "topic": topic,
                "confidence": confidence
            })
            
        # Fetch Exams for Readiness
        exams_ref = user_ref.collection("exams")
        
        # Re-approach: Fetch all exams to list first
        all_exams = [doc.to_dict() for doc in exams_ref.stream()]
        
        total_readiness = 0
        total_syllabus_progress = 0
        count = len(all_exams)
        
        for data in all_exams:
            total_readiness += data.get('readiness_score', 0)
            
            # Syllabus completion calculation
            completed = data.get('completed_topics', 0)
            total = data.get('total_topics', 0)
            if total > 0:
                total_syllabus_progress += (completed / total) * 100
                
        avg_readiness = round(total_readiness / count) if count > 0 else 0
        avg_syllabus = round(total_syllabus_progress / count) if count > 0 else 0
        
        # Calculate Study Hours Today from Plan
        plans_ref = user_ref.collection("generated_plans").order_by("created_at", direction=firestore.Query.DESCENDING).limit(1)
        plan_docs = plans_ref.get()
        
        study_hours_today = 0
        if plan_docs:
            plan_data = plan_docs[0].to_dict()
            schedule = plan_data.get('schedule', [])
            
            # Find today's date string
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            # If generated today or covers today
            for day in schedule:
                # Simple check: matches date OR if it's a daily plan generated today
                # For daily plan, usually only 1 item in list.
                # We'll trust the plan's day if it matches or if it's the only one and recent.
                if day.get('date') == today_str or (len(schedule) == 1 and plan_data.get('created_at', '').startswith(today_str)):
                    for slot in day.get('slots', []):
                        if slot.get('type') == 'study':
                            study_hours_today += slot.get('duration', 0)
                            
        study_hours_str = f"{round(study_hours_today / 60, 1)}h"

        # Fetch History for Graph (Accuracy trend)
        history_ref = user_ref.collection("stats_history").order_by("date", direction=firestore.Query.ASCENDING).limit(10)
        history_docs = history_ref.stream()
        
        performance_data = []
        accuracies = []
        
        for doc in history_docs:
            data = doc.to_dict()
            score = data.get('score', 0)
            accuracies.append(score)
            
            # Label
            date_label = data.get('date').strftime("%d/%m %H:%M") if data.get('date') else "Test"
            
            performance_data.append({
                "name": date_label,
                "marks": score, # Using score as marks percent
                "accuracy": score # Simplified: accuracy same as score for single test
            })
            
        global_accuracy = round(statistics.mean(accuracies)) if accuracies else 0

        # Construct Agent Decisions based on real data
        decisions = []
        if avg_readiness < 50 and count > 0:
             decisions.append({"id": 1, "message": "Detected low readiness. Increasing revision blocks.", "time": "Just now"})
        if len(weak_areas) > 3:
             decisions.append({"id": 2, "message": f"Identified {len(weak_areas)} weak topics. Targeted practice recommended.", "time": "1h ago"})
        if global_accuracy > 80:
             decisions.append({"id": 3, "message": "High accuracy maintained. Suggesting advanced difficulty.", "time": "2h ago"})
        
        if not decisions: # Default
             decisions.append({"id": 1, "message": "Study plan optimized based on recent activity.", "time": "Just now"})

        return {
            "weak_areas": weak_areas, # All areas
            "performance_graph": performance_data if performance_data else [{"name": "Start", "marks": 0, "accuracy": 0}],
            "accuracy_rate": global_accuracy,
            "exam_readiness": avg_readiness,
            "agent_decisions": decisions,
            "study_hours": study_hours_str,
            "syllabus_completion": avg_syllabus
        }

    except Exception as e:
        print(f"Stats Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
