import os
import re
import json
import httpx
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Nạp cấu hình từ .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "src"))

from rag import rag_utils

app = FastAPI(
    title="IELTS Essay Scorer API Backend",
    description="FastAPI Backend sử dụng 1-LoRA + RAG để tự động chấm điểm bài viết IELTS Task 2",
    version="1.0"
)

# Cấu hình CORS để cho phép Web UI (Streamlit) gọi API chéo cổng
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình các hằng số
VECTOR_DB_DIR = os.path.join(BASE_DIR, "data", "processed", "chroma_db")
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL_NAME = "llama3-1-aes-8b"

# Khởi tạo Vector DB
try:
    print(f"Đang tải Vector Database từ: {VECTOR_DB_DIR}...")
    vectordb = rag_utils.load_vector_db(VECTOR_DB_DIR)
    print("✔ Tải Vector Database thành công!")
except Exception as e:
    print(f"Cảnh báo: Không thể tải Vector Database. Lỗi: {e}")
    vectordb = None

# Định nghĩa cấu trúc dữ liệu đầu vào
class EssayInput(BaseModel):
    prompt: str
    essay: str

# Hàm regex để trích xuất JSON sạch từ phản hồi của LLM
def extract_clean_json(text):
    text = text.strip()
    # Tìm kiếm chuỗi nằm giữa dấu ngoặc nhọn đầu tiên và cuối cùng
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text

# Template prompt hệ thống gộp 4 tiêu chí chấm điểm được import tập trung từ rag_utils
from rag.rag_utils import IELTS_EVAL_PROMPT_TEMPLATE

@app.post("/api/evaluate")
async def evaluate(input_data: EssayInput):
    if not vectordb:
        raise HTTPException(status_code=500, detail="Vector Database chưa được khởi tạo thành công trên hệ thống.")
        
    try:
        # 1. Truy xuất RAG từ ChromaDB (K=2)
        print("Đang truy xuất bài viết tham chiếu từ ChromaDB...")
        retrieved_docs = rag_utils.retrieve_examples(vectordb, input_data.essay, k=2)
        context_str = rag_utils.format_rag_context(retrieved_docs)
        
        # 2. Xây dựng prompt hoàn chỉnh
        final_prompt = rag_utils.format_evaluation_prompt(
            prompt_template=IELTS_EVAL_PROMPT_TEMPLATE,
            context=context_str,
            essay_prompt=input_data.prompt,
            essay_text=input_data.essay
        )
        
        # 3. Gọi Ollama API bất đồng bộ (Thêm format: json và tăng timeout lên 120s)
        print("Đang gửi yêu cầu chấm điểm tới Ollama Server...")
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": OLLAMA_MODEL_NAME,
                "prompt": final_prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            }
            response = await client.post(OLLAMA_API_URL, json=payload)
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Ollama trả về mã lỗi: {response.status_code}")
                
            result = response.json()
            raw_response = result.get("response", "").strip()
            
        # 4. Trích xuất và parse JSON sạch
        clean_json_str = extract_clean_json(raw_response)
        try:
            parsed_json = json.loads(clean_json_str)
            return {
                "status": "success",
                "evaluation": parsed_json,
                "references": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    } for doc in retrieved_docs
                ]
            }
        except json.JSONDecodeError as je:
            print(f"Lỗi parse JSON: {je}. Nội dung thô: {raw_response}")
            raise HTTPException(
                status_code=500, 
                detail=f"Mô hình không trả về định dạng JSON hợp lệ. Nội dung thô: {raw_response}"
            )
            
    except Exception as e:
        print(f"Lỗi hệ thống trong quá trình xử lý: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ nội bộ: {str(e)}")

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "vector_db_loaded": vectordb is not None,
        "model_configured": OLLAMA_MODEL_NAME
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("API Swagger Docs: http://127.0.0.1:8000/docs")
    print("Trang chủ (tự redirect): http://127.0.0.1:8000")
    print("="*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
