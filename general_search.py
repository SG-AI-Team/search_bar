from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from utils import read_json
from filters import *
import json
import time  # Add this import
from ranking import hybrid_retrieve

from llm_use import  handle_typo_errors, batch_relevance_filter

try:
    embedding_function = HuggingFaceEmbeddings(model="intfloat/e5-large-v2")
    vdb = Chroma(persist_directory="combined_db_new/", embedding_function=embedding_function)
except Exception as e:
    print(f"Error initializing vector database: {e}")
    vdb = None

def search(user_input: str, search_filter: str, school_ids: list, program_ids: list, more_flag: bool, is_filter_query: bool, filter_statements: list):
    
    total_start = time.time()  
    
    if vdb is None:
        print("Vector database not initialized")
        return [], [], [], []
    
    try:
        # Filter setup timing
        filter_start = time.time()
        search_kwargs = {
            "k": 15,  # Reduced from 30
            "fetch_k": 30,  # Reduced from 60  
            "lambda_mult": 0.4,
        }
        
        # Apply user filters first
        if filter_statements:
            try:
                print(f"Processing filter statements: {filter_statements}")
                user_filters = filters(filter_statements)
                print(f"Generated user filters: {user_filters}")
                
                # Separate metadata filters from document filters
                metadata_filters = []
                document_filters = []
                
                for filter_condition in user_filters:
                    if "where_document" in filter_condition:
                        document_filters.append(filter_condition["where_document"])
                    else:
                        metadata_filters.append(filter_condition)
                
                print(f"Metadata filters: {metadata_filters}")
                print(f"Document filters: {document_filters}")
                
                # Apply metadata filters
                if metadata_filters:
                    if len(metadata_filters) > 1:
                        search_kwargs['filter'] = {"$and": metadata_filters}
                    else:
                        search_kwargs['filter'] = metadata_filters[0]
                
                # Apply document filters
                if document_filters:
                    if len(document_filters) > 1:
                        search_kwargs['where_document'] = {"$and": document_filters}
                    else:
                        search_kwargs['where_document'] = document_filters[0]
            except Exception as e:
                print(f"Error processing filter statements: {e}")
                # Continue with default search_kwargs
        
        # Apply exclusion filters
        if more_flag == True:
            try:
                if search_filter == 'schools':
                    exclude_filter = exclude_ids(school_ids, [], search_filter)
                elif search_filter == 'programs':                
                    exclude_filter = exclude_ids([], program_ids, search_filter)
                else :
                    exclude_filter = exclude_ids(school_ids, program_ids, search_filter)
                    
                if exclude_filter:  
                    if 'filter' in search_kwargs:
                        search_kwargs['filter'] = {"$and": [search_kwargs['filter'], exclude_filter]}
                    else:
                        search_kwargs['filter'] = exclude_filter
            except Exception as e:
                print(f"Error applying exclusion filters: {e}")
        
        if is_filter_query == True:
            try:
                if 'rewritten_query' in locals() and rewritten_query != '':
                    not_exclude_filter_statments = not_exclude_ids(school_ids, program_ids)
                    if not_exclude_filter_statments:
                        if 'filter' in search_kwargs:
                            search_kwargs['filter'] = {"$and": [search_kwargs['filter'], not_exclude_filter_statments]}
                        else:
                            search_kwargs['filter'] = not_exclude_filter_statments
            except Exception as e:
                print(f"Error applying filter query filters: {e}")
        
        print(f"⏱️ Filter setup took: {time.time() - filter_start:.2f}s")
        
        print("=== FINAL SEARCH KWARGS ===")
        print(json.dumps(search_kwargs, indent=2))
        print("===========================")
        
        # Retriever creation timing
        retriever_start = time.time()
        try:
            retriever = vdb.as_retriever(
                search_type="mmr",
                search_kwargs=search_kwargs
            )
        except Exception as e:
            print(f"Error creating retriever: {e}")
            return [], [], [], []
        print(f"⏱️ Retriever creation took: {time.time() - retriever_start:.2f}s")

        # Typo correction timing - THIS IS LIKELY THE BOTTLENECK
        typo_start = time.time()
        try:
            # Skip LLM for very short queries or empty queries
            if len(user_input.strip()) < 3 or not user_input.strip():
                rewritten_query = user_input
                print("Skipped typo correction for short/empty query")
            else:
                rewritten_query = handle_typo_errors(user_input)
            print(f"Original query: {user_input}")
            print(f"Rewritten query: {rewritten_query}")
        except Exception as e:
            print(f"Error in typo correction: {e}")
            rewritten_query = user_input
        print(f"⏱️ Typo correction took: {time.time() - typo_start:.2f}s")

        # JSON loading timing
        json_start = time.time()
        try:
            school_parent_data = read_json("school_parent_json.json")
            program_parent_data = read_json("program_parent_json.json")
        except Exception as e:
            print(f"Error reading parent data files: {e}")
            return [], [], [], []
        print(f"⏱️ JSON loading took: {time.time() - json_start:.2f}s")

        # Vector search timing
        search_start = time.time()
        if search_filter == 'schools':
            try:
                print("Applying hybrid similarity + global rank sorting...")
                k = search_kwargs.get('k', 15)  
                if rewritten_query == '':
                    k = 2000 
                
                # Extract filters properly for hybrid_retrieve
                metadata_filter = search_kwargs.get('filter')
                document_filter = search_kwargs.get('where_document')
                
                content = hybrid_retrieve(
                    vdb=vdb, 
                    query=rewritten_query, 
                    k=k, 
                    filter=metadata_filter,
                    where_document=document_filter
                )
            except Exception as e:
                print(f"Error in hybrid_retrieve: {e}")
                return [], [], [], []
        else:
            # Use normal retriever for programs or all
            try:
                content = retriever.invoke(rewritten_query)
                print(f"Raw retriever returned {len(content)} documents")
            except Exception as e:
                print(f"Error in retriever.invoke: {e}")
                return [], [], [], []
        print(f"⏱️ Vector search took: {time.time() - search_start:.2f}s")

        # Relevance filter timing - ANOTHER LIKELY BOTTLENECK
        relevance_start = time.time()
        try:
            # Skip relevance filter for empty queries or very short queries
            if not rewritten_query.strip() or len(rewritten_query.strip()) < 3:
                relevant_docs = content
                print("Skipped relevance filtering for short/empty query")
            else:
                # Pass only metadata filters to relevance filter, not document filters
                metadata_only_kwargs = {k: v for k, v in search_kwargs.items() if k != 'where_document'}
                relevant_docs = batch_relevance_filter(rewritten_query, content)
            print(f"After relevance filtering: {len(relevant_docs)} documents")
        except Exception as e:
            print(f"Error in relevance filtering: {e}")
            relevant_docs = content  # Use all content as fallback
        print(f"⏱️ Relevance filtering took: {time.time() - relevance_start:.2f}s")

        # Document processing timing
        processing_start = time.time()
        return_docs = []
        generated_school_ids = []
        generated_program_ids = []

        unique_school_ids = set() 
        unique_program_ids = set()
        
        try:
            for i, doc in enumerate(relevant_docs):
                try:
                    school_id = doc.metadata.get('school_id')
                    program_id = doc.metadata.get('program_id')

                    if search_filter == 'schools':
                        if school_id and school_id not in unique_school_ids:
                            try:
                                school_data = school_parent_data[school_id]
                                return_docs.append(school_data)
                                generated_school_ids.append(school_id)
                                unique_school_ids.add(school_id)
                            except KeyError:
                                print(f"School {school_id} not found in parent data")
                            except Exception as e:
                                print(f"Error processing school {school_id}: {e}")

                    elif search_filter == 'programs':
                        if program_id and program_id not in unique_program_ids:
                            try:
                                program_data = program_parent_data[program_id]
                                return_docs.append(program_data)
                                generated_program_ids.append(program_id)
                                unique_program_ids.add(program_id)
                            except KeyError:
                                print(f"Program {program_id} not found in parent data")
                            except Exception as e:
                                print(f"Error processing program {program_id}: {e}")
                            
                    else:  # search_filter == 'all'
                        if school_id and school_id not in unique_school_ids:
                            try:
                                school_data = school_parent_data[school_id]
                                return_docs.append(school_data)
                                generated_school_ids.append(school_id)
                                unique_school_ids.add(school_id)
                            except KeyError:
                                print(f"School {school_id} not found in parent data")
                            except Exception as e:
                                print(f"Error processing school {school_id}: {e}")
                        
                        if program_id and program_id not in unique_program_ids:
                            try:
                                program_data = program_parent_data[program_id]
                                return_docs.append(program_data)
                                generated_program_ids.append(program_id)
                                unique_program_ids.add(program_id)
                            except KeyError:
                                print(f"Program {program_id} not found in parent data")
                            except Exception as e:
                                print(f"Error processing program {program_id}: {e}")
                except Exception as e:
                    print(f"Error processing document {i}: {e}")
                    continue  # Skip this document and continue with the next
        except Exception as e:
            print(f"Error processing relevant documents: {e}")
        
        print(f"⏱️ Document processing took: {time.time() - processing_start:.2f}s")

        print(f"Final results: {len(return_docs)} documents")
        print(f"School IDs: {generated_school_ids}")
        print(f"Program IDs: {generated_program_ids}")
        
        print(f"🎯 TOTAL SEARCH TIME: {time.time() - total_start:.2f}s")
        print(content)
        
        return return_docs, generated_school_ids, generated_program_ids, content
        
    except Exception as e:
        print(f"Unexpected error in search function: {e}")
        return [], [], [], []