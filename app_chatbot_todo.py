# ============================================================
# CHATBOT PHÂN TÍCH PHẢN HỒI - V2.1 (CÓ SO SÁNH 2 NHÓM)
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re
from collections import Counter

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    from wordcloud import WordCloud
except ImportError:
    WordCloud = None

try:
    from underthesea import sentiment, word_tokenize
except ImportError:
    sentiment = None
    word_tokenize = None

# ============================================================
# CACHING
# ============================================================
@st.cache_data
def load_stopwords():
    default = {'và','của','là','các','cho','với','có','không','một','này','để','trong','được','như','cũng','từ','đó','rất','nên','khi','thì','mà','lại','nhưng','hay','về','đang','đã','sẽ','bị','ở','vào','ra'}
    try:
        with open("stopwords_vi.txt", "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return default

STOPWORDS = load_stopwords()

@st.cache_resource
def get_sentiment_model():
    return sentiment

# ============================================================
# CORE FUNCTIONS
# ============================================================
def clean_text(text: str) -> str:
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    return re.sub(r'\s+', ' ', text).strip()

def analyze_feedback(text: str) -> dict:
    if not text or len(text.strip()) < 2:
        return {"text": text, "sentiment": "neutral", "confidence": 0.5, "keywords": [], "timestamp": datetime.now().isoformat()}
    
    text_clean = clean_text(text)
    model = get_sentiment_model()
    
    try:
        label = model(text_clean) if model else "neutral"
    except:
        label = "neutral"
    
    try:
        tokens = word_tokenize(text_clean) if word_tokenize else text_clean.split()
        words = [w for w in tokens if w not in STOPWORDS and len(w) > 1]
        keywords = [w for w, _ in Counter(words).most_common(12)]
    except:
        keywords = []

    confidence = 0.88 if label == "positive" else 0.80 if label == "negative" else 0.65

    return {
        "text": text,
        "sentiment": label,
        "confidence": round(confidence, 2),
        "keywords": keywords,
        "timestamp": datetime.now().isoformat()
    }

def render_analysis(result: dict) -> str:
    emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(result["sentiment"], "😐")
    return f"""
**{emoji} {result['sentiment'].upper()}** — {result['confidence']:.0%}
**Phản hồi:** {result['text']}
**Từ khóa:** {", ".join(result['keywords'][:8]) if result['keywords'] else "Không có"}
"""

# ============================================================
# FILE & PERSISTENCE
# ============================================================
def handle_file_upload(group_name: str):
    file = st.sidebar.file_uploader(f"📤 Upload cho **{group_name}**", type=["csv", "xlsx", "txt"], key=f"upload_{group_name}")
    if file is None:
        return []
    # (logic đọc file giống trước)
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            return [line.strip() for line in file.getvalue().decode("utf-8").splitlines() if line.strip()]
        col = next((c for c in df.columns if any(k in c.lower() for k in ["feedback","phanhoi","text","comment"])), df.columns[0])
        return df[col].dropna().astype(str).tolist()
    except:
        st.error("Không đọc được file")
        return []

def save_history(history):
    try:
        with open("history.json", "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_history():
    try:
        with open("history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# ============================================================
# VISUALIZATION
# ============================================================
def render_wordcloud(keywords, title):
    if not keywords or WordCloud is None or plt is None:
        return
    wc = WordCloud(width=700, height=350, background_color="white", colormap="viridis").generate(" ".join(keywords))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(title, fontsize=14)
    st.pyplot(fig)

def render_comparison_timeline(history1, history2):
    st.subheader("📈 Timeline So sánh")
    df1 = pd.DataFrame(history1)
    df2 = pd.DataFrame(history2)
    
    for df, name, color in [(df1, "Nhóm 1 (Trước)", "#1f77b4"), (df2, "Nhóm 2 (Sau)", "#ff7f0e")]:
        if len(df) > 0:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            mapping = {"positive": 1, "neutral": 0, "negative": -1}
            df["score"] = df["sentiment"].map(mapping)
            daily = df.set_index("timestamp")["score"].resample("D").mean()
            st.line_chart(daily.rename(name), color=color, use_container_width=True)

# ============================================================
# MAIN
# ============================================================
def main():
    st.set_page_config(page_title="Phân tích Phản hồi SV", page_icon="🎓", layout="wide")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = load_history()
    if "compare_mode" not in st.session_state:
        st.session_state.compare_mode = False
    if "group1" not in st.session_state:
        st.session_state.group1 = []
    if "group2" not in st.session_state:
        st.session_state.group2 = []

    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.title("⚙️ Cài đặt")
        
        compare_mode = st.toggle("🔄 Bật Chế độ So sánh 2 Nhóm", value=st.session_state.compare_mode)
        st.session_state.compare_mode = compare_mode

        st.divider()
        
        if compare_mode:
            st.subheader("Nhóm 1 (Trước)")
            g1 = handle_file_upload("Nhóm 1")
            if g1 and st.button("Phân tích Nhóm 1", type="primary"):
                for text in g1:
                    res = analyze_feedback(text)
                    st.session_state.group1.append(res)
                st.success(f"Đã phân tích {len(g1)} phản hồi Nhóm 1")
                st.rerun()

            st.subheader("Nhóm 2 (Sau)")
            g2 = handle_file_upload("Nhóm 2")
            if g2 and st.button("Phân tích Nhóm 2", type="primary"):
                for text in g2:
                    res = analyze_feedback(text)
                    st.session_state.group2.append(res)
                st.success(f"Đã phân tích {len(g2)} phản hồi Nhóm 2")
                st.rerun()
        else:
            uploaded = handle_file_upload("Tất cả")
            if uploaded and st.button("Phân tích tất cả", type="primary"):
                for text in uploaded:
                    res = analyze_feedback(text)
                    st.session_state.history.append(res)
                    st.session_state.messages.append({"role": "user", "content": text})
                    st.session_state.messages.append({"role": "assistant", "content": render_analysis(res)})
                save_history(st.session_state.history)
                st.rerun()

        if st.session_state.history:
            csv = pd.DataFrame(st.session_state.history).to_csv(index=False).encode()
            st.download_button("📥 Tải CSV", csv, "feedback_history.csv")

    # ==================== MAIN AREA ====================
    st.title("🤖 Phân tích Phản hồi Sinh viên")
    
    if st.session_state.compare_mode:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📍 Nhóm 1 - Trước cải tiến")
            if st.session_state.group1:
                df1 = pd.DataFrame(st.session_state.group1)
                st.bar_chart(df1["sentiment"].value_counts())
                all_kw1 = [k for item in st.session_state.group1 for k in item.get("keywords", [])]
                render_wordcloud(all_kw1, "Word Cloud - Nhóm 1")
            else:
                st.info("Chưa có dữ liệu Nhóm 1")
        
        with col2:
            st.subheader("📍 Nhóm 2 - Sau cải tiến")
            if st.session_state.group2:
                df2 = pd.DataFrame(st.session_state.group2)
                st.bar_chart(df2["sentiment"].value_counts())
                all_kw2 = [k for item in st.session_state.group2 for k in item.get("keywords", [])]
                render_wordcloud(all_kw2, "Word Cloud - Nhóm 2")
            else:
                st.info("Chưa có dữ liệu Nhóm 2")

        # So sánh chi tiết
        if st.session_state.group1 and st.session_state.group2:
            st.divider()
            st.subheader("📊 Bảng So Sánh Chi Tiết")
            
            df1 = pd.DataFrame(st.session_state.group1)
            df2 = pd.DataFrame(st.session_state.group2)
            
            compare_df = pd.DataFrame({
                "Chỉ số": ["Tổng phản hồi", "Tích cực (%)", "Tiêu cực (%)", "Trung lập (%)"],
                "Nhóm 1 (Trước)": [
                    len(df1),
                    (df1["sentiment"] == "positive").mean()*100,
                    (df1["sentiment"] == "negative").mean()*100,
                    (df1["sentiment"] == "neutral").mean()*100
                ],
                "Nhóm 2 (Sau)": [
                    len(df2),
                    (df2["sentiment"] == "positive").mean()*100,
                    (df2["sentiment"] == "negative").mean()*100,
                    (df2["sentiment"] == "neutral").mean()*100
                ]
            })
            st.dataframe(compare_df, use_container_width=True)
            
            render_comparison_timeline(st.session_state.group1, st.session_state.group2)

    else:
        # Chế độ bình thường
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if prompt := st.chat_input("Nhập phản hồi sinh viên (có thể nhiều dòng)..."):
            lines = [line.strip() for line in prompt.splitlines() if line.strip()]
            for line in lines:
                result = analyze_feedback(line)
                st.session_state.history.append(result)
                st.session_state.messages.append({"role": "user", "content": line})
                st.session_state.messages.append({"role": "assistant", "content": render_analysis(result)})
            save_history(st.session_state.history)
            st.rerun()

if __name__ == "__main__":
    main()