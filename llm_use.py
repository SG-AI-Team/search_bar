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

    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"Field extraction took: {execution_time:.4f} seconds")
    
    return response


def batch_relevance_filter(rewritten_query: str, docs: list):
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
            title = doc.page_content.split('\n')[1] if '\n' in doc.page_content else 'unknown'
            print(f"Index {i}: Program ID {program_id} | Spec: {specialization} | Parent: {parent} | Title: {title}")
        
        fields = extract_fields(rewritten_query)
        print(f"🔍 DEBUG: Extracted fields: {fields}")
        
        prompt_template = pull_prompt_from_langsmith("relevance-check-search-bar")
        prompt = prompt_template.format(json=fields, data=docs)
        
        # Hash the prompt to compare with LangSmith
        import hashlib
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        print(f"🔍 DEBUG: Prompt hash: {prompt_hash}")
        
        print("🔍 DEBUG: ============ PROMPT SENT TO LLM ============")
        print(prompt)
        print("🔍 DEBUG: ============ END OF PROMPT ============")
        
        # Force more deterministic behavior
        response = llm_41_mini.invoke(
            prompt,
            config={
                "temperature": 0.0,
                "top_p": 0.0,
                "seed": 42,  # Add seed for reproducibility
            }
        )
        result = response.content.strip()
        
        print(f"🔍 DEBUG: ============ LLM RAW RESPONSE ============")
        print(f"'{result}'")
        print(f"🔍 DEBUG: Response type: {type(result)}")
        print(f"🔍 DEBUG: Response length: {len(result)}")
        print("🔍 DEBUG: ============ END OF LLM RESPONSE ============")

        # Add manual verification for the expected indices
        expected_indices = [1, 3, 7]  # Based on your LangSmith results
        print(f"🔍 DEBUG: Expected indices from LangSmith: {expected_indices}")
        print(f"🔍 DEBUG: Expected programs: {[docs[i].metadata.get('program_id') for i in expected_indices if i < len(docs)]}")

        if result.upper() == "ALL":
            print("🔍 DEBUG: LLM returned 'ALL', returning all documents")
            return docs
        elif result in ["NONE", "[]", "null"]:
            print("🔍 DEBUG: LLM returned 'NONE/[]/null', returning empty list")
            return []

        # Handle parsing
        if result.startswith('[') and result.endswith(']'):
            print("🔍 DEBUG: Parsing as Python list format")
            indices = json.loads(result)
        else:
            print("🔍 DEBUG: Parsing as comma-separated format")
            indices = [int(x.strip()) for x in result.split(',')]
            
        print(f"🔍 DEBUG: Parsed indices: {indices}")
        print(f"🔍 DEBUG: Total documents available: {len(docs)}")
        
        # Compare with expected
        if indices != expected_indices:
            print(f"🔍 DEBUG: ⚠️  MISMATCH! Expected {expected_indices} but got {indices}")
            print("🔍 DEBUG: Difference analysis:")
            for i, (expected, actual) in enumerate(zip(expected_indices, indices)):
                if expected != actual:
                    print(f"  Position {i}: Expected {expected} (Program {docs[expected].metadata.get('program_id') if expected < len(docs) else 'OOB'})")
                    print(f"  Position {i}: Got {actual} (Program {docs[actual].metadata.get('program_id') if actual < len(docs) else 'OOB'})")
        
        # Handle indices
        filtered_docs = []
        for idx in indices:
            if 0 <= idx < len(docs):
                filtered_docs.append(docs[idx])
                print(f"🔍 DEBUG: Added document {idx}: {docs[idx].metadata.get('program_id', 'unknown')}")
            else:
                print(f"🔍 DEBUG: WARNING - Index {idx} out of range (0-{len(docs)-1})")
                
        print(f"🔍 DEBUG: Final filtered documents count: {len(filtered_docs)}")
        return filtered_docs
        
    except Exception as e:
        print(f"🔍 DEBUG: ERROR in batch_relevance_filter: {e}")
        import traceback
        traceback.print_exc()
        return docs