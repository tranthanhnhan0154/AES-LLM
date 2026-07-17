import os
import sys
from dotenv import load_dotenv

# Tìm đường dẫn đến file .env ở thư mục gốc dự án và nạp
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import pandas as pd
from sklearn.model_selection import train_test_split

# Đảm bảo có thể import được file data_utils.py khi chạy script từ bất kỳ thư mục nào
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import data_utils

# --- Cấu hình các hằng số đường dẫn ---
DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DATA_PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

RAW_TRAIN_FILE = os.path.join(DATA_RAW_DIR, "dataset", "train_final.csv")
RAW_TEST_FILE = os.path.join(DATA_RAW_DIR, "dataset", "test_final.csv")

PROCESSED_TRAIN_FILE = os.path.join(DATA_PROCESSED_DIR, "train.csv")
PROCESSED_VAL_FILE = os.path.join(DATA_PROCESSED_DIR, "val.csv")
PROCESSED_TEST_FILE = os.path.join(DATA_PROCESSED_DIR, "test.csv")
RAG_KB_FILE = os.path.join(DATA_PROCESSED_DIR, "rag_knowledge_base.csv")

def main():
    print("="*60)
    print(" BẮT ĐẦU QUY TRÌNH TIỀN XỬ LÝ DỮ LIỆU TỰ ĐỘNG (GIAI ĐOẠN 1) ")
    print("="*60)

    # 1. Đọc dữ liệu thô
    print("\n[1/6] Đang tải dữ liệu thô từ data/raw...")
    try:
        df_train = data_utils.load_csv(RAW_TRAIN_FILE)
        df_test = data_utils.load_csv(RAW_TEST_FILE)
        print(f"Đã load df_train: {df_train.shape[0]} dòng")
        print(f"Đã load df_test: {df_test.shape[0]} dòng")
    except Exception as e:
        print(f"Lỗi tải file: {e}")
        sys.exit(1)

    # 2. Loại bỏ cột trống không cần thiết
    if 'error' in df_train.columns:
        df_train = df_train.drop(columns=['error'])
        print("Đã loại bỏ cột 'error' trống trong tập train.")

    # 3. Làm sạch văn bản và chuẩn hóa dữ liệu
    print("\n[2/6] Đang làm sạch ký tự thừa (\\n, \\r, \\t, khoảng trắng)...")
    
    # Làm sạch các cột văn bản chính
    for col in ['essay', 'prompt']:
        df_train[col] = df_train[col].astype(str).apply(data_utils.clean_whitespace)
        df_test[col] = df_test[col].astype(str).apply(data_utils.clean_whitespace)
    
    # Riêng cột band, làm sạch triệt để ký tự xuống dòng
    df_train['band'] = df_train['band'].astype(str).str.strip().str.replace(r'[\r\n\t]+', '', regex=True)
    df_test['band'] = df_test['band'].astype(str).str.strip().str.replace(r'[\r\n\t]+', '', regex=True)

    # Điền giá trị rỗng cho các cột lỗi bằng chuỗi "None"
    mistake_cols = ['LR_Mistakes', 'LR_Corrections', 'GRA_Mistakes', 'GRA_Corrections']
    for col in mistake_cols:
        df_train[col] = df_train[col].fillna("None").astype(str).apply(data_utils.clean_whitespace)
        df_test[col] = df_test[col].fillna("None").astype(str).apply(data_utils.clean_whitespace)
    
    print(f"Hoàn thành làm sạch văn bản. Kích thước hiện tại:")
    print(f"  - df_train: {df_train.shape}")
    print(f"  - df_test : {df_test.shape}")

    # 3.5. Loại bỏ bài viết quá dài (trên 1000 từ)
    print("\n[2.5/6] Đang lọc bài viết quá dài (trên 1000 từ) trong tập Train...")
    MAX_WORD_LIMIT = 1000
    df_train['word_count'] = df_train['essay'].apply(lambda x: len(str(x).split()))
    too_long_count = (df_train['word_count'] > MAX_WORD_LIMIT).sum()
    print(f"Phát hiện {too_long_count} bài viết có độ dài vượt quá {MAX_WORD_LIMIT} từ trong tập Train.")
    df_train = df_train[df_train['word_count'] <= MAX_WORD_LIMIT].drop(columns=['word_count'])
    print(f"Đã loại bỏ các bài viết quá dài. Kích thước tập Train: {df_train.shape[0]} dòng")

    # 4. Kiểm tra và loại bỏ rò rỉ dữ liệu (Data Leakage)
    print("\n[3/6] Đang xử lý rò rỉ dữ liệu (Data Leakage) chéo giữa Train và Test...")
    leaked_set, num_leaked = data_utils.check_leakage(df_train, df_test, 'essay', 'essay')
    
    if num_leaked > 0:
        print(f"Cảnh báo: Phát hiện {num_leaked} bài viết trong tập Train trùng với tập Test!")
        # Loại bỏ các bài viết bị rò rỉ khỏi tập Train
        df_train = df_train[~df_train['essay'].isin(df_test['essay'])]
        print(f"Đã loại bỏ rò rỉ. Kích thước tập Train mới: {df_train.shape[0]} dòng")
    else:
        print("Không phát hiện rò rỉ dữ liệu giữa Train và Test.")

    # 5. Khử trùng lặp nội bộ (Deduplication)
    print("\n[4/6] Đang khử trùng lặp bài viết nội bộ trong từng tập...")
    initial_train_len = len(df_train)
    df_train = df_train.drop_duplicates(subset=['essay'])
    removed_train = initial_train_len - len(df_train)
    
    initial_test_len = len(df_test)
    df_test = df_test.drop_duplicates(subset=['essay'])
    removed_test = initial_test_len - len(df_test)
    
    print(f"Đã xóa {removed_train} bài viết trùng lặp trong tập Train.")
    print(f"Đã xóa {removed_test} bài viết trùng lặp trong tập Test.")
    print(f"Kích thước tập Train: {df_train.shape}")
    print(f"Kích thước tập Test : {df_test.shape}")

    # 6. Phân chia tập dữ liệu Train/Val theo Phân tầng (Stratified Train/Val Split)
    print("\n[5/6] Đang phân chia tập Train thành Train (90%) và Val (10%) với phân tầng...")
    
    # Loại bỏ các nhóm điểm Overall_Band có ít hơn 2 mẫu để tránh lỗi hàm stratified split
    band_counts = df_train['Overall_Band'].value_counts()
    rare_bands = band_counts[band_counts < 2].index
    if len(rare_bands) > 0:
        print(f"Loại bỏ các nhóm điểm có ít hơn 2 mẫu để đảm bảo phân tầng: {list(rare_bands)}")
        df_train = df_train[~df_train['Overall_Band'].isin(rare_bands)]

    # Chia tập dữ liệu
    df_train_split, df_val_split = train_test_split(
        df_train,
        test_size=0.10,
        random_state=42,
        stratify=df_train['Overall_Band']
    )
    print(f"Phân chia thành công:")
    print(f"  - Tập Train SFT (90%): {df_train_split.shape[0]} dòng")
    print(f"  - Tập Val SFT (10%)  : {df_val_split.shape[0]} dòng")

    # 7. Lưu kết quả ra file trong processed/
    print("\n[6/6] Đang xuất dữ liệu sạch ra thư mục data/processed/...")
    try:
        data_utils.save_csv(df_train_split, PROCESSED_TRAIN_FILE)
        data_utils.save_csv(df_val_split, PROCESSED_VAL_FILE)
        data_utils.save_csv(df_test, PROCESSED_TEST_FILE)
        # RAG Knowledge Base chỉ được nhân bản từ tập Train
        data_utils.save_csv(df_train_split, RAG_KB_FILE)
        print("\nGIAI ĐOẠN 1 ĐÃ HOÀN THÀNH!")
        print("="*60)
    except Exception as e:
        print(f"Lỗi ghi tệp tin: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
