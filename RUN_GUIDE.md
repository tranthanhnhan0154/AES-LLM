# HƯỚNG DẪN THIẾT LẬP VÀ CHẠY DỰ ÁN AES_LLM

Tệp tin này hướng dẫn chi tiết các bước từ việc tạo môi trường ảo (Virtual Environment), cài đặt thư viện, đến chạy quy trình xử lý dữ liệu (Giai đoạn 1), RAG (Giai đoạn 2), Fine-Tuning (Giai đoạn 3), và Đánh giá & Triển khai Web App (Giai đoạn 4).

---

## 1. Thiết lập Môi trường ảo (Virtual Environment)

Môi trường ảo giúp cô lập các thư viện của dự án, tránh xung đột phiên bản hệ thống.

### Bước 1: Mở Terminal hoặc Command Prompt
Di chuyển (cd) vào thư mục gốc của dự án:
```bash
cd "T:\5 - Summer 2026\AES_LLM"
```

### Bước 2: Tạo môi trường ảo `.venv`
Thực thi lệnh Python để khởi tạo môi trường ảo:
```bash
python -m venv .venv
```
*(Thư mục `.venv` mới sẽ xuất hiện trong thư mục dự án).*

### Bước 3: Kích hoạt môi trường ảo
Tùy thuộc vào Hệ điều hành và Terminal bạn sử dụng, gõ lệnh kích hoạt tương ứng:

*   **Windows (PowerShell):**
    ```powershell
    .venv\Scripts\Activate.ps1
    ```
    *Lưu ý: Nếu gặp lỗi quyền thực thi (Execution Policy) trên PowerShell, hãy chạy lệnh sau trước khi kích hoạt:*
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
    ```
*   **Windows (Command Prompt - cmd):**
    ```cmd
    .venv\Scripts\activate.bat
    ```
*   **macOS / Linux (Bash/Zsh):**
    ```bash
    source .venv/bin/activate
    ```

> Sau khi kích hoạt thành công, bạn sẽ thấy ký hiệu `(.venv)` xuất hiện ở đầu dòng lệnh của Terminal.

### Bước 4: Cài đặt các thư viện cần thiết (Tối ưu GPU CUDA)
Cài đặt PyTorch với chỉ mục CUDA trước, sau đó cài đặt requirements:
```bash
# 1. Cài đặt Torch GPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# 2. Cài đặt các thư viện cốt lõi
pip install -r requirements.txt

# 3. Cài đặt Triton cho Windows (Bản build cộng đồng dành cho Python 3.10)
pip install https://github.com/woct0rdho/triton-windows/releases/download/v3.0.0/triton-3.0.0-cp310-cp310-win_amd64.whl

# 4. Cài đặt Unsloth tăng tốc SFT
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

---

## 2. Các bước chạy dự án

### Bước 1: Xử lý dữ liệu tự động (Giai đoạn 1)
Đảm bảo bạn đã đặt các tệp dữ liệu thô vào thư mục `data/raw/` (như `dataset/train_final.csv`, `dataset/test_final.csv`, `Raw IELTS essays/collected_ielts_data.csv`).

Kích hoạt môi trường ảo `.venv` (nếu chưa) và thực thi script xử lý:
```bash
python scripts/run_data_preprocessing.py
```
*   **Kết quả:** Script tự động làm sạch văn bản, loại bỏ rò rỉ dữ liệu (data leakage) giữa tập train/test, khử trùng lặp nội bộ và loại bỏ các bài viết quá dài (>1000 từ). Các tệp sạch `train.csv`, `val.csv`, `test.csv`, và `rag_knowledge_base.csv` sẽ được xuất vào thư mục `data/processed/`.

---

### Bước 2: Thiết lập Vector Database cho RAG (Giai đoạn 2)
Sau khi có dữ liệu sạch tại `data/processed/`, chúng ta tiến hành sinh cơ sở dữ liệu Vector để chạy RAG:

1.  **Mở VS Code** tại thư mục dự án `T:\5 - Summer 2026\AES_LLM`.
2.  Mở tệp notebook **`notebooks/5_rag_setup.ipynb`**.
3.  Chọn Kernel cho notebook:
    *   Click vào nút **"Select Kernel"** ở góc trên cùng bên phải.
    *   Chọn **"Python Environments..."** -> Chọn đường dẫn trỏ tới môi trường ảo `.venv` bạn vừa thiết lập.
4.  Nhấp vào **"Run All"** để chạy toàn bộ các ô lệnh.
    *   **Kết quả:** Notebook nạp mô hình embedding `BAAI/bge-large-en-v1.5`, tự động phát hiện GPU/CUDA (hoặc CPU nếu không có) để mã hóa ngữ nghĩa toàn bộ bài viết trong tập train và lưu cơ sở dữ liệu vector ChromaDB tại thư mục `data/processed/chroma_db/`.

---

### Bước 3: Thử nghiệm Truy xuất & Sinh Prompt kết hợp RAG
1.  Mở và chạy tệp **`notebooks/6_rag_test.ipynb`** (Sử dụng Kernel `.venv`):
    *   **Mục đích:** Thử nghiệm tìm kiếm tương đồng trên một bài luận ngẫu nhiên để xác định tính ổn định của cơ sở dữ liệu vector.
2.  Mở và chạy tệp **`notebooks/7_rag_prompt_engineering.ipynb`** (Sử dụng Kernel `.venv`):
    *   **Mục đích:** Ghép nối ngữ cảnh truy xuất RAG với đề bài mới thành prompt hoàn chỉnh dạng JSON.

---

### Bước 4: Huấn luyện 1-LoRA & Hợp nhất mô hình (Giai đoạn 3)
1.  Mở và chạy tệp **`notebooks/8_1lora_finetuning.ipynb`** (Kernel `.venv`):
    *   **Mục đích:** Huấn luyện một adapter LoRA duy nhất chấm điểm đồng thời cả 4 tiêu chí IELTS Task 2.
    *   *Lưu ý:* Hãy cắm sạc laptop liên tục để tránh sụt điện năng của GPU.
2.  **Khởi động lại (Restart) Jupyter Kernel** để giải phóng VRAM.
3.  Mở và chạy tệp **`notebooks/9_model_merge.ipynb`** (Kernel `.venv`):
    *   **Mục đích:** Hợp nhất (merge) trọng số của adapter vào mô hình nền để tạo mô hình hợp nhất float16 và 4-bit.

---

### Bước 5: Đánh giá & Triển khai ứng dụng Web (Giai đoạn 4)

#### 1. Lượng hóa mô hình sang GGUF & Cài đặt trên Ollama
Để mô hình chạy siêu nhẹ và siêu nhanh cục bộ trên laptop:
1.  **Lượng hóa mô hình:** Sử dụng Unsloth để xuất tệp lượng hóa GGUF hoặc chạy convert từ mô hình merged 16-bit:
    *   *Tệp tin xuất ra:* `T:\5 - Summer 2026\AES_LLM\merged_model_16bit_gguf/merged_model_16bit.Q4_K_M.gguf`
2.  **Tạo mô hình trên Ollama:**
    Mở Command Prompt/Terminal và chạy lệnh sau để tạo mô hình `llama3-1-aes-8b` từ tệp `Modelfile` đã thiết lập sẵn:
    ```bash
    ollama create llama3-1-aes-8b -f Modelfile
    ```
3.  **Khởi chạy mô hình trên Ollama Server:**
    ```bash
    ollama run llama3-1-aes-8b
    ```

#### 2. Chạy đánh giá học thuật (Quantitative Evaluation)
1.  **Khởi động lại Jupyter Kernel** để giải phóng VRAM của các tiến trình python khác (chỉ chạy Ollama).
2.  Mở và chạy tệp **`notebooks/11_model_evaluation.ipynb`** (Kernel `.venv`):
    *   **Mục đích:** Đánh giá điểm số QWK (Quadratic Weighted Kappa) và MAE (Mean Absolute Error) của mô hình trên tập Test độc lập thông qua Ollama API.

#### 3. Chạy ứng dụng Chấm điểm IELTS (FastAPI + Streamlit Web App)
1.  **Khởi động Backend API (FastAPI):**
    Mở một cửa sổ Terminal mới, kích hoạt môi trường ảo `.venv` và khởi chạy máy chủ API:
    ```bash
    python src/api/app.py
    ```
    *(API sẽ chạy tại cổng `http://127.0.0.1:8000`)*.
2.  **Khởi động Giao diện Web (Streamlit UI):**
    Mở thêm một cửa sổ Terminal mới, kích hoạt môi trường ảo `.venv` và chạy:
    ```bash
    streamlit run scripts/web_app.py
    ```
    *(Trình duyệt web sẽ tự động mở trang giao diện tại địa chỉ `http://localhost:8501`)*.

---

## 3. Khắc phục sự cố & Reset quy trình

Nếu bạn chỉnh sửa logic xử lý dữ liệu và muốn chạy lại từ đầu:
1.  Xóa thư mục dữ liệu đã xử lý để tránh lỗi không khớp chiều Vector:
    ```powershell
    # Trên PowerShell Windows:
    Remove-Item -Path "data/processed/*" -Recurse -Force
    ```
2.  Chạy lại tệp tự động hóa dữ liệu:
    ```bash
    python scripts/run_data_preprocessing.py
    ```
3.  Chạy lại notebook `5_rag_setup.ipynb` để xây dựng lại Vector Database.
