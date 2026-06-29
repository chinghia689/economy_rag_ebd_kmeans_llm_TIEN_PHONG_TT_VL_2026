# Tai lieu thu vien va cong nghe

Cap nhat: 2026-06-29

Tai lieu nay tom tat cac thu vien, framework va cong nghe dang duoc su dung trong du an Chatbot Kinh Te Viet Nam (`Folder_All`). Thong tin duoc tong hop tu `requirements.txt`, `frontend_react/package.json`, `Dockerfile`, `docker-compose.yml` va cac entrypoint chinh cua backend/frontend.

## 1. Tong quan kien truc

Du an gom cac thanh phan chinh:

| Thanh phan | Cong nghe chinh | Vai tro |
|---|---|---|
| Backend API | Python, FastAPI, Uvicorn, Pydantic | Cung cap API chat, auth, admin, payment, health check |
| RAG/AI Engine | LangChain, LangGraph, ChromaDB, Sentence Transformers | Truy xuat tai lieu, cham diem ngu canh va sinh cau tra loi |
| Vector Database | ChromaDB | Luu embedding cua tai lieu kinh te |
| Embedding Model | `intfloat/multilingual-e5-base` | Tao vector cho cau hoi va tai lieu, ho tro tieng Viet |
| LLM Provider | OpenAI, Google Gemini, Groq | Sinh cau tra loi va ho tro cham diem tai lieu |
| App Database | SQLite | Luu user, login session, token, payment, chat history va runtime settings |
| Frontend | React, TypeScript, Vite, TailwindCSS | Giao dien nguoi dung, chat, dang nhap, pricing, admin |
| Deployment | Docker, Docker Compose, Nginx | Dong goi backend va trien khai production |

Luong xu ly chat chinh:

```text
Nguoi dung
  -> React Frontend
  -> FastAPI Backend
  -> GT1 Single-Vector ERC Retriever
  -> ChromaDB Vector Store
  -> DocumentGrader
  -> LLM sinh cau tra loi
  -> Tra ve frontend
```

## 2. Backend API

Backend duoc viet bang Python va chay qua `chatbot/services/server.py`.

| Thu vien / cong nghe | Khai bao | Vai tro trong du an |
|---|---|---|
| FastAPI | `fastapi>=0.115.0` | Framework xay dung REST API, khai bao route, middleware, dependency |
| Uvicorn | `uvicorn[standard]>=0.30.0` | ASGI server de chay FastAPI |
| Pydantic | `pydantic>=2.7.0` | Dinh nghia schema request/response va validate du lieu |
| python-multipart | `python-multipart>=0.0.9` | Ho tro parse form-data/form-urlencoded |
| typing-extensions | `typing-extensions>=4.12.0` | Bo sung type hints cho Python |
| SQLite | Thu vien built-in Python `sqlite3` | Luu du lieu ung dung tai `chatbot/data/login_sessions.db` |
| logging | Built-in Python | Ghi log ung dung qua `app/logger.py` |

Mot so API/nhom chuc nang backend:

- Chat API: nhan cau hoi, goi pipeline RAG va tra ve cau tra loi.
- Auth API: Google OAuth, JWT, login session, thong tin user.
- Admin API: cau hinh runtime, quan ly user, audit, database query.
- Payment API: nap token, kiem tra giao dich, tich hop SePay/VietQR.
- Public content API: noi dung public cho cac trang thong tin frontend.

## 3. Bao mat, xac thuc va thanh toan

| Thu vien / cong nghe | Khai bao | Vai tro |
|---|---|---|
| PyJWT | `PyJWT>=2.8.0` | Tao va xac thuc JWT token |
| passlib[bcrypt] | `passlib[bcrypt]>=1.7.4` | Hash va verify mat khau |
| bcrypt | `bcrypt>=4.1.0` | Thuat toan hash mat khau |
| httpx | `httpx>=0.27.0` | Goi HTTP bat dong bo/dong bo khi can tich hop dich vu ngoai |
| requests | `requests>=2.32.0` | Goi HTTP den API ben ngoai |
| Google OAuth | Cau hinh qua `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Dang nhap nguoi dung bang Google |
| SePay/VietQR | Cau hinh qua `SEPAY_API_KEY`, thong tin ngan hang | Kiem tra giao dich nap token |

Cac runtime settings quan trong duoc seed tu `.env` vao SQLite trong lan khoi dong dau tien. Sau do database la nguon cau hinh runtime chinh, vi vay thay doi `.env` khong tu dong ghi de cac setting da co trong database.

## 4. AI Engine va RAG

Pipeline AI su dung GT1 Single-Vector ERC:

```text
cau hoi
  -> embed(q) bang E5 embedding
  -> lay top-40 tai lieu tu ChromaDB
  -> gom cum bang K-Means, thu k=2..10
  -> chon k theo Silhouette Score
  -> tinh Energy Distance tu query vector den tung cum
  -> chon cum co Energy Distance nho nhat
  -> DocumentGrader loc tai lieu lien quan
  -> LLM sinh cau tra loi dua tren context
```

| Thu vien / cong nghe | Khai bao | Vai tro |
|---|---|---|
| LangChain | `langchain>=0.3.0` | Khung lam viec ket noi LLM, retriever, chain |
| langchain-core | `langchain-core>=0.3.0` | Thanh phan core cua LangChain |
| langchain-community | `langchain-community>=0.3.0` | Integration cong dong cua LangChain |
| langchain-openai | `langchain-openai>=0.2.0` | Ket noi LLM OpenAI |
| langchain-google-genai | `langchain-google-genai>=2.0.0` | Ket noi Google Gemini |
| langchain-groq | `langchain-groq>=0.2.0` | Ket noi Groq |
| LangGraph | `langgraph>=0.2.0` | Xay dung workflow RAG dang graph |
| ChromaDB | `chromadb>=0.5.0` | Vector database luu va truy xuat embedding |
| langchain-chroma | `langchain-chroma>=0.2.0` | Adapter LangChain cho ChromaDB |
| sentence-transformers | `sentence-transformers>=3.0.0` | Nen tang load embedding model |
| langchain-huggingface | `langchain-huggingface>=0.1.0` | Adapter embedding HuggingFace cho LangChain |
| intfloat/multilingual-e5-base | Load qua HuggingFace | Embedding model da ngon ngu, ho tro tieng Viet |
| scikit-learn | `scikit-learn>=1.5.0` | K-Means va Silhouette Score trong retrieval |
| scipy | `scipy>=1.13.0` | Tinh Energy Distance / xu ly vector |
| numpy | `numpy>=1.26.0` | Tinh toan ma tran va vector |
| tiktoken | `tiktoken>=0.7.0` | Dem token khi can tinh chi phi/gioi han |
| langchain-text-splitters | `langchain-text-splitters>=0.3.0` | Tach tai lieu thanh chunk |

### LLM provider duoc ho tro

| Provider | Bien cau hinh | Model mac dinh trong code |
|---|---|---|
| OpenAI | `KEY_API_OPENAI`, `OPENAI_LLM_MODEL_NAME` | `gpt-5-mini` |
| Google Gemini | `GOOGLE_API_KEY`, `GOOGLE_LLM_MODEL_NAME` | `gemini-2.5-flash` |
| Groq | `GROQ_API_KEY`, `GROQ_LLM_MODEL_NAME` | `llama-3.1-8b-instant` |

Provider mac dinh duoc cau hinh bang `DEFAULT_LLM`.

## 5. Xu ly du lieu va vector store

Data ingestion nam trong thu muc `ingestion/`.

| File / cong nghe | Vai tro |
|---|---|
| `ingestion/load_document.py` | Doc tai lieu nguon tu `Dataset_economy` |
| `ingestion/model_embedding.py` | Lazy-load embedding model E5 va them prefix `query:` / `passage:` |
| `ingestion/chunks_document.py` | Tach chunk va ghi vao ChromaDB |
| `ingestion/vector_data_builder.py` | Entry point xay dung vector database |
| `chroma_economy_db/` | Thu muc persist vector database |

Tham so chunking hien tai trong `vector_data_builder.py`:

| Tham so | Gia tri |
|---|---:|
| `chunk_size` | 600 |
| `chunk_overlap` | 80 |
| `persist_dir` | `./chroma_economy_db` |

Lenh build vector database:

```bash
python ingestion/vector_data_builder.py
```

## 6. Danh gia chat/RAG

Thu muc `scoring/` dung de sinh file ket qua va tinh diem pipeline.

| Thu vien / cong nghe | Khai bao | Vai tro |
|---|---|---|
| pandas | `pandas>=2.2.0` | Doc/ghi va xu ly bang du lieu danh gia |
| openpyxl | `openpyxl>=3.1.0` | Doc/ghi file Excel `.xlsx` |
| nltk | `nltk>=3.9.0` | Ho tro metric BLEU/ROUGE |
| ir_datasets | `ir_datasets>=0.5.0` | Ho tro benchmark/retrieval evaluation khi can |
| scikit-learn/numpy | Khai bao o nhom AI | Tinh cosine similarity va metric vector |

Metric dang duoc su dung:

- BLEU-2
- ROUGE-2 Recall / Precision / F1
- Cosine Similarity
- Mean Reciprocal Rank (MRR)
- Hit@5
- NDCG@5

Lenh sinh ket qua danh gia:

```bash
python -m scoring.create_eval
```

Lenh tinh diem:

```bash
python scoring/main.py --file scoring/GT1_eval_results.xlsx
```

## 7. Frontend

Frontend nam trong `frontend_react/`, su dung React + TypeScript + Vite.

| Thu vien / cong nghe | Khai bao | Vai tro |
|---|---|---|
| React | `react^18.3.1` | Xay dung UI component |
| React DOM | `react-dom^18.3.1` | Render React len DOM |
| TypeScript | `typescript~5.6.2` | Type checking cho frontend |
| Vite | `vite^5.4.10` | Dev server va build tool |
| React Router DOM | `react-router-dom^6.30.3` | Dieu huong route frontend |
| Zustand | `zustand^5.0.13` | Quan ly state phia client |
| react-markdown | `react-markdown^10.1.0` | Render Markdown trong cau tra loi chat |
| react-icons | `react-icons^5.6.0` | Icon UI |
| TailwindCSS | `tailwindcss^3.4.19` | Utility-first CSS framework |
| PostCSS | `postcss^8.5.14` | Xu ly CSS |
| Autoprefixer | `autoprefixer^10.5.0` | Them vendor prefix CSS |
| ESLint | `eslint^9.13.0` | Kiem tra style va loi code |

Script frontend:

```bash
cd frontend_react
npm install
npm run dev
npm run build
npm run lint
```

Mot so module frontend chinh:

| Duong dan | Vai tro |
|---|---|
| `frontend_react/src/App.tsx` | Khai bao route/layout chinh |
| `frontend_react/src/services/api.ts` | Wrapper goi API backend |
| `frontend_react/src/domains/chat/` | Trang chat, input, message, state |
| `frontend_react/src/domains/auth/` | Login, token, auth store |
| `frontend_react/src/domains/payment/` | Modal thanh toan va lich su giao dich |
| `frontend_react/src/domains/admin/` | Giao dien admin |
| `frontend_react/src/pages/` | Cac trang public: home, about, info, pricing |

## 8. Trien khai

Backend co the chay truc tiep bang Python hoac Docker.

### Chay local

Backend:

```bash
python chatbot/services/server.py
```

Frontend:

```bash
cd frontend_react
npm run dev
```

### Docker

| File | Vai tro |
|---|---|
| `Dockerfile` | Build image backend tu `python:3.10-slim` |
| `docker-compose.yml` | Chay service `chatbot` tren `127.0.0.1:8001` |
| `.env` | Bien moi truong va secret runtime |

Lenh chay:

```bash
docker compose up -d --build
```

Volume quan trong trong Docker Compose:

| Volume | Muc dich |
|---|---|
| `./chroma_economy_db:/app/chroma_economy_db` | Persist vector database |
| `./chatbot/data:/app/chatbot/data` | Persist SQLite app database |

Production deploy theo `DEPLOY.md`:

- Backend chay o `127.0.0.1:8001`.
- Nginx serve frontend build va proxy `/api` ve FastAPI backend.
- HTTPS co the cau hinh bang Certbot.

## 9. File va thu muc quan trong

| Duong dan | Y nghia |
|---|---|
| `requirements.txt` | Dependency Python backend/RAG/scoring |
| `frontend_react/package.json` | Dependency va script frontend |
| `chatbot/services/server.py` | FastAPI server chinh |
| `chatbot/main.py` | Runner chinh cua chatbot RAG |
| `chatbot/services/files_rag_chat_agent.py` | LangGraph workflow RAG |
| `chatbot/utils/llm.py` | Khoi tao LLM theo provider |
| `ingestion/model_embedding.py` | Khoi tao embedding model |
| `ingestion/single_vector_retriever.py` | GT1 Single-Vector ERC retriever |
| `ingestion/vector_data_builder.py` | Build ChromaDB tu dataset |
| `chatbot/utils/base_db.py` | SQLite database cho auth/user/payment/chat/settings |
| `scoring/` | Sinh ket qua va tinh metric danh gia |
| `Dockerfile` | Build backend container |
| `docker-compose.yml` | Chay backend container va volume |
| `DEPLOY.md` | Huong dan deploy production |

## 10. Du lieu runtime va secret

Khong nen commit cac file/thu muc sau:

```text
.env
chatbot/data/login_sessions.db
chroma_economy_db/
```

Cac bien cau hinh/secret quan trong:

| Bien | Muc dich |
|---|---|
| `JWT_SECRET_KEY` | Secret ky JWT |
| `DEFAULT_LLM` | Provider LLM mac dinh |
| `KEY_API_OPENAI` | API key OpenAI |
| `OPENAI_LLM_MODEL_NAME` | Ten model OpenAI |
| `GOOGLE_API_KEY` | API key Gemini |
| `GOOGLE_LLM_MODEL_NAME` | Ten model Gemini |
| `GROQ_API_KEY` | API key Groq |
| `GROQ_LLM_MODEL_NAME` | Ten model Groq |
| `GOOGLE_CLIENT_ID` | OAuth Google client id |
| `GOOGLE_CLIENT_SECRET` | OAuth Google secret |
| `OAUTH_REDIRECT_URI` | Callback OAuth |
| `SEPAY_API_KEY` | API key SePay |
| `SEPAY_ACCOUNT_NUMBER` | So tai khoan nhan tien |
| `BANK_CODE` | Ma ngan hang VietQR |
| `BANK_NAME` | Ten ngan hang hien thi |
| `BANK_ACCOUNT_NAME` | Ten chu tai khoan |

## 11. Ghi chu van hanh

- Neu chua co `chroma_economy_db/`, backend se bao loi `VECTOR_STORE_NOT_FOUND`.
- Embedding model duoc lazy-load khi pipeline can dung, giup server khoi dong nhanh hon.
- Neu `EMBEDDING_DEVICE=auto`, he thong tu chon `cuda` khi co GPU, nguoc lai dung `cpu`.
- Cac cau chao doc lap co the duoc tra loi truc tiep o backend, khong chay RAG va khong tru token.
- Khi deploy production, can backup `chatbot/data/login_sessions.db` va `chroma_economy_db/`.
