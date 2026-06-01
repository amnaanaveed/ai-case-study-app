# 🩺 AI Clinical Case Study Orchestrator (CaseGen AI)

## 📌 Project Overview
The **AI Clinical Case Study Orchestrator** is a full-stack web application designed to automate professional clinical documentation for physiotherapists. It takes rough patient session notes, analyzes them using Advanced AI (LLMs), and instantly generates a comprehensive, perfectly formatted A4 clinical case study in PDF format. 

This project aims to reduce the administrative burden on healthcare professionals, allowing them to focus more on patient care rather than manual paperwork.

## 🚀 Live Demo
**Access the live application here:** [Insert your Vercel Link here]

## ✨ Key Features
* **Intelligent Clinical Parsing:** Converts rough, unstructured OPD session notes into structured clinical schemas (Demographics, Pain Profile, Systems Review, MSK Assessment, Treatment Plan, etc.).
* **Automated PDF Generation:** Uses `fpdf2` to mathematically render a beautiful, multi-page, clinic-ready PDF report.
* **Cloud Storage Integration:** Automatically uploads the generated confidential case studies securely to Google Drive using the Google Drive API.
* **Real-time Validation:** Smart UI that alerts the user if essential clinical information (like pain scale or patient age) is missing from the notes.
* **Modern UI/UX:** Built with React, offering a clean, responsive, and seamless clinical dashboard experience.

## 🛠️ Technology Stack
* **Frontend:** React.js, Vite, CSS (Responsive UI)
* **Backend:** FastAPI (Python), RESTful APIs
* **AI & NLP:** Integrated with High-Performance AI APIs (Gemini / Groq) for rapid clinical text generation.
* **PDF Engine:** `fpdf2` (Mathematical layout engine for secure document generation)
* **Cloud & Auth:** Google Drive API, OAuth 2.0
* **Deployment:** Vercel (Frontend), Render (Backend)

## 💻 Local Setup Instructions

If you want to run this project locally, follow these steps:

### 1. Clone the repository
\`\`\`bash
git clone https://github.com/amnaanaveed/ai-case-study-app.git
\`\`\`

### 2. Backend Setup (FastAPI)
\`\`\`bash
cd backend
python -m venv venv
source venv/Scripts/activate  # (For Windows)
pip install -r requirements.txt
uvicorn main:app --reload
\`\`\`

### 3. Frontend Setup (React)
Open a new terminal tab:
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

## 🎓 Academic Context
This project was developed as a comprehensive solution combining software engineering (AI Workflow Automation) with clinical physiotherapy knowledge. It bridges the gap between modern technology and clinical practice.

---
**Developed by:** Aamna Naveed
