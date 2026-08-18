import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Tìm đường dẫn đến file .env ở thư mục gốc dự án và nạp trước khi import thư viện HF
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import torch
# pyrefly: ignore [missing-import]
from langchain_community.vectorstores import Chroma
# pyrefly: ignore [missing-import]
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

def retrieve_examples(vectordb, query_essay, k=2, exclude_essay_text=None):
    """
    Truy xuất k bài viết tham khảo với bài viết đầu vào sử dụng chiến lược Đa dạng hóa (Diversity Retrieval).
    - Tìm kiếm một tập hợp rộng hơn (ví dụ: 15 bài tương đồng nhất).
    - Khử trùng lặp nội dung bài viết nếu có.
    - Loại bỏ bài viết trùng với exclude_essay_text (nếu được cung cấp) để chống Target Leakage lúc train.
    - Sắp xếp và chọn ra phổ điểm rộng nhất (ví dụ k=2 sẽ lấy 1 bài thấp điểm nhất và 1 bài cao điểm nhất).
    """
    # Tìm kiếm tập hợp 15 bài viết tương đồng nhất để có phổ điểm (tăng lên để phòng trừ bài bị loại trừ)
    search_k = max(15, (k + 1) * 3)
    docs = vectordb.similarity_search(query_essay, k=search_k)
    
    if not docs:
        return []
        
    # Khử trùng lặp các tài liệu giống nhau về nội dung văn bản và loại trừ bài viết leakage
    unique_docs = []
    seen_contents = set()
    
    # Chuẩn hóa văn bản loại trừ (nếu có)
    exclude_normalized = None
    if exclude_essay_text:
        exclude_normalized = " ".join(exclude_essay_text.split()).strip().lower()
        
    for doc in docs:
        content_normalized = " ".join(doc.page_content.split()).strip().lower()
        
        # 1. Tránh trùng lặp nội dung RAG
        if content_normalized in seen_contents:
            continue
            
        # 2. Tránh Target Leakage (loại bỏ chính bài đang chấm)
        if exclude_normalized:
            # page_content trong ChromaDB lưu dưới dạng "Prompt: ... \n\nEssay: ..."
            if exclude_normalized in content_normalized:
                continue
                
        seen_contents.add(content_normalized)
        unique_docs.append(doc)
        
    if not unique_docs:
        unique_docs = docs
        
    # Sắp xếp các tài liệu theo điểm số Overall_Band tăng dần
    sorted_docs = sorted(unique_docs, key=lambda d: float(d.metadata.get("Overall_Band", 0.0)))
    
    if len(sorted_docs) <= k:
        return sorted_docs
        
    # Nếu k = 2, chọn bài thấp điểm nhất và cao điểm nhất để làm rộng phổ đối chiếu
    if k == 2:
        return [sorted_docs[0], sorted_docs[-1]]
    else:
        # Fallback cho k khác 2
        return sorted_docs[:k]

def format_rag_context(retrieved_docs):
    """
    Chuyển đổi danh sách các Document truy xuất từ ChromaDB thành chuỗi văn bản ngữ cảnh (Context)
    để nạp vào Prompt Template. Giới hạn tối đa 450 từ để tránh các bài viết ngoại lệ quá dài.
    """
    context_str = ""
    for idx, doc in enumerate(retrieved_docs):
        # Trích xuất nội dung bài viết và điểm số tương ứng
        content = doc.page_content
        overall_band = doc.metadata.get("Overall_Band", "Unknown")
        
        # Cắt bài mẫu về tối đa 450 từ (IELTS Task 2 thực tế hiếm khi vượt quá 400 từ)
        words = content.split()
        if len(words) > 450:
            content = " ".join(words[:450]) + "..."
            
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

IELTS_EVAL_PROMPT_TEMPLATE = """You are a highly experienced IELTS writing examiner. Your goal is to provide a precise and consistent evaluation of an essay by following a structured reasoning process.

**CONTEXT (Reference Essays with Scores):**
{context}

**NEW ESSAY TO GRADE:**
{question}

**EVALUATION PROCESS (Think step-by-step):**
1. Task Response (TR) Analysis: Assess how well the 'NEW ESSAY' addresses the prompt. Compare its quality to the TR scores in the 'CONTEXT'.
2. Coherence and Cohesion (CC) Analysis: Assess structure, paragraphing, and linking. Compare to CC scores in the 'CONTEXT'.
3. Lexical Resource (LR) Analysis: Assess range and accuracy of vocabulary. Compare to LR scores in the 'CONTEXT'.
4. Grammatical Range and Accuracy (GRA) Analysis: Assess grammar range and accuracy. Compare to GRA scores in the 'CONTEXT'.

**FINAL OUTPUT FORMAT (Strict JSON):**
Your entire response MUST be a single valid JSON object containing exactly these fields. Do NOT include markdown code blocks or explanations outside JSON.
{{
  "Task_Response": {{
    "Band": <score>,
    "Comment": "<brief justification>"
  }},
  "Coherence_and_Cohesion": {{
    "Band": <score>,
    "Comment": "<brief justification>"
  }},
  "Lexical_Resource": {{
    "Band": <score>,
    "Mistakes": ["<mistake1>", "<mistake2>"],
    "Corrections": ["<correction1>", "<correction2>"],
    "Comment": "<brief justification>"
  }},
  "Grammatical_Range_and_Accuracy": {{
    "Band": <score>,
    "Mistakes": ["<mistake1>", "<mistake2>"],
    "Corrections": ["<correction1>", "<correction2>"],
    "Comment": "<brief justification>"
  }},
  "General_Feedback": "<constructive feedback>"
}}

JSON Response:
"""
