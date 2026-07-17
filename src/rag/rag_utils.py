import os
from dotenv import load_dotenv

# Tìm đường dẫn đến file .env ở thư mục gốc dự án và nạp trước khi import thư viện HF
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import torch
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def load_vector_db(persist_directory, embedding_model_name="BAAI/bge-large-en-v1.5"):
    """
    Tải cơ sở dữ liệu vector ChromaDB từ thư mục lưu trữ cục bộ.
    Mô hình mặc định là BAAI/bge-large-en-v1.5 (context 512 tokens).
    Tự động chọn CUDA nếu có, ngược lại sử dụng CPU.
    """
    if not os.path.exists(persist_directory):
        raise FileNotFoundError(f"Lỗi: Thư mục Vector DB tại '{persist_directory}' không tồn tại.")
        
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_kwargs = {"device": device}
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name, model_kwargs=model_kwargs)
    
    vectordb = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    return vectordb

def retrieve_examples(vectordb, query_essay, k=2):
    """
    Truy xuất k bài viết tham khảo tương đồng nhất với bài viết đầu vào.
    """
    # Thực hiện tìm kiếm tương đồng trên cơ sở dữ liệu vector
    docs = vectordb.similarity_search(query_essay, k=k)
    return docs

def format_rag_context(retrieved_docs):
    """
    Chuyển đổi danh sách các Document truy xuất từ ChromaDB thành chuỗi văn bản ngữ cảnh (Context)
    để nạp vào Prompt Template.
    """
    context_str = ""
    for idx, doc in enumerate(retrieved_docs):
        # Trích xuất nội dung bài viết và điểm số tương ứng
        content = doc.page_content
        overall_band = doc.metadata.get("Overall_Band", "Unknown")
        
        context_str += f"--- REFERENCE ESSAY {idx + 1} (Overall Band: {overall_band}) ---\n"
        context_str += f"{content}\n\n"
    return context_str.strip()

def format_evaluation_prompt(prompt_template, context, essay_prompt, essay_text):
    """
    Ghép các tham số (Context, Prompt đề bài, Bài viết mới) vào Prompt Template.
    """
    # Khớp các biến trong template
    # Template sử dụng: {context} và {question}
    # Trong đó, {question} là sự kết hợp của Prompt đề bài và Essay mới cần chấm điểm
    question_str = f"Prompt: {essay_prompt}\nEssay: {essay_text}"
    
    formatted_prompt = prompt_template.format(
        context=context,
        question=question_str
    )
    return formatted_prompt
