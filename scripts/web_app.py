import streamlit as st
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="IELTS Writing Task 2 Essay Scorer",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Backend URL
API_URL = "http://127.0.0.1:8000/api/evaluate"

st.title("IELTS Writing Task 2 - Automated Essay Scorer")
st.markdown("Hệ thống chấm điểm bài viết IELTS tự động sử dụng mô hình **Llama-3.1-8B (1-LoRA) + RAG**.")

# Cấu trúc Sidebar
st.sidebar.header("Thông tin cấu hình")
st.sidebar.markdown("""
*   **Mô hình:** Llama-3.1-8B-AES (1-LoRA)
*   **Vector DB:** ChromaDB (BGE-Large-En-v1.5)
*   **Tham số RAG:** K=2 (Ví dụ tương đồng)
*   **Nhiệt độ (Temp):** 0.1 (JSON nhất quán)
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### Hướng dẫn sử dụng:")
st.sidebar.markdown("""
1. Nhập đề bài IELTS Task 2.
2. Dán bài viết của bạn (tối thiểu 150 từ, khuyến nghị >250 từ).
3. Nhấn nút **Chấm điểm & Phân tích** và đợi 5-10 giây để nhận kết quả chi tiết.
""")

# Tạo layout chính
col_input, col_results = st.columns([1, 1])

with col_input:
    st.subheader("Nhập bài luận cần chấm")
    
    # Ô nhập đề bài
    prompt_input = st.text_area(
        "Đề bài (IELTS Writing Prompt):", 
        value="", 
        placeholder="Nhập hoặc dán đề bài IELTS Writing Task 2 vào đây...",
        height=100
    )
    
    # Ô nhập bài luận của học sinh
    essay_input = st.text_area(
        "Bài viết (Student Essay):", 
        value="", 
        placeholder="Nhập hoặc dán bài viết của học sinh vào đây (tối thiểu 150 từ)...",
        height=350
    )
    
    # Tính số từ tạm thời
    word_count = len(essay_input.strip().split()) if essay_input.strip() else 0
    st.info(f"Độ dài bài viết: **{word_count} từ**")
    
    # Nút submit
    submit_button = st.button("Chấm điểm & Phân tích", type="primary", use_container_width=True)

# Hàm vẽ biểu đồ Radar Chart điểm số
def draw_radar_chart(scores):
    categories = ['Task Response', 'Coherence/Cohesion', 'Lexical Resource', 'Grammar Range/Acc']
    values = [scores['TR'], scores['CC'], scores['LR'], scores['GRA']]
    
    # Lặp lại giá trị đầu để khép kín vòng tròn
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 5), subplot_kw=dict(polar=True))
    
    # Vẽ các vùng điểm nền
    ax.fill(angles, values, color='#1f77b4', alpha=0.25)
    ax.plot(angles, values, color='#1f77b4', linewidth=2)
    
    # Cấu hình các nhãn tiêu chí
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=10)
    
    # Thiết lập giới hạn dải điểm IELTS [0 - 9]
    ax.set_ylim(0, 9)
    ax.set_yticks([2, 4, 6, 8])
    ax.set_yticklabels(['2.0', '4.0', '6.0', '8.0'], color="grey", fontsize=8)
    
    plt.tight_layout()
    return fig

# Xử lý khi nhấn nút submit
if submit_button:
    if not prompt_input.strip() or not essay_input.strip():
        st.error("Vui lòng điền đầy đủ cả Đề bài và Bài viết trước khi chấm.")
    else:
        with col_results:
            with st.spinner("Đang phân tích bài viết và đối chiếu RAG..."):
                try:
                    # Gửi POST request tới FastAPI Backend
                    payload = {"prompt": prompt_input, "essay": essay_input}
                    response = requests.post(API_URL, json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        eval_data = result.get("evaluation", {})
                        references = result.get("references", [])
                        
                        # 1. Trích xuất điểm số
                        tr_score = float(eval_data.get("Task_Response", {}).get("Band", 0.0))
                        cc_score = float(eval_data.get("Coherence_and_Cohesion", {}).get("Band", 0.0))
                        lr_score = float(eval_data.get("Lexical_Resource", {}).get("Band", 0.0))
                        gra_score = float(eval_data.get("Grammatical_Range_and_Accuracy", {}).get("Band", 0.0))
                        
                        # Tính Overall Band Score theo quy tắc IELTS (làm tròn về 0.25/0.75 gần nhất)
                        raw_overall = (tr_score + cc_score + lr_score + gra_score) / 4.0
                        overall_band = round(raw_overall * 2) / 2 # Làm tròn về 0.5 gần nhất
                        
                        # 2. Hiển thị điểm số dạng số lớn
                        st.subheader("Điểm số đánh giá tổng quan")
                        col_ovr, col_metrics = st.columns([1, 2])
                        
                        with col_ovr:
                            st.metric(label="Overall Band Score", value=f"{overall_band:.1f}")
                            
                        with col_metrics:
                            st.markdown(f"""
                            *   **Task Response (TR):** `{tr_score:.1f}`
                            *   **Coherence and Cohesion (CC):** `{cc_score:.1f}`
                            *   **Lexical Resource (LR):** `{lr_score:.1f}`
                            *   **Grammatical Range and Accuracy (GRA):** `{gra_score:.1f}`
                            """)
                        
                        # 3. Vẽ biểu đồ Radar Chart
                        st.markdown("#### Biểu đồ năng lực các tiêu chí")
                        scores_dict = {'TR': tr_score, 'CC': cc_score, 'LR': lr_score, 'GRA': gra_score}
                        radar_fig = draw_radar_chart(scores_dict)
                        st.pyplot(radar_fig)
                        
                        # 4. Hiển thị nhận xét chi tiết
                        st.markdown("---")
                        st.subheader("Nhận xét chi tiết từng tiêu chí")
                        
                        with st.expander("1. Task Response (TR)", expanded=True):
                            st.markdown(eval_data.get("Task_Response", {}).get("Comment", "Không có nhận xét."))
                            
                        with st.expander("2. Coherence and Cohesion (CC)", expanded=True):
                            st.markdown(eval_data.get("Coherence_and_Cohesion", {}).get("Comment", "Không có nhận xét."))
                            
                        with st.expander("3. Lexical Resource (LR - Từ vựng)", expanded=True):
                            st.markdown(eval_data.get("Lexical_Resource", {}).get("Comment", "Không có nhận xét."))
                            # Hiển thị bảng lỗi từ vựng
                            lr_mistakes = eval_data.get("Lexical_Resource", {}).get("Mistakes", [])
                            lr_corrections = eval_data.get("Lexical_Resource", {}).get("Corrections", [])
                            if lr_mistakes:
                                st.markdown("**Các lỗi từ vựng & gợi ý sửa đổi:**")
                                lr_df = pd.DataFrame({
                                    "Từ viết sai / không tự nhiên": lr_mistakes,
                                    "Gợi ý sửa đổi": lr_corrections
                                })
                                st.table(lr_df)
                                
                        with st.expander("4. Grammatical Range and Accuracy (GRA - Ngữ pháp)", expanded=True):
                            st.markdown(eval_data.get("Grammatical_Range_and_Accuracy", {}).get("Comment", "Không có nhận xét."))
                            # Hiển thị bảng lỗi ngữ pháp
                            gra_mistakes = eval_data.get("Grammatical_Range_and_Accuracy", {}).get("Mistakes", [])
                            gra_corrections = eval_data.get("Grammatical_Range_and_Accuracy", {}).get("Corrections", [])
                            if gra_mistakes:
                                st.markdown("**Các lỗi ngữ pháp & gợi ý sửa đổi:**")
                                gra_df = pd.DataFrame({
                                    "Lỗi cấu trúc câu": gra_mistakes,
                                    "Gợi ý sửa đổi": gra_corrections
                                })
                                st.table(gra_df)
                                
                        with st.expander("Lời khuyên chung (General Feedback)", expanded=True):
                            st.markdown(f"*{eval_data.get('General_Feedback', 'Không có lời khuyên chung.')}*")
                            
                        # 5. Hiển thị tham chiếu RAG
                        st.markdown("---")
                        st.subheader("Bài luận tham khảo từ cơ sở tri thức (RAG References)")
                        for idx, ref in enumerate(references):
                            ref_score = ref.get("metadata", {}).get("Overall_Band", "Unknown")
                            with st.expander(f"Ví dụ tương đồng {idx+1} (Overall Band: {ref_score})"):
                                st.text(ref.get("content", ""))
                                
                    else:
                        st.error(f"Lỗi kết nối tới Backend API. Chi tiết: {response.text}")
                        
                except Exception as ex:
                    st.error(f"Không thể kết nối tới Backend API tại {API_URL}. Vui lòng kiểm tra xem bạn đã khởi động máy chủ FastAPI chưa. Chi tiết lỗi: {ex}")
