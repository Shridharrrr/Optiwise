from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional
from utils.llm import llm
from utils.route_utils import handle_error
from youtube_search import YoutubeSearch

router = APIRouter(prefix="/learning", tags=["learning"])

# Pydantic Models for Structured Output
class SearchQuery(BaseModel):
    """Optimized YouTube search query"""
    query: str = Field(description="Single optimized YouTube search query for educational content")

# Request/Response Models
class RecommendationRequest(BaseModel):
    topic: str
    subject: str

class VideoResource(BaseModel):
    id: str
    title: str
    thumbnail: str
    duration: str
    channel: str
    link: str
    viewCount: Optional[str] = "N/A"

@router.post("/recommend", response_model=List[VideoResource])
async def recommend_resources(request: RecommendationRequest):
    """Recommend YouTube learning resources using AI-optimized search"""
    try:
        # Create structured output LLM
        structured_llm = llm.with_structured_output(SearchQuery)
        
        # Concise prompt
        prompt = f"""Generate ONE optimized YouTube search query for learning about "{request.topic}" in {request.subject}.

Requirements:
1. Focus on conceptual understanding and visual explanations
2. Target educational content
3. Be specific and clear
4. Return only the search query text

Example: For "Photosynthesis" in Biology, return: "photosynthesis explained animation visual"
"""

        try:
            # Get optimized query
            search_query: SearchQuery = structured_llm.invoke(prompt)
            query = search_query.query.strip().replace('"', '')
        except Exception as e:
            print(f"Structured output error: {e}")
            # Fallback to simple query
            query = f"{request.topic} {request.subject} explained"
        
        # Search YouTube
        results = YoutubeSearch(query, max_results=4).to_dict()

        videos = []
        for item in results:
            link = f"https://www.youtube.com{item['url_suffix']}"
            thumbnail = item['thumbnails'][0] if item.get('thumbnails') else ""
            
            videos.append({
                "id": item['id'],
                "title": item['title'],
                "thumbnail": thumbnail,
                "duration": item.get('duration', 'N/A'),
                "channel": item.get('channel', 'Unknown'),
                "link": link,
                "viewCount": item.get('views', 'N/A')
            })
        
        return videos

    except Exception as e:
        raise handle_error(e, "Learning Resources")
