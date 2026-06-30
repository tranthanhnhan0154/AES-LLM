import os
import re
import pandas as pd

def load_csv(file_path):
    """
    Đọc tệp CSV và xử lý lỗi nếu không tìm thấy tệp.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Lỗi: Không tìm thấy tệp tin dữ liệu tại '{file_path}'")
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        raise IOError(f"Lỗi khi đọc tệp tin CSV '{file_path}': {str(e)}")

def clean_whitespace(text):
    """
    Làm sạch văn bản: Loại bỏ ký tự xuống dòng (\n, \r), tab (\t) 
    và rút gọn khoảng trắng dư thừa về khoảng trắng đơn.
    """
    if pd.isna(text):
        return ""
    text = str(text).strip()
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def check_leakage(df1, df2, col1='essay', col2='essay'):
    """
    Kiểm tra sự giao thoa (rò rỉ dữ liệu) giữa cột col1 của df1 và col2 của df2.
    Trả về tập hợp các giá trị bị trùng lặp và số lượng trùng lặp.
    """
    set1 = set(df1[col1].astype(str).apply(clean_whitespace).unique())
    set2 = set(df2[col2].astype(str).apply(clean_whitespace).unique())
    intersection = set1.intersection(set2)
    return intersection, len(intersection)

def save_csv(df, file_path):
    """
    Lưu DataFrame ra tệp CSV, tự động tạo thư mục cha nếu chưa tồn tại.
    """
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    try:
        df.to_csv(file_path, index=False)
        print(f"Đã lưu tệp tin thành công tại: {os.path.abspath(file_path)}")
    except Exception as e:
        raise IOError(f"Lỗi khi lưu tệp tin CSV '{file_path}': {str(e)}")
