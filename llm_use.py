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
deepseek_llm = get_deepseek_llm
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
            response = llm_grok.invoke(prompt.format(user_input=user_input)).content
            print(response)
            return response
        except Exception as e:
            print(f"Error in LLM typo correction: {e}")
            return user_input  # Return original input if LLM fails
            
    except Exception as e:
        print(f"Unexpected error in handle_typo_errors: {e}")
        return user_input

def batch_relevance_filter(user_input: str, docs: list):
    """Filter documents for relevance using LLM"""
    # Handle edge cases
    if not docs or not user_input.strip():
        return docs
    
    try:
        # Get prompt and format documents
        prompt_template = pull_prompt_from_langsmith("relevance-check-search-bar")
        if not prompt_template:
            return docs
        
        # Convert docs to numbered text
        docs_text = []
        for i, doc in enumerate(docs, 1):
            content = getattr(doc, 'page_content', str(doc))
            docs_text.append(f"{i}. {content}")
        
        # Call LLM
        prompt = prompt_template.format(
            user_input=user_input.strip(),
            docs_text=docs_text
        )
        
        response = llm_grok.invoke(prompt).content.strip().upper()
        
        # Parse response
        if response in ["NONE", "NO RELEVANT DOCUMENTS", ""]:
            return []
        elif response == "ALL":
            return docs
        else:
            # Parse indices
            indices = []
            for part in response.split(','):
                try:
                    idx = int(part.strip()) - 1  # Convert to 0-based
                    if 0 <= idx < len(docs):
                        indices.append(idx)
                except ValueError:
                    continue
            
            return [docs[i] for i in indices] if indices else []
            
    except Exception:
        return docs