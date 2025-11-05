from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from utils import read_json
from filters import *
import json
from ranking import hybrid_retrieve

from llm_use import  handle_typo_errors, batch_relevance_filter

try:
    embedding_function = HuggingFaceEmbeddings(model="intfloat/e5-large-v2")
    vdb = Chroma(persist_directory="combined_db_new/", embedding_function=embedding_function)
except Exception as e:
    print(f"Error initializing vector database: {e}")
    vdb = None

def search(user_input: str, search_filter: str, school_ids: list, program_ids: list, more_flag: bool, is_filter_query: bool, filter_statements: list):
    
    if vdb is None:
        print("Vector database not initialized")
        return [], [], [], []
    
    try:
        search_kwargs = {
            "k": 30,  
            "fetch_k": 60,  
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
        
        print("=== FINAL SEARCH KWARGS ===")
        print(json.dumps(search_kwargs, indent=2))
        print("===========================")
        
        try:
            retriever = vdb.as_retriever(
                search_type="mmr",
                search_kwargs=search_kwargs
            )
        except Exception as e:
            print(f"Error creating retriever: {e}")
            return [], [], [], []

        try:
            rewritten_query = handle_typo_errors(user_input, search_kwargs)
            print(f"Original query: {user_input}")
            print(f"Rewritten query (English): {rewritten_query}")
        except Exception as e:
            print(f"Error in typo correction: {e}")
            rewritten_query = user_input  

        try:
            school_parent_data = read_json("school_parent_json.json")
            program_parent_data = read_json("program_parent_json.json")
        except Exception as e:
            print(f"Error reading parent data files: {e}")
            return [], [], [], []

        # ============================================
        # 🧠 HYBRID RANKING ONLY FOR SCHOOLS
        # ============================================
        if search_filter == 'schools':
            try:
                print("Applying hybrid similarity + global rank sorting...")
                if rewritten_query == '':
                    k = 1000
                else:
                    k = 30 
                
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
        # ============================================

        # Relevance filter
        try:
            # Pass only metadata filters to relevance filter, not document filters
            metadata_only_kwargs = {k: v for k, v in search_kwargs.items() if k != 'where_document'}
            relevant_docs = batch_relevance_filter(rewritten_query, content, metadata_only_kwargs)
            print(f"After relevance filtering: {len(relevant_docs)} documents")
        except Exception as e:
            print(f"Error in relevance filtering: {e}")
            relevant_docs = content  # Use all content as fallback

        return_docs = []
        generated_school_ids = []
        generated_program_ids = []

        unique_school_ids = set() 
        unique_program_ids = set()
        
        try:
            for i, doc in enumerate(relevant_docs):
                try:
                    print(f"Processing relevant doc {i}")
                    school_id = doc.metadata.get('school_id')
                    program_id = doc.metadata.get('program_id')

                    if search_filter == 'schools':
                        if school_id and school_id not in unique_school_ids:
                            try:
                                school_data = school_parent_data[school_id]
                                return_docs.append(school_data)
                                generated_school_ids.append(school_id)
                                unique_school_ids.add(school_id)
                                print(f"Added school: {school_id}")
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
                                print(f"Added program: {program_id}")
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
                                print(f"Added school: {school_id}")
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
                                print(f"Added program: {program_id}")
                            except KeyError:
                                print(f"Program {program_id} not found in parent data")
                            except Exception as e:
                                print(f"Error processing program {program_id}: {e}")
                except Exception as e:
                    print(f"Error processing document {i}: {e}")
                    continue  # Skip this document and continue with the next
        except Exception as e:
            print(f"Error processing relevant documents: {e}")

        print(f"Final results: {len(return_docs)} documents")
        print(f"School IDs: {generated_school_ids}")
        print(f"Program IDs: {generated_program_ids}")
        
        return return_docs, generated_school_ids, generated_program_ids, content
        
    except Exception as e:
        print(f"Unexpected error in search function: {e}")
        return [], [], [], []