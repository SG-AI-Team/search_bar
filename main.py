import os 
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.general_search import search
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


@app.post("/search", response_model=SearchResult)
async def search_endpoint(request: SearchRequest):
        
    results, school_ids, program_ids, content1 = search(
            user_input=request.user_input,
            search_filter=request.search_filter,
            school_ids=request.school_ids,
            program_ids=request.program_ids,
            more_flag=request.more_flag,
            is_filter_query=request.is_filter_query,
            filter_statements=request.filter_statements,
        )
        
    
    search_result = SearchResult(
            results=results,
            generated_school_ids=school_ids,
            generated_program_ids=program_ids
        )
    
    
    return search_result