import time
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langsmith import Client
import os 
import json
import re 

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

llm_41_mini = ChatOpenAI(
        model="gpt-4.1-mini",  
        temperature=0.0,
        top_p=0.0,
    )

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


def check_relevance(rewritten_query: str, docs: list, extracted_fields: dict):
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
            program_degree = doc.metadata.get('program_degree', 'none')
            
            # Extract school name from page_content instead of metadata
            school_name = extract_school_from_content(doc.page_content)
            print(f"Index {i}: Program ID {program_id} | School: {school_name} | Degree: {program_degree} | Spec: {specialization}")
        
        # If searching for a specific school, filter strictly by page_content
        if extracted_fields.get('school') and extracted_fields['school'] != 'null':
            target_school = extracted_fields['school'].lower().strip()
            filtered_docs = []
            
            for i, doc in enumerate(docs):
                # Extract school name from page_content
                doc_school = extract_school_from_content(doc.page_content).lower().strip()
                
                # Only proceed if both school names are non-empty
                if target_school and doc_school:
                    # Strict matching - normalize school names for comparison
                    target_normalized = normalize_school_name(target_school)
                    doc_normalized = normalize_school_name(doc_school)
                    
                    # Check for exact or contained matches
                    if (target_normalized == doc_normalized or 
                        target_normalized in doc_normalized or 
                        doc_normalized in target_normalized):
                        filtered_docs.append(doc)
                        print(f"🔍 DEBUG: Keeping doc {i} - School match: '{doc_school}' matches '{target_school}'")
                    else:
                        print(f"🔍 DEBUG: Filtering out doc {i} - School mismatch: '{doc_school}' vs '{target_school}'")
                else:
                    print(f"🔍 DEBUG: Filtering out doc {i} - Empty school name: doc='{doc_school}', target='{target_school}'")
            
            if not filtered_docs:
                print("🔍 DEBUG: No documents match the target school after strict filtering")
                return []
            
            # Update docs list for LLM processing
            docs = filtered_docs
        
        fields = extracted_fields
        print(f"🔍 DEBUG: Extracted fields: {fields}")
        
        # Use the new smart metadata-based prompt
        prompt_template = pull_prompt_from_langsmith("relevance-check-search-bar")
        prompt = prompt_template.format(
            extracted_fields=fields, 
            documents_metadata=[doc.metadata for doc in docs], 
            documents_page_content=[doc.page_content for doc in docs]
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


def extract_school_from_content(page_content: str) -> str:
    """Extract school name from document page_content"""
    try:
        import re
        # Look for "**School:** [School Name]" pattern
        school_match = re.search(r'\*\*School:\*\*\s*(.+)', page_content)
        if school_match:
            return school_match.group(1).strip()
        
        # Fallback: Look for other patterns like "School: [School Name]"
        school_match = re.search(r'School:\s*(.+)', page_content)
        if school_match:
            return school_match.group(1).strip()
            
        return ""
    except Exception as e:
        print(f"🔍 ERROR extracting school from content: {e}")
        return ""


def normalize_school_name(school_name: str) -> str:
    """Normalize school name for comparison"""
    try:
        # Convert to lowercase and remove extra whitespace
        normalized = school_name.lower().strip()
        
        # Remove common suffixes/prefixes for better matching
        normalized = re.sub(r'\s*-\s*.*$', '', normalized)  # Remove " - Group/Campus" etc
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        
        return normalized
    except Exception:
        return school_name.lower().strip()
    
def create_specialization_flag(list_of_programs: list, extracted_fields: dict):
    try:
        prompt = pull_prompt_from_langsmith("specialization_check_search_bar")
        response = llm_41_mini.invoke(prompt.format(list_of_programs=list_of_programs, extracted_fields=extracted_fields)).content
        
        print(f"🔍 DEBUG: Specialization check raw response: {response}")
        
        # Clean the response - remove any markdown formatting
        cleaned_response = response.strip()
        
        # Remove ```json and ``` if present
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]  # Remove ```json
        elif cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]   # Remove ```
        
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]  # Remove trailing ```
        
        cleaned_response = cleaned_response.strip()
        print(f"🔍 DEBUG: Cleaned specialization response: {cleaned_response}")
        
        # Parse the list of indices
        if cleaned_response in ["[]", "null", "", "NONE"]:
            print("🔍 DEBUG: No specializations found")
            return list_of_programs
        
        # Parse as list of indices
        indices = json.loads(cleaned_response)
        print(f"🔍 DEBUG: Parsed indices: {indices}")
        
        # Apply the specialization flags
        for index in indices:
            if 0 <= index < len(list_of_programs):
                list_of_programs[index]['is_specialization'] = True
                print(f"🔍 DEBUG: Set is_specialization=True for program {index}")
            else:
                print(f"🔍 DEBUG: Index {index} is out of range for {len(list_of_programs)} programs")
        
        return list_of_programs
        
    except json.JSONDecodeError as e:
        print(f"🔍 DEBUG: JSON parsing error in specialization check: {e}")
        print(f"🔍 DEBUG: Attempted to parse: '{cleaned_response}'")
        return list_of_programs
    except Exception as e:
        print(f"🔍 DEBUG: Error in create_specialization_flag: {e}")
        import traceback
        traceback.print_exc()
        return list_of_programs