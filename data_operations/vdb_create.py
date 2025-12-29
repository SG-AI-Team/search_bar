import os
import shutil
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def create_vdb(list_of_document_objects):
    embedding_function = HuggingFaceEmbeddings(model="intfloat/e5-large-v2", model_kwargs={"device": "cpu"})
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to get to the project root, then to data/search_db
    db_path = os.path.join(os.path.dirname(script_dir), "data", "search_db")
    
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
    
    print(f"Database created at {db_path}")