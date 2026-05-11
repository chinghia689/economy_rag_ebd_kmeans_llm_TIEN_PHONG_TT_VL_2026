# Chatbot Kinh Te Viet Nam

He thong hoi dap thong minh ve kinh te Viet Nam, su dung RAG (Retrieval-Augmented Generation) voi Energy-Based Distance Retriever va K-Means Clustering.

## Tong quan (Overview)

Du an xay dung mot chatbot chuyen ve linh vuc kinh te Viet Nam, ket hop:
- **Energy-Based Distance Retriever**: Thuat toan truy xuat tai lieu tinh vi hon Cosine Similarity thong thuong.
- **K-Means Clustering**: Nhom tai lieu theo cum ngữ nghĩa de tang toc truy xuat.
- **Multi-LLM Support**: Ho tro nhieu nha cung cap LLM (OpenAI, Google Gemini, Groq).
- **LangGraph Workflow**: Quan ly luong xu ly AI theo mo hinh State Machine.

Nguoi dung co the dat cau hoi ve kinh te va nhan cau tra loi dua tren co so du lieu tai lieu da duoc vector hoa.

---

## Yeu cau He thong (System Requirements)

- Python >= 3.10
- RAM toi thieu 4GB (khuyen nghi 8GB cho Embedding model)
- Dung luong o dia: ~2GB (bao gom vector store va model)
- He dieu hanh: Linux / macOS / Windows

---

## Cai dat & Chay thu cuc bo (Local Setup)

### 1. Clone va tao moi truong ao (Backend)

```bash
git clone git@github.com:chinghia689/economy_rag_ebd_kmeans_llm_TIEN_PHONG_TT_VL_2026.git
cd economy_rag_ebd_kmeans_llm_TIEN_PHONG_TT_VL_2026

python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 2. Cau hinh bien moi truong

```bash
cp .env.example .env
# Mo file .env va dien cac gia tri thuc (API keys, JWT secret, ...)
```

### 3. Xay dung Vector Store (lan dau)

```bash
python ingestion/vector_data_builder.py
```

### 4. Khoi dong Backend API

```bash
python chatbot/services/server.py
# Hoac:
uvicorn chatbot.services.server:app --host 0.0.0.0 --port 8001 --reload
```

### 5. Truy cap ung dung

- **Giao dien Web**: http://localhost:8001
- **API Docs (Swagger)**: http://localhost:8001/docs

---

## Cau hinh Bien Moi truong (Environment Variables)

Tao file `.env` tu mau `.env.example`. Cac bien bat buoc:

| Bien                   | Mo ta                                         | Vi du                                    |
|------------------------|-----------------------------------------------|------------------------------------------|
| DEFAULT_LLM            | LLM Provider mac dinh                        | openai                                   |
| KEY_API_OPENAI         | API Key cua OpenAI                            | sk-xxxxxxx                               |
| OPENAI_LLM_MODEL_NAME | Ten model OpenAI                              | gpt-4o-mini                              |
| GOOGLE_API_KEY         | API Key cua Google Gemini                     | AIzaSy...                                |
| GOOGLE_LLM_MODEL_NAME | Ten model Gemini                              | gemini-2.5-flash                         |
| GROQ_API_KEY           | API Key cua Groq                              | gsk_xxxxxxx                              |
| JWT_SECRET_KEY         | Khoa bi mat ky JWT (toi thieu 32 ky tu)       | thay-doi-key-nay-khi-deploy              |
| GOOGLE_CLIENT_ID       | Google OAuth Client ID                        | xxxx.apps.googleusercontent.com          |
| GOOGLE_CLIENT_SECRET   | Google OAuth Client Secret                    | GOCSPX-xxxxxxx                           |
| OAUTH_REDIRECT_URI     | Google OAuth Redirect URI                     | http://localhost:8001/api/v1/auth/google/callback/flutter |

**Luu y bao mat:**
- File `.env` KHONG DUOC commit len Git (da co trong `.gitignore`).
- File `.env.example` chi chua ten bien va mo ta, KHONG chua gia tri thuc.

---

## Cau truc Thu muc (Project Structure)

```text
project_root/
├── app/                        # Backend Core (Config, Schemas, Security)
│   ├── config.py               # Load bien moi truong tu .env
│   ├── logger.py               # He thong logging tap trung
│   ├── models/
│   │   └── schemas.py          # ApiSuccess, ApiError, PaginatedData
│   └── security/
│       └── security.py         # JWT Dependency, RBAC (get_current_user, get_current_admin)
├── chatbot/                    # AI Engine
│   ├── main.py                 # ChatbotRunner: Khoi tao LLM + Workflow
│   ├── services/
│   │   ├── server.py           # FastAPI Server chinh
│   │   ├── auth.py             # Google OAuth + Cloud-Sync Polling Login
│   │   └── files_rag_chat_agent.py  # RAG Agent (retrieve -> grade -> generate)
│   ├── utils/
│   │   ├── llm.py              # Multi-LLM factory (OpenAI, Gemini, Groq)
│   │   ├── base_db.py          # SQLite: Users, Login Sessions, Chat History
│   │   ├── jwt_utils.py        # JWT create/verify
│   │   ├── document_grader.py  # Batch Document Grading (1 API call)
│   │   ├── answer_generator.py # RAG Answer Generation
│   │   ├── custom_prompt.py    # Prompt templates
│   │   └── graph_state.py      # LangGraph State definition
│   └── data/                   # SQLite database files
├── ingestion/                  # Data Pipeline
│   ├── energy_kmeans.py        # Energy-Based Distance + K-Means Retriever
│   ├── model_embedding.py      # Vietnamese Embedding model
│   ├── chunks_document.py      # ChromaDB Manager
│   └── vector_data_builder.py  # Xay dung Vector Store
├── scoring/                    # Evaluation scripts (NDCG, MRR)
├── frontend/                   # Giao dien web (Vanilla JS + CSS)
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── utils/                      # Storage tap trung
│   ├── logs/                   # File log (app.log)
│   └── download/               # File export, assets
├── .env.example                # Mau bien moi truong
├── .gitignore                  # Quy tac bo qua file nhay cam
└── requirements.txt            # Python dependencies
```

---

## Danh sach API Endpoint (API Reference)

Backend chay tai `http://localhost:8001`.

### He thong (System)

| Method | Endpoint          | Xac thuc | Mo ta                     |
|--------|-------------------|----------|---------------------------|
| GET    | /api/health       | Khong    | Kiem tra trang thai server |

### Xac thuc (Auth)

| Method | Endpoint                               | Xac thuc | Mo ta                              |
|--------|----------------------------------------|----------|------------------------------------|
| POST   | /api/v1/auth/login-session             | Khong    | Tao phien cho dang nhap            |
| GET    | /api/v1/auth/login-session/{id}        | Khong    | Polling trang thai dang nhap       |
| GET    | /api/v1/auth/google/login/flutter      | Khong    | Redirect den Google OAuth          |
| GET    | /api/v1/auth/google/callback/flutter   | Khong    | Google callback (tao JWT)          |
| POST   | /api/v1/auth/verify                    | Khong    | Xac thuc JWT token                 |
| GET    | /api/v1/auth/me                        | Bearer   | Lay thong tin user hien tai        |

### Chat

| Method | Endpoint            | Xac thuc  | Mo ta                           |
|--------|---------------------|-----------|--------------------------------|
| POST   | /api/chat           | Optional  | Gui cau hoi, nhan tra loi AI   |
| GET    | /api/chat/history   | Bearer    | Lay lich su chat                |
| DELETE | /api/chat/history   | Bearer    | Xoa lich su chat                |

### Tac vu bat dong bo (Async Task)

| Method | Endpoint              | Xac thuc  | Mo ta                                  |
|--------|-----------------------|-----------|----------------------------------------|
| POST   | /api/task/chat        | Optional  | Khoi tao tac vu AI (background)        |
| GET    | /api/task/{task_id}   | Khong     | Polling trang thai tac vu              |

### File Download

| Method | Endpoint                      | Xac thuc | Mo ta                    |
|--------|-------------------------------|----------|--------------------------|
| GET    | /api/v1/download/{filename}   | Khong    | Tai file tu thu muc an toan |

---

## Huong dan Trien khai (Deployment)

### Tren Linux (Khong Docker)

```bash
# 1. Cai dat he thong
apt update && apt install python3-pip python3-venv

# 2. Clone va cai dat
git clone git@github.com:chinghia689/economy_rag_ebd_kmeans_llm_TIEN_PHONG_TT_VL_2026.git
cd economy_rag_ebd_kmeans_llm_TIEN_PHONG_TT_VL_2026

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Cau hinh moi truong
cp .env.example .env
# Dien cac gia tri thuc vao .env

# 4. Xay dung Vector Store
python ingestion/vector_data_builder.py

# 5. Chay server
python chatbot/services/server.py
```

---

## Lien he & Tai lieu Ky thuat

- Tai lieu Skill: `docs/DOCS-main/`
- Bao loi: Tao Issue tren GitHub repository.
