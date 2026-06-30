# HƯỚNG DẪN THIẾT LẬP VÀ CHẠY DỰ ÁN AES_LLM

---

## 1. Thiết lập Môi trường ảo (Virtual Environment)
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

### Bước 4: Cài đặt các thư viện cần thiết
Nâng cấp pip và tiến hành cài đặt toàn bộ thư viện từ tệp `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Các bước chạy dự án

### Bước 1: Xử lý dữ liệu tự động (Giai đoạn 1)
Đảm bảo bạn đã đặt các tệp dữ liệu thô vào thư mục `data/raw/` (như `dataset/train_final.csv`, `dataset/test_final.csv`, `Raw IELTS essays/collected_ielts_data.csv`).

Kích hoạt môi trường ảo `.venv` (nếu chưa) và thực thi script xử lý:
```bash
python scripts/run_data_preprocessing.py
```
*   **Kết quả:** Script tự động làm sạch văn bản, loại bỏ rò rỉ dữ liệu (data leakage) giữa tập train/test, khử trùng lặp và chia tách dữ liệu theo phân tầng điểm số. Các tệp sạch `train.csv`, `val.csv`, `test.csv`, và `rag_knowledge_base.csv` sẽ được xuất vào thư mục `data/processed/`.

---

### Bước 2: Thiết lập Vector Database cho RAG (Giai đoạn 2)
Sau khi có dữ liệu sạch tại `data/processed/`, chúng ta tiến hành sinh cơ sở dữ liệu Vector để chạy RAG:

1.  **Mở VS Code** tại thư mục dự án `T:\5 - Summer 2026\AES_LLM`.
2.  Mở tệp notebook **`notebooks/5_rag_setup.ipynb`**.
3.  Chọn Kernel cho notebook:
    *   Click vào nút **"Select Kernel"** ở góc trên cùng bên phải.
    *   Chọn **"Python Environments..."** -> Chọn đường dẫn trỏ tới môi trường ảo `.venv` bạn vừa thiết lập.
4.  Nhấp vào **"Run All"** để chạy toàn bộ các ô lệnh.
    *   **Kết quả:** Notebook nạp mô hình embedding `BAAI/bge-large-en-v1.5`, mã hóa ngữ nghĩa toàn bộ bài viết trong tập train và lưu cơ sở dữ liệu vector ChromaDB tại thư mục `data/processed/chroma_db/`.

---

### Bước 3: Thử nghiệm Truy xuất & Sinh Prompt kết hợp RAG
1.  Mở và chạy tệp **`notebooks/6_rag_test.ipynb`** (Sử dụng Kernel `.venv`):
    *   **Mục đích:** Thử nghiệm tìm kiếm tương đồng trên một bài luận ngẫu nhiên để xác định tính ổn định của cơ sở dữ liệu vector.
2.  Mở và chạy tệp **`notebooks/7_rag_prompt_engineering.ipynb`** (Sử dụng Kernel `.venv`):
    *   **Mục đích:** Ghép nối ngữ cảnh truy xuất RAG với đề bài mới thành prompt hoàn chỉnh dạng JSON để sẵn sàng chuyển qua Giai đoạn 3 (Fine-tuning mô hình 1-LoRA).

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
