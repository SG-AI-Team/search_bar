import time
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_xai import ChatXAI
from dotenv import load_dotenv
import functools
from langsmith import Client
import os 
import json

def serialize_docs(docs):
    serialized = []
    for d in docs:
        content = d.page_content
        doc_info = {
            "id": d.id,
            "metadata": d.metadata,
            "page_content": content
        }
        serialized.append(doc_info)
    return json.dumps(serialized, ensure_ascii=False)


def pull_prompt_from_langsmith(prompt_name: str):
    """Pull prompt from LangSmith hub"""
    try:
        client = Client(api_key=os.getenv("LANGCHAIN_API_KEY"))
        prompt = client.pull_prompt(prompt_name)
        return prompt
    except Exception as e:
        print(f"Error pulling prompt {prompt_name}: {e}")
        return None

load_dotenv()


# @functools.lru_cache(maxsize=1)
# def get_openai_llm():
#     return ChatOpenAI(
#         model="gpt-4.1-mini",  # Fix: was "gpt-4.1-mini" which doesn't exist
#         temperature=0.0,
#         top_p=0.0,
#         seed=42,  # Add seed for reproducibility
#     )
@functools.lru_cache(maxsize=1)
def get_deepseek_llm():
    return ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.0,
    max_tokens=4048,
    top_p=1,
)
@functools.lru_cache(maxsize=1)
def get_xai_llm():
    return ChatXAI(
    model="grok-4-fast",
    temperature=0.0,
)

llm_41_mini = ChatOpenAI(
        model="gpt-4.1-mini",  
        temperature=0.0,
        top_p=0.0,
    )
deepseek_llm = get_deepseek_llm()
llm_grok = get_xai_llm()




def handle_typo_errors(user_input: str):
    try:
        # Handle empty input early
        if not user_input.strip():
            return ""
                
        try:
            prompt = pull_prompt_from_langsmith("typo-error-handle-prompt-search-bar")
        except Exception as e:
            print(f"Error pulling prompt: {e}")
            return user_input  # Return original input if prompt fails
        
        try:
            response = llm_41_mini.invoke(prompt.format(user_input=user_input)).content
            # Fix: Clean the response to ensure single line
            cleaned_response = response.strip().split('\n')[0]  # Take only first line
            print(cleaned_response)
            return cleaned_response
        except Exception as e:
            print(f"Error in LLM typo correction: {e}")
            return user_input  # Return original input if LLM fails
            
    except Exception as e:
        print(f"Unexpected error in handle_typo_errors: {e}")
        return user_input
    

def extract_fields(rewritten_query: str):
    start_time = time.time()
    
    prompt = pull_prompt_from_langsmith("fields_extraction_search_bar")
    response = llm_41_mini.invoke(prompt.format(rewritten_query=rewritten_query)).content
    print(f"🔍 Raw LLM response: {response}")
    
    # Clean the response - remove markdown code blocks if present
    cleaned_response = response.strip()
    
    # Remove ```json and ``` if present
    if cleaned_response.startswith('```json'):
        cleaned_response = cleaned_response[7:]  # Remove ```json
    elif cleaned_response.startswith('```'):
        cleaned_response = cleaned_response[3:]   # Remove ```
    
    if cleaned_response.endswith('```'):
        cleaned_response = cleaned_response[:-3]  # Remove trailing ```
    
    cleaned_response = cleaned_response.strip()
    print(f"🔍 Cleaned response: {cleaned_response}")
    
    try:
        response_dict = json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"❌ Attempted to parse: '{cleaned_response}'")
        return {'is_valid': False}

    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"Field extraction took: {execution_time:.4f} seconds")
    
    return response_dict


def batch_relevance_filter(rewritten_query: str, docs: list, extracted_fields: dict):
    if not docs:
        print("🔍 DEBUG: No documents provided to filter")
        return []

    if not rewritten_query.strip() or rewritten_query.strip() in ['""', "''"]:
        print("🔍 DEBUG: Empty query, returning all documents")
        return docs

    try:
        # Document order verification first
        print("🔍 DEBUG: Document order verification:")
        for i, doc in enumerate(docs):
            program_id = doc.metadata.get('program_id', 'unknown')
            specialization = doc.metadata.get('specialization', 'none')
            parent = doc.metadata.get('parent_program', 'none')
            program_degree = doc.metadata.get('program_degree', 'none')
            print(f"Index {i}: Program ID {program_id} | Degree: {program_degree} | Spec: {specialization} | Parent: {parent}")
        
        fields = extracted_fields
        print(f"🔍 DEBUG: Extracted fields: {fields}")
        
        # Use the new smart metadata-based prompt
        prompt_template = pull_prompt_from_langsmith("relevance-check-search-bar")
        prompt = prompt_template.format(
            extracted_fields=fields, 
            documents_metadata=[doc.metadata for doc in docs], 
            documents_page_content = [doc.page_content for doc in docs]
        )
        
        # Force more deterministic behavior
        response = llm_41_mini.invoke(
            prompt,
            config={
                "temperature": 0.0,
                "top_p": 0.0,
                "seed": 42,
                "max_tokens": 100,
            }
        )
        result = response.content.strip()
        
        print(f"🔍 DEBUG: ============ LLM RAW RESPONSE ============")
        print(f"'{result}'")
        print("🔍 DEBUG: ============ END OF LLM RESPONSE ============")

        if result.upper() == "ALL":
            return docs
        elif result in ["NONE", "[]", "null", ""]:
            return []

        # Parse indices
        if result.startswith('[') and result.endswith(']'):
            indices = json.loads(result)
        else:
            indices = [int(x.strip()) for x in result.split(',') if x.strip().isdigit()]
            
        # Filter valid documents
        filtered_docs = []
        for idx in indices:
            if 0 <= idx < len(docs):
                filtered_docs.append(docs[idx])
                
        return filtered_docs
        
    except Exception as e:
        print(f"🔍 DEBUG: ERROR in batch_relevance_filter: {e}")
        import traceback
        traceback.print_exc()
        return docs