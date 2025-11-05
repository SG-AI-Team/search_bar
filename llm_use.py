from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_xai import ChatXAI
from dotenv import load_dotenv
import functools
from langsmith import Client
import os 

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


@functools.lru_cache(maxsize=1)
def get_openai_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
    )
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

llm_4o_mini = get_openai_llm()
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
            response = llm_4o_mini.invoke(prompt.format(user_input=user_input)).content
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

def batch_relevance_filter(user_input: str, docs: list):
    """
    Filter a list of documents for relevance in a single LLM call.
    Returns only the relevant documents.
    """
    try:
        print(f"DEBUG: batch_relevance_filter called with user_input='{user_input}', len(docs)={len(docs)}")
        print(f"DEBUG: user_input.strip()='{user_input.strip()}', bool check={not user_input.strip()}")
        
        if not docs:
            return []
        
        # Check for empty input (including '""' case) and return all docs
        if not user_input.strip() or user_input.strip() == '""' or user_input.strip() == "''":
            print(f"Empty input detected, returning all {len(docs)} documents")
            return docs
        
        try:
            docs_text = ""
            for i, doc in enumerate(docs):
                try:
                    content_preview = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                    docs_text += f"Document {i+1}:\nContent: {content_preview}\nMetadata: {doc.metadata}\n\n"
                except Exception as e:
                    print(f"Error processing document {i}: {e}")
                    continue
        except Exception as e:
            print(f"Error building docs text: {e}")
            return docs  # Return all docs if building text fails
        
        try:
            prompt = pull_prompt_from_langsmith("relevance-check-search-bar").format(
                    user_input=user_input,
                    docs_text=docs_text
                )
        except Exception as e:
            print(f"Error pulling or formatting relevance prompt: {e}")
            return docs  # Return all docs if prompt fails
        
        try:
            response = llm_4o_mini.invoke(prompt)
            result = response.content.strip()
            
            # Parse the response
            if result == "NONE":
                return []
            elif result == "ALL":
                return docs
            else:
                # Parse comma-separated numbers
                relevant_indices = []
                try:
                    indices = [int(x.strip()) - 1 for x in result.split(',') if x.strip().isdigit()]
                    relevant_indices = [i for i in indices if 0 <= i < len(docs)]
                except Exception as e:
                    # If parsing fails, fall back to individual checks
                    print(f"Failed to parse batch response: {result}, error: {e}")
                    return docs  # Return all docs as fallback
                
                return [docs[i] for i in relevant_indices]
                
        except Exception as e:
            print(f"LLM relevance check failed: {e}")
            # Fallback to returning all docs
            return docs
            
    except Exception as e:
        print(f"Unexpected error in batch_relevance_filter: {e}")
        return docs  # Return all docs as ultimate fallback