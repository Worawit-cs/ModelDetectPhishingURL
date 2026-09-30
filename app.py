"""Streamlit interface for the offline PhiUSIIL URL classifier."""

import pandas as pd
import streamlit as st

from predictor import MAX_URL_LENGTH, try_predict_url


st.set_page_config(
    page_title="Phishing URL Detector",
    page_icon="🛡️",
    layout="centered",
)

st.markdown(
    """
    <style>
    .result-card { border-radius: 16px; padding: 1.25rem 1.4rem; margin: 1rem 0; }
    .result-card h2 { margin: 0 0 .35rem 0; }
    .legitimate { background: #e8f7ee; border: 2px solid #27a65a; color: #145c32; }
    .suspicious { background: #fff5d8; border: 2px solid #e0a800; color: #765500; }
    .phishing { background: #fde8e8; border: 2px solid #d83a3a; color: #7d1717; }
    </style>
    """,
    unsafe_allow_html=True,
)


def choose_example(url, note):
    st.session_state.url_input = url
    st.session_state.example_note = note
    st.session_state.check_example = True


st.title("🛡️ Phishing URL Detector")
st.write("ลองใส่ URL เพื่อดูผลจากโมเดลเป็น **Legitimate / Suspicious / Phishing**")

st.warning(
    """
**ข้อควรรู้ก่อนใช้**

- โมเดลตรวจจากข้อความ **URL เท่านั้น** ไม่ได้เปิดหน้าเว็บและไม่ได้ตรวจเนื้อหาภายในเว็บ
- ใช้เพื่อการศึกษา ไม่ใช่เครื่องมือความปลอดภัย และห้ามใช้ผล **Legitimate** เป็นหลักฐานว่า URL “ปลอดภัย”
- Legitimate URLs ใน Dataset เกือบทั้งหมดเป็นหน้าแรกของเว็บ ไม่มี path/query จึงมักทาย URL ปกติที่มี path ผิด
- โมเดลฝึกแบบ 2 คลาส (Phishing/Legitimate) ส่วน **Suspicious** สร้างจากช่วงคะแนนที่กำหนดบน Validation set
"""
)

st.subheader("ลองตัวอย่าง")
brand_col, typo_col, path_col = st.columns(3)
brand_col.button(
    "✅ แบรนด์จริง",
    width="stretch",
    on_click=choose_example,
    args=(
        "https://google.com",
        "แบรนด์จริง: domain หลักตรงกับรายชื่อแบรนด์ออฟไลน์ (ระบุ https:// ให้เหมือนข้อมูลฝึก)",
    ),
)
typo_col.button(
    "🎭 Typosquat",
    width="stretch",
    on_click=choose_example,
    args=("y0utube.com", "Typosquat สังเคราะห์: ใช้เลข 0 แทนตัว o ใน youtube"),
)
path_col.button(
    "🧭 URL มี path",
    width="stretch",
    on_click=choose_example,
    args=(
        "docs.python.org/3/tutorial/",
        "URL ปกติที่มี path แต่โมเดลมักทายเป็น Phishing เพราะข้อจำกัดของ Dataset",
    ),
)

if "url_input" not in st.session_state:
    st.session_state.url_input = ""

with st.form("url_check_form"):
    url = st.text_input(
        "URL ที่ต้องการตรวจ",
        key="url_input",
        placeholder="เช่น https://example.com/path",
        max_chars=MAX_URL_LENGTH,
    )
    submitted = st.form_submit_button("🔍 ตรวจ URL", type="primary", width="stretch")

if note := st.session_state.get("example_note"):
    st.caption(note)

should_check = submitted or st.session_state.pop("check_example", False)
if should_check:
    result, error = try_predict_url(url)
    if error:
        st.error(error)
    else:
        level, score, features = result
        presentation = {
            "Legitimate": ("✅", "legitimate", "คะแนน Phishing ต่ำ แต่ไม่ได้รับรองว่าเว็บปลอดภัย"),
            "Suspicious": ("⚠️", "suspicious", "คะแนนอยู่ในช่วงไม่แน่ชัด ควรตรวจสอบด้วยวิธีอื่นเพิ่มเติม"),
            "Phishing": ("🚨", "phishing", "รูปแบบ URL มีความเสี่ยงตามโมเดล หลีกเลี่ยงการเปิดหรือลงข้อมูล"),
        }
        icon, css_class, explanation = presentation[level]
        st.markdown(
            f'<div class="result-card {css_class}"><h2>{icon} {level}</h2>'
            f'<div>{explanation}</div><div><strong>Phishing score:</strong> {score:.2%}</div></div>',
            unsafe_allow_html=True,
        )

        with st.expander("ดูรายละเอียด — 18 features"):
            feature_table = pd.DataFrame(
                {"Feature": list(features), "Value": list(features.values())}
            )
            st.dataframe(feature_table, hide_index=True, width="stretch")

st.divider()
st.subheader("เกี่ยวกับโมเดล")
st.markdown(
    """
- Algorithm: **XGBoost (XGBClassifier)**
- Input: **18 URL-only features** รวม lexical และ typosquatting features
- ผลบน Test set: **Accuracy 97.62%**, **F1 (Phishing) 97.21%**

ตัวเลขข้างต้นมาจาก Test set ของ **Dataset เดียวกับที่ใช้พัฒนาโมเดล** ไม่ใช่ผลการทดสอบกับ URL ในโลกจริง
"""
)
