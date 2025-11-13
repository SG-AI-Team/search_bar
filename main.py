from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from general_search import search
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    user_input: str
    search_filter: str = "all"  
    school_ids: List[str] = []
    program_ids: List[str] = []
    more_flag: bool = False
    is_filter_query: bool = False
    filter_statements: List[Dict[str, Any]] = []

class SearchResult(BaseModel):
    results: List[Dict[str, Any]]
    generated_school_ids: List[str]
    generated_program_ids: List[str]

class SearchResponse(BaseModel):
    search_results: List[SearchResult]

@app.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    try:
        results1, school_ids1, program_ids1, content1 = search(
            user_input=request.user_input,
            search_filter=request.search_filter,
            school_ids=request.school_ids,
            program_ids=request.program_ids,
            more_flag=False,
            is_filter_query=request.is_filter_query,
            filter_statements=request.filter_statements,
        )
        
        results2, school_ids2, program_ids2, content2 = search(
            user_input=request.user_input,
            search_filter=request.search_filter,
            school_ids=school_ids1,
            program_ids=program_ids1,
            more_flag=True,
            is_filter_query=request.is_filter_query,
            filter_statements=request.filter_statements,
        )
        
        search_result1 = SearchResult(
            results=results1,
            generated_school_ids=school_ids1,
            generated_program_ids=program_ids1
        )
        
        search_result2 = SearchResult(
            results=results2,
            generated_school_ids=school_ids2,
            generated_program_ids=program_ids2
        )
        
        return SearchResponse(search_results=[search_result1, search_result2])
        
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))