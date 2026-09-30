# Phishing URL Detector ด้วย Streamlit

เว็บสำหรับทดลองใส่ URL แล้วดูผลจากโมเดล XGBoost เป็น 3 ระดับ: **Legitimate**, **Suspicious** และ **Phishing** โดยวิเคราะห์เฉพาะข้อความ URL แบบออฟไลน์ ไม่เปิดเว็บปลายทางและไม่บันทึก URL ที่ผู้ใช้กรอก

ผู้จัดทำ: **Worawit**

## โครงสร้างโปรเจกต์

```text
.
├── app.py
├── features.py
├── predictor.py
├── requirements.txt
├── model/
│   └── phishing_url_detector_v1.4.joblib
└── tests/
    ├── test_features.py
    └── test_predictor.py
```

## วิธีรันในเครื่อง

โปรเจกต์พัฒนาด้วย Python 3.10.12 และล็อกเวอร์ชัน dependency ที่ใช้โหลด model bundle ไว้ใน `requirements.txt`

```bash
cd streamlit_phishing_url_detector
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

เปิด URL ที่ Streamlit แสดงใน terminal (ปกติคือ `http://localhost:8501`) หากต้องการรัน tests ให้ติดตั้ง pytest เพิ่มเฉพาะ development environment:

```bash
python -m pip install pytest==8.4.2
pytest -q
```

## วิธี Deploy ฟรีบน Streamlit Community Cloud

1. สร้าง GitHub repository ใหม่และตั้งเป็น **Public**
2. นำไฟล์ทั้งหมดในโปรเจกต์นี้ขึ้น repository โดยต้อง commit ไฟล์ `model/phishing_url_detector_v1.4.joblib` ด้วย
3. ตรวจว่า `app.py` และ `requirements.txt` อยู่ใน root ของ repository หากเก็บโปรเจกต์เป็น subdirectory ให้ระบุ path ของ `app.py` ให้ตรงตอน deploy
4. เข้า [Streamlit Community Cloud](https://share.streamlit.io/) แล้ว Sign in/เชื่อมบัญชี GitHub
5. กด **Create app** หรือ **Deploy an app** เลือก repository, branch และ main file path เป็น `app.py`
6. เลือก Python version ให้ตรงกับที่ทดสอบ (Python 3.10) ใน Advanced settings หากตัวเลือกนี้มีให้ตั้ง
7. กด **Deploy** และตรวจ build log หากติดตั้ง dependency ไม่สำเร็จ
8. เมื่อ push commit ใหม่ Community Cloud จะ redeploy แอปให้อัตโนมัติ

เอกสารอ้างอิงการ deploy: [Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [การจัดไฟล์](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization) และ [การกำหนด dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)

## ความปลอดภัยและความเป็นส่วนตัว

- แอปไม่ `fetch` หรือเปิด URL ที่กรอก และไม่มีการใช้ `requests`/`urllib.request` กับ URL นั้น
- แอปไม่บันทึกหรือ log URL ที่ผู้ใช้กรอก
- จำกัด input ไม่เกิน 2,000 ตัวอักษร และตรวจรูปแบบก่อนส่งเข้าโมเดล
- ผล Legitimate ไม่ได้แปลว่า URL ปลอดภัย ควรใช้บริการ reputation, browser protection และการตรวจเนื้อหาเว็บร่วมด้วย

## ข้อจำกัดของโมเดล

- โมเดลใช้ข้อความ URL เท่านั้น ไม่ตรวจ DNS, certificate, redirect, reputation หรือเนื้อหาเว็บ
- Legitimate URLs ในชุดข้อมูลเกือบทั้งหมดเป็นหน้าแรกของเว็บที่ไม่มี path/query โมเดลจึงมักทาย URL ปกติที่มี path เป็น Phishing เช่น `docs.python.org/3/tutorial/` และ `github.com/openai/openai-python`
- Logic จาก notebook เติม `http://` ให้ input ที่ไม่มี scheme และโมเดลไวต่อรูปแบบนี้มาก: `google.com`/`youtube.com` ถูกทายเป็น Phishing แต่รูปแบบ `https://google.com`/`https://youtube.com` ถูกทายเป็น Legitimate
- โมเดลฝึก 2 คลาส คือ Phishing/Legitimate ส่วน Suspicious มาจากช่วงคะแนนที่กำหนดจาก Validation set ไม่ใช่คลาสที่สามจากข้อมูลฝึก
- Accuracy 97.62% และ F1 (Phishing) 97.21% เป็นผลจาก Test set ของ Dataset เดียวกัน ไม่ใช่ผลกับ URL ในโลกจริง
- รายชื่อแบรนด์ 136 ชื่อมาจาก model bundle และใช้แบบออฟไลน์ จึงไม่ครอบคลุมทุกแบรนด์หรือ domain ใหม่

## แหล่งข้อมูล

- Prasad, A. และ Chandra, S. (2024), [PhiUSIIL Phishing URL (Website), UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/967/phiusiil%26), ใบอนุญาต CC BY 4.0
- Feature extraction และ threshold อ้างอิงจาก `Phishing_URL_Detection_Colab_v1_4.ipynb` ของโปรเจกต์นี้โดยคง logic การคำนวณเดิม
