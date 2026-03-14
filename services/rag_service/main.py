# rag_service.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from functools import lru_cache
from typing import Optional

app = FastAPI(title="DTHub RAG Service")

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DB_PATH = os.path.join(BASE_DIR, "faiss_index")

class QueryRequest(BaseModel):
    query: str
    k: int = 3

class QueryResponse(BaseModel):
    query: str
    result: str
    source_docs: list[str] = []

@lru_cache(maxsize=1)
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

@lru_cache(maxsize=1)
def load_retriever():
    """Load vector store và trả về retriever"""
    if not os.path.exists(VECTOR_DB_PATH):
        print(f"[ERROR] Vector DB path not found: {VECTOR_DB_PATH}")
        return None
    
    embeddings = get_embeddings()
    vectorstore = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)
    return vectorstore.as_retriever(search_kwargs={"k": 5})

@app.get("/health")
async def health():
    return {"status": "ok", "db_loaded": load_retriever() is not None}

@app.post("/search", response_model=QueryResponse)
async def search(request: QueryRequest):
    """Tìm kiếm kiến thức từ database RAG"""
    retriever = load_retriever()
    if not retriever:
        raise HTTPException(status_code=500, detail="RAG Database not loaded")
    
    try:
        query_lower = request.query.lower()
        docs = retriever.invoke(request.query)
        
        relevant_docs = []
        for d in docs:
            content = d.page_content.strip()
            # Hybrid scoring (simplified)
            score = 0
            if query_lower in content.lower():
                score += 10
            
            relevant_docs.append((content, score))
            
        # Sắp xếp theo score
        relevant_docs.sort(key=lambda x: x[1], reverse=True)
        
        if not relevant_docs:
            return QueryResponse(
                query=request.query,
                result="Xin lỗi, tôi không tìm thấy thông tin liên quan trong database nội bộ.",
                source_docs=[]
            )
            
        # Lấy top kết quả
        top_results = [doc[0] for doc in relevant_docs[:request.k]]
        final_result = "\n\n".join(top_results)
        
        return QueryResponse(
            query=request.query,
            result=final_result,
            source_docs=top_results
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5001)
