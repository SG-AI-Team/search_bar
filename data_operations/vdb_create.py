import os
import shutil
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def create_vdb(list_of_document_objects):
    embedding_function = HuggingFaceEmbeddings(model="intfloat/e5-large-v2", model_kwargs={"device": "cpu"})
    
    # Check if database directory exists
    db_path = "data/search_db"
    if os.path.exists(db_path):
        # Remove existing database
        shutil.rmtree(db_path)
        print(f"Existing database at {db_path} removed")
    
    # Create new database
    Chroma.from_documents(
        documents=list_of_document_objects, 
        embedding=embedding_function, 
        persist_directory=db_path
    )
    print(f"New database created at {db_path}")