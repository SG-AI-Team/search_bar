import functools
import os
import json
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langsmith import traceable

# Correct imports based on file structure
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.utils import read_json
from src.filters import *
from src.ranking import hybrid_retrieve
from src.llm_use import handle_typo_errors, check_relevance, extract_fields, create_specialization_flag

@functools.lru_cache(maxsize=1)
def get_embedding_function():
    return HuggingFaceEmbeddings(model="intfloat/e5-large-v2")

# Cache the vector database
@functools.lru_cache(maxsize=1) 
def get_vector_database():
    embedding_function = get_embedding_function()
    return Chroma(persist_directory=db_path, embedding_function=embedding_function)

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(project_root, "data")
db_path = os.path.join(data_path, "search_db")
school_parent_json_path = os.path.join(data_path, "school_parent_json.json")
program_parent_json_path = os.path.join(data_path, "program_parent_json.json")
print(f"🔍 Project root: {project_root}")
print(f"🔍 Database path: {db_path}")
print(f"🔍 Database exists: {os.path.exists(db_path)}")

try:
    vdb = get_vector_database()
    print("✅ Vector database initialized successfully")
except Exception as e:
    print(f"❌ Error initializing vector database: {e}")
    vdb = None


@traceable(name="search_bar")
def search(user_input: str, search_filter: str, school_ids: list, program_ids: list, more_flag: bool, is_filter_query: bool, filter_statements: list):
    # Typo correction
    try:
        if len(user_input.strip()) < 3 or not user_input.strip():
            rewritten_query = user_input
        else:
            rewritten_query = handle_typo_errors(user_input)
    except Exception:
        rewritten_query = user_input

    metadata_filters = []
    document_filters = []

    # Extract fields and create internal filters
    extracted_fields = extract_fields(rewritten_query)
    internal_filter_result = internal_filters(extracted_fields)
    
    if internal_filter_result:
        metadata_filters.extend(internal_filter_result)
    
    if vdb is None:
        return [], [], [], []
    
    try:
        search_kwargs = {
            "k": 15,
            "fetch_k": 30,
            "lambda_mult": 0.4,
        }
        print(f"🔍 Extracted fields: {extracted_fields}")
        print(f"🔍 Internal filter result: {internal_filter_result}")
        print(f"🔍 Filter statements: {filter_statements}")
        print(f"🔍 Metadata filters: {metadata_filters}")
        print(f"🔍 Document filters: {document_filters}")
        
        # Apply internal filters
        if metadata_filters:
            search_kwargs['filter'] = {"$and": metadata_filters} if len(metadata_filters) > 1 else metadata_filters[0]


        if filter_statements:
            try:
                user_filter_result = filters(filter_statements)
                print(f"🔍 User filter result: {user_filter_result}")
                
                # Process the list of filter conditions (like the old working code)
                for filter_condition in user_filter_result:
                    if isinstance(filter_condition, dict) and "where_document" in filter_condition:
                        document_filters.append(filter_condition["where_document"])
                    else:
                        metadata_filters.append(filter_condition)
                
                # Build final filters
                if metadata_filters:
                    if len(metadata_filters) == 1:
                        search_kwargs['filter'] = metadata_filters[0]
                    else:
                        # Flatten metadata filters properly
                        flattened_conditions = []
                        for filter_dict in metadata_filters:
                            if isinstance(filter_dict, dict):
                                flattened_conditions.append(filter_dict)
                        
                        if len(flattened_conditions) > 1:
                            search_kwargs['filter'] = {"$and": flattened_conditions}
                        else:
                            search_kwargs['filter'] = flattened_conditions[0]
                
                # Handle document filters
                if document_filters:
                    if len(document_filters) == 1:
                        search_kwargs['where_document'] = document_filters[0]
                    else:
                        search_kwargs['where_document'] = {"$and": document_filters}
                    
            except Exception as e:
                print(f"❌ Error processing user filters: {e}")
                pass
        
        # Apply exclusion filters (more_flag logic)
        if more_flag:
            try:
                print(f"🔍 Input - school_ids: {school_ids}, program_ids: {program_ids[:10] if program_ids else []}... (showing first 10)")
                print(f"🔍 Input - search_filter: {search_filter}, program_ids count: {len(program_ids) if program_ids else 0}")
                
                if search_filter == 'schools':
                    exclude_filter = exclude_ids(school_ids, [], search_filter)
                elif search_filter == 'programs':                
                    exclude_filter = exclude_ids([], program_ids, search_filter)
                else:
                    exclude_filter = exclude_ids(school_ids, program_ids, search_filter)
                
                print(f"🔍 Exclude filter generated: {exclude_filter}")
                
                # Check if program_ids are being truncated
                if exclude_filter and 'program_id' in str(exclude_filter):
                    import re
                    nin_ids = re.findall(r'\d+', str(exclude_filter))
                    print(f"🔍 Program IDs in filter: {len(nin_ids)} out of {len(program_ids) if program_ids else 0}")
                
                if exclude_filter:  
                    if 'filter' in search_kwargs:
                        search_kwargs['filter'] = {"$and": [search_kwargs['filter'], exclude_filter]}
                    else:
                        search_kwargs['filter'] = exclude_filter
                    print(f"🔍 Updated search_kwargs with exclusion: {search_kwargs}")
            except Exception as e:
                print(f"❌ Error in exclusion logic: {e}")
                pass
        
        # Apply inclusion filters (is_filter_query logic)
        if is_filter_query:
            try:
                if rewritten_query and rewritten_query.strip():
                    not_exclude_filter_statements = not_exclude_ids(school_ids, program_ids)
                    if not_exclude_filter_statements:
                        if 'filter' in search_kwargs:
                            search_kwargs['filter'] = {"$and": [search_kwargs['filter'], not_exclude_filter_statements]}
                        else:
                            search_kwargs['filter'] = not_exclude_filter_statements
            except Exception:
                pass
        
        # Load parent data
        try:
            school_parent_data = read_json(school_parent_json_path)
            program_parent_data = read_json(program_parent_json_path)
        except Exception:
            return [], [], [], []

        print(f"🔍 Final search_kwargs: {json.dumps(search_kwargs, indent=2, default=str)}")

        # Vector search with proper filter application
        if search_filter == 'schools':
            try:
                k = search_kwargs.get('k', 15)  
                if not rewritten_query or not rewritten_query.strip():
                    k = 2000 
                
                metadata_filter = search_kwargs.get('filter')
                document_filter = search_kwargs.get('where_document')
                
                content = hybrid_retrieve(
                    vdb=vdb, 
                    query=rewritten_query if rewritten_query.strip() else "schools", 
                    k=k, 
                    filter=metadata_filter,
                    where_document=document_filter
                )
            except Exception as e:
                print(f"❌ Error in school search: {e}")
                return [], [], [], []
        else:
            try:
                # FIX: Create retriever AFTER all filters are applied
                retriever = vdb.as_retriever(
                    search_type="mmr",
                    search_kwargs=search_kwargs  # Now contains all filters including exclusions
                )
                
                # Use default query for empty searches
                query_to_use = rewritten_query if rewritten_query.strip() else "programs"
                content = retriever.invoke(query_to_use)
                
            except Exception as e:
                print(f"❌ Error in program search: {e}")
                return [], [], [], []

        # Relevance filtering
        try:
            if not rewritten_query or not rewritten_query.strip() or len(rewritten_query.strip()) < 3:
                print("🔍 Skipping relevance filtering for empty/short query")
                relevant_docs = content
            else:
                relevant_docs = check_relevance(rewritten_query, content, extracted_fields)
        except Exception as e:
            print(f"❌ Error in relevance filtering: {e}")
            relevant_docs = content

        # Process documents
        return_docs = []
        generated_school_ids = []
        generated_program_ids = []
        unique_school_ids = set() 
        unique_program_ids = set()
        
        print(f"🔍 Processing {len(relevant_docs)} relevant documents")
        
        try:
            for doc in relevant_docs:
                try:
                    school_id = doc.metadata.get('school_id')
                    program_id = doc.metadata.get('program_id')

                    if search_filter == 'schools':
                        if school_id and school_id not in unique_school_ids:
                            school_data = school_parent_data.get(str(school_id))
                            if school_data:
                                return_docs.append(school_data)
                                generated_school_ids.append(str(school_id))
                                unique_school_ids.add(school_id)

                    elif search_filter == 'programs':
                        if program_id and program_id not in unique_program_ids:
                            program_data = program_parent_data.get(str(program_id))
                            if program_data:
                                return_docs.append(program_data)
                                generated_program_ids.append(str(program_id))
                                unique_program_ids.add(program_id)
                            
                    else:  # search_filter == 'all'
                        if school_id and school_id not in unique_school_ids:
                            school_data = school_parent_data.get(str(school_id))
                            if school_data:
                                return_docs.append(school_data)
                                generated_school_ids.append(str(school_id))
                                unique_school_ids.add(school_id)
                        
                        if program_id and program_id not in unique_program_ids:
                            program_data = program_parent_data.get(str(program_id))
                            if program_data:
                                return_docs.append(program_data)
                                generated_program_ids.append(str(program_id))
                                unique_program_ids.add(program_id)
                except Exception as e:
                    print(f"❌ Error processing document: {e}")
                    continue
        except Exception as e:
            print(f"❌ Error in document processing loop: {e}")
            pass
        
        print(f"🔍 Final results: {len(return_docs)} documents, {len(generated_school_ids)} schools, {len(generated_program_ids)} programs")
        metadata_list = [doc.metadata for doc in content]
        page_content_list = [doc.page_content for doc in content]
        print(f"🔍  metadata: {metadata_list}")
        print(f"🔍  page content: {page_content_list}")
        programs_list = [doc for doc in return_docs if 'program_name' in doc]
        specialization_checked_docs = create_specialization_flag(programs_list, extracted_fields)
        return specialization_checked_docs, generated_school_ids, generated_program_ids, content

        
    except Exception as e:
        print(f"❌ Critical error in search function: {e}")
        return [], [], [], []