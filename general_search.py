from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from utils import read_json
from filters import *
import json
import time
from ranking import hybrid_retrieve
from llm_use import handle_typo_errors, batch_relevance_filter, extract_fields

try:
    embedding_function = HuggingFaceEmbeddings(model="intfloat/e5-large-v2")
    vdb = Chroma(persist_directory="vdb_with_double_diploma/", embedding_function=embedding_function)
except Exception as e:
    print(f"Error initializing vector database: {e}")
    vdb = None

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
        
        if metadata_filters:
            search_kwargs['filter'] = {"$and": metadata_filters} if len(metadata_filters) > 1 else metadata_filters[0]

        if filter_statements:
            try:
                user_filters = filters(filter_statements)
                
                for filter_condition in user_filters:
                    if isinstance(filter_condition, dict) and "where_document" in filter_condition:
                        document_filters.append(filter_condition["where_document"])
                    else:
                        metadata_filters.append(filter_condition)
                
                if metadata_filters:
                    search_kwargs['filter'] = {"$and": metadata_filters} if len(metadata_filters) > 1 else metadata_filters[0]
                
                if document_filters:
                    search_kwargs['where_document'] = {"$and": document_filters} if len(document_filters) > 1 else document_filters[0]
            except Exception:
                pass
        
        if more_flag:
            try:
                if search_filter == 'schools':
                    exclude_filter = exclude_ids(school_ids, [], search_filter)
                elif search_filter == 'programs':                
                    exclude_filter = exclude_ids([], program_ids, search_filter)
                else:
                    exclude_filter = exclude_ids(school_ids, program_ids, search_filter)
                    
                if exclude_filter:  
                    if 'filter' in search_kwargs:
                        search_kwargs['filter'] = {"$and": [search_kwargs['filter'], exclude_filter]}
                    else:
                        search_kwargs['filter'] = exclude_filter
            except Exception:
                pass
        
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
        
        # Create retriever
        try:
            retriever = vdb.as_retriever(
                search_type="mmr",
                search_kwargs=search_kwargs
            )
        except Exception:
            return [], [], [], []

        # Load parent data
        try:
            school_parent_data = read_json("school_parent_json.json")
            program_parent_data = read_json("program_parent_json.json")
        except Exception:
            return [], [], [], []

        # Vector search
        if search_filter == 'schools':
            try:
                k = search_kwargs.get('k', 15)  
                if not rewritten_query or not rewritten_query.strip():
                    k = 2000 
                
                metadata_filter = search_kwargs.get('filter')
                document_filter = search_kwargs.get('where_document')
                
                content = hybrid_retrieve(
                    vdb=vdb, 
                    query=rewritten_query, 
                    k=k, 
                    filter=metadata_filter,
                    where_document=document_filter
                )
            except Exception:
                return [], [], [], []
        else:
            try:
                content = retriever.invoke(rewritten_query)
            except Exception:
                return [], [], [], []

        # Relevance filtering
        try:
            if not rewritten_query or not rewritten_query.strip() or len(rewritten_query.strip()) < 3:
                relevant_docs = content
            else:
                relevant_docs = batch_relevance_filter(rewritten_query, content, extracted_fields)
        except Exception:
            relevant_docs = content

        # Process documents
        return_docs = []
        generated_school_ids = []
        generated_program_ids = []
        unique_school_ids = set() 
        unique_program_ids = set()
        print(f"🔍 Final search_kwargs: {json.dumps(search_kwargs, indent=2, default=str)}")
        
        try:
            for doc in relevant_docs:
                try:
                    school_id = doc.metadata.get('school_id')
                    program_id = doc.metadata.get('program_id')

                    if search_filter == 'schools':
                        if school_id and school_id not in unique_school_ids:
                            school_data = school_parent_data.get(school_id)
                            if school_data:
                                return_docs.append(school_data)
                                generated_school_ids.append(school_id)
                                unique_school_ids.add(school_id)

                    elif search_filter == 'programs':
                        if program_id and program_id not in unique_program_ids:
                            program_data = program_parent_data.get(program_id)
                            if program_data:
                                return_docs.append(program_data)
                                generated_program_ids.append(program_id)
                                unique_program_ids.add(program_id)
                            
                    else:  # search_filter == 'all'
                        if school_id and school_id not in unique_school_ids:
                            school_data = school_parent_data.get(school_id)
                            if school_data:
                                return_docs.append(school_data)
                                generated_school_ids.append(school_id)
                                unique_school_ids.add(school_id)
                        
                        if program_id and program_id not in unique_program_ids:
                            program_data = program_parent_data.get(program_id)
                            if program_data:
                                return_docs.append(program_data)
                                generated_program_ids.append(program_id)
                                unique_program_ids.add(program_id)
                except Exception:
                    continue
        except Exception:
            pass
        
        return return_docs, generated_school_ids, generated_program_ids, content
        
    except Exception:
        return [], [], [], []