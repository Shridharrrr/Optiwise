from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from datetime import datetime, timedelta
from typing import List, Dict

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
db = firestore.client()

@router.get("/sidehustle/{uid}")
async def get_sidehustle_dashboard(uid: str):
    """
    Get comprehensive side hustle dashboard data
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        profile_doc = user_ref.get()
        
        if not profile_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile_data = profile_doc.to_dict()
        
        # Get skills data
        skills_ref = user_ref.collection("skills")
        all_skills = [doc.to_dict() for doc in skills_ref.stream()]
        
        # Get projects data
        projects_ref = user_ref.collection("projects")
        all_projects = [doc.to_dict() for doc in projects_ref.stream()]
        
        # Get learning sources
        sources_ref = user_ref.collection("learning_sources")
        all_sources = [doc.to_dict() for doc in sources_ref.stream()]
        
        # Get activity alerts
        alerts_ref = user_ref.collection("activity_alerts").order_by("created_at", direction=firestore.Query.DESCENDING).limit(5)
        all_alerts = []
        for doc in alerts_ref.stream():
            alert_data = doc.to_dict()
            alert_data['id'] = doc.id
            all_alerts.append(alert_data)
        
        # Calculate stats
        if all_skills:
            skills_in_progress = len([s for s in all_skills if s.get('status') == 'in_progress'])
        elif profile_data.get('side_hustle_interests'):
            skills_in_progress = len(profile_data.get('side_hustle_interests', []))
        else:
            skills_in_progress = 0
        projects_completed = len([p for p in all_projects if p.get('status') == 'completed'])
        
        # Calculate weekly practice hours
        week_ago = datetime.now() - timedelta(days=7)
        practice_sessions = user_ref.collection("practice_sessions").where("date", ">=", week_ago).stream()
        weekly_hours = sum(session.to_dict().get('duration', 0) for session in practice_sessions) / 60  # Convert to hours
        
        # Calculate portfolio readiness
        total_portfolio_items = sum(1 for p in all_projects if p.get('in_portfolio', False))
        portfolio_target = 10  # Target number of portfolio items
        portfolio_ready = min(int((total_portfolio_items / portfolio_target) * 100), 100)
        
        # Format skill progress
        skill_progress = []
        icon_map = {
            'web': 'Code',
            'mobile': 'Code',
            'app': 'Code',
            'code': 'Code',
            'coding': 'Code',
            'dsa': 'FolderKanban',
            'data': 'FolderKanban',
            'design': 'Zap',
            'ui': 'Zap',
            'ux': 'Zap',
            'creative': 'Zap',
            'ai': 'Rocket',
            'ml': 'Rocket',
            'machine': 'Rocket',
            'artificial': 'Rocket',
            'intelligence': 'Rocket'
        }

        def get_icon(name):
            name_lower = name.lower()
            for key, icon in icon_map.items():
                if key in name_lower:
                    return icon
            return 'Code' # Default
        
        if all_skills:
            for skill in all_skills:
                # Try to get roadmap for detailed progress even if skill doc exists
                progress = int(skill.get('mastery', 0))
                try:
                    roadmap_doc = user_ref.collection("roadmaps").document(skill.get('name', '').lower()).get()
                    if roadmap_doc.exists:
                        r_data = roadmap_doc.to_dict()
                        total = 0
                        completed = 0
                        for phase in r_data.get('phases', []):
                            items = phase.get('items', [])
                            total += len(items)
                            completed += sum(1 for i in items if i.get('completed'))
                        if total > 0:
                            progress = int((completed / total) * 100)
                except:
                    pass

                skill_progress.append({
                    'name': skill.get('name', 'Skill'),
                    'progress': progress,
                    'icon': get_icon(skill.get('name', ''))
                })
        
        # Merge with profile interests that aren't already covered by skills
        existing_skill_names = set(s.get('name', '').lower() for s in skill_progress)
        
        if profile_data.get('side_hustle_interests'):
            for interest in profile_data.get('side_hustle_interests', []):
                if interest.lower() in existing_skill_names:
                    continue
                    
                progress = 0
                try:
                    roadmap_doc = user_ref.collection("roadmaps").document(interest.lower()).get()
                    if roadmap_doc.exists:
                        r_data = roadmap_doc.to_dict()
                        total = 0
                        completed = 0
                        for phase in r_data.get('phases', []):
                            items = phase.get('items', [])
                            total += len(items)
                            completed += sum(1 for i in items if i.get('completed'))
                        if total > 0:
                            progress = int((completed / total) * 100)
                except:
                    pass

                skill_progress.append({
                    'name': interest,
                    'progress': progress,
                    'icon': get_icon(interest)
                })
        
        # Format learning sources
        learning_sources = []
        for source in all_sources[:5]:  # Top 5 sources
            learning_sources.append({
                'id': source.get('id', ''),
                'source': source.get('name', ''),
                'skill': source.get('skill', ''),
                'type': source.get('type', 'course'),
                'status': source.get('status', 'Queued')
            })
        
        # Format assigned projects
        assigned_projects = []
        active_projects = [p for p in all_projects if p.get('status') == 'assigned']
        
        for project in active_projects[:5]:  # Top 5 active projects
            assigned_projects.append({
                'id': project.get('id', ''),
                'title': project.get('title', ''),
                'description': project.get('description', ''),
                'difficulty': project.get('difficulty', 'Beginner'),
                'estimatedTime': project.get('estimated_time', '8 hours'),
                'skills': project.get('skills', [])
            })
        
        # Format activity alerts
        activity_alerts = []
        for alert in all_alerts:
            alert_type = alert.get('type', 'info')
            activity_alerts.append({
                'id': alert.get('id', ''),
                'type': alert_type,
                'message': alert.get('message', ''),
                'time': format_time_ago(alert.get('created_at'))
            })
        
        # Calculate daily activity for heatmap (last 365 days)
        year_ago = datetime.now() - timedelta(days=365)
        activity_ref = user_ref.collection("activity_alerts").where("created_at", ">=", year_ago.isoformat()).stream()
        
        date_counts = {}
        for doc in activity_ref:
            data = doc.to_dict()
            date_str = data.get('created_at', '')[:10] # YYYY-MM-DD
            if date_str:
                date_counts[date_str] = date_counts.get(date_str, 0) + 1
        
        daily_activity = []
        for date, count in date_counts.items():
            daily_activity.append({"date": date, "count": count})
            
        return {
            "stats": {
                "skills_in_progress": skills_in_progress,
                "projects_completed": projects_completed,
                "weekly_practice": f"{int(weekly_hours)}h",
                "portfolio_ready": f"{portfolio_ready}%",
                "portfolio_ready_value": portfolio_ready
            },
            "skill_progress": skill_progress,
            "learning_sources": learning_sources,
            "assigned_projects": assigned_projects,
            "activity_alerts": activity_alerts,
            "daily_activity": daily_activity,
            "monthly_project_stats": get_monthly_project_stats(all_projects)
        }
    
    except Exception as e:
        print(f"Dashboard Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deadlines/{uid}")
async def get_deadlines(uid: str):
    """
    Get upcoming deadlines for the user
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        deadlines_ref = user_ref.collection("deadlines").where("dueDate", ">=", datetime.now()).order_by("dueDate").limit(10)
        
        deadlines = []
        for doc in deadlines_ref.stream():
            data = doc.to_dict()
            deadlines.append({
                "id": doc.id,
                "title": data.get('title', ''),
                "dueDate": data.get('dueDate').isoformat() if data.get('dueDate') else None,
                "category": data.get('category', 'assignment'),
                "subject": data.get('subject')
            })
        
        return {"deadlines": deadlines}
    
    except Exception as e:
        print(f"Deadlines Error: {str(e)}")
        return {"deadlines": []}


@router.get("/reminders/{uid}")
async def get_reminders(uid: str):
    """
    Get study reminders for the user
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        reminders_ref = user_ref.collection("reminders").where("completed", "==", False).order_by("dueTime").limit(10)
        
        reminders = []
        for doc in reminders_ref.stream():
            data = doc.to_dict()
            reminders.append({
                "id": doc.id,
                "subject": data.get('subject', ''),
                "topic": data.get('topic', ''),
                "dueTime": data.get('dueTime').isoformat() if data.get('dueTime') else None,
                "priority": data.get('priority', 'medium'),
                "completed": data.get('completed', False)
            })
        
        return {"reminders": reminders}
    
    except Exception as e:
        print(f"Reminders Error: {str(e)}")
        return {"reminders": []}


@router.get("/status/{uid}")
async def get_crunch_mode_status(uid: str):
    """
    Check if user is in crunch mode (exam < 24h)
    """
    try:
        user_ref = db.collection("user_profiles").document(uid)
        # Check exams in the next 24 hours
        exams_ref = user_ref.collection("exams")
        all_exams = exams_ref.stream()
        
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        crunch_mode = False
        crucial_exam = None
        
        for doc in all_exams:
            data = doc.to_dict()
            if 'date' in data:
                try:
                    exam_date = datetime.strptime(data['date'], "%Y-%m-%d").date()
                    # Check if exam is today or tomorrow
                    if exam_date <= tomorrow and exam_date >= today:
                        # CHECK SYLLABUS COMPLETION
                        total = data.get('total_topics', 0)
                        completed = data.get('completed_topics', 0)
                        
                        # Only activate crunch mode if syllabus is NOT complete
                        if total > 0 and completed >= total:
                            continue

                        crunch_mode = True
                        crucial_exam = data.get('subject', 'Unknown Subject')
                        break
                except:
                    continue
                    
        return {
            "isCrunchMode": crunch_mode,
            "crucialExam": crucial_exam
        }
        
    except Exception as e:
        print(f"Status Check Error: {str(e)}")
        return {"isCrunchMode": False, "crucialExam": None}


def get_monthly_project_stats(all_projects: List[Dict]) -> List[Dict]:
    """
    Calculate monthly project completions for the last 6 months.
    Returns list of {name: 'Month', value: count}
    """
    # Initialize last 6 months with 0
    today = datetime.now()
    stats = {}
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30) # Approx month
        month_name = d.strftime("%b")
        stats[month_name] = 0
        
    # Count completed projects
    for project in all_projects:
        if project.get('status') == 'completed' and project.get('completed_at'):
            try:
                # Parse date
                completed_at = project.get('completed_at')
                if isinstance(completed_at, str):
                    dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                elif isinstance(completed_at, datetime):
                    dt = completed_at
                else:
                    continue
                
                # Check if within last 6 months window (approx)
                if (today - dt).days < 180:
                    month_name = dt.strftime("%b")
                    if month_name in stats:
                        stats[month_name] += 1
            except:
                continue

    # Convert to list ensuring order
    result = []
    # Re-generate key order to ensure chronological sort
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        month_name = d.strftime("%b")
        # specific check to avoid duplicates if month names overlap in short window (unlikely with 30 days but safer)
        if not any(x['name'] == month_name for x in result): 
             result.append({"name": month_name, "value": stats.get(month_name, 0)})
             
    return result


def format_time_ago(timestamp) -> str:
    """Format timestamp to human-readable time ago"""
    if not timestamp:
        return "Just now"
    
    # Handle Firestore timestamp
    if hasattr(timestamp, 'timestamp'):
        dt = datetime.fromtimestamp(timestamp.timestamp())
    elif isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            return "Just now"
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        return "Just now"
    
    now = datetime.now()
    diff = now - dt
    
    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
    else:
        days = int(diff.total_seconds() / 86400)
        return f"{days} {'day' if days == 1 else 'days'} ago"
