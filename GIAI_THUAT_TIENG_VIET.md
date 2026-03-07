# GIẢI THUẬT HỆ THỐNG CHATBOT KINH TẾ VIỆT NAM

## 1. Tổng quan hệ thống

Hệ thống là một **Chatbot RAG (Retrieval-Augmented Generation)** xây dựng trên tập dữ liệu văn bản kinh tế Việt Nam (`Dataset_economy/`), bao gồm 9 danh mục: Bất động sản, Dân sinh, Đầu tư, Doanh nghiệp, Kinh tế số, Tài chính, Thế giới, Thị trường, Tiêu điểm.

Mục tiêu: Cải thiện chất lượng truy hồi trong mô hình RAG thông qua cơ chế **lọc đa tầng**:
1. Truy hồi diện rộng bằng Cosine Similarity
2. Lọc ngưỡng tương đồng
3. Phân cụm tối ưu bằng K-Means + Silhouette Score
4. Chọn cụm tốt nhất bằng Energy Distance
5. Chấm điểm tài liệu bằng LLM (Document Grading)
6. Sinh câu trả lời

### Kiến trúc tổng thể

```
Workflow (LangGraph StateGraph):
  START → retrieve → grade_documents → decide_to_generate
    → generate → END
    → no_document (handle_no_answer) → END
```

---

## 2. Tiền xử lý dữ liệu (Ingestion Pipeline)

### 2.1. Đọc dữ liệu (`load_document.py`)
- Duyệt đệ quy toàn bộ thư mục `Dataset_economy/`, đọc tất cả file `*.txt`
- Mỗi file → 1 `Document` object với metadata: `source`, `category` (tên thư mục cha), `filename`

### 2.2. Phân đoạn văn bản (`chunks_document.py`)
Toàn bộ tập dữ liệu được chia nhỏ bằng:
* **RecursiveCharacterTextSplitter**
  * `chunk_size = 600`
  * `chunk_overlap = 80`
  * `separators = ['\n\n', '\n']`
* **Deduplication**: Loại bỏ chunks trùng nội dung bằng MD5 hash trước khi lưu

### 2.3. Biểu diễn vector (`model_embedding.py`)
Mỗi đoạn văn được ánh xạ sang không gian vector **768 chiều** bằng mô hình:
> `intfloat/multilingual-e5-base` (chạy trên **CUDA**)

Sử dụng **E5EmbeddingsWrapper** tự động thêm prefix bắt buộc:
* Query: thêm prefix `"query: "` trước khi embed
* Document/Passage: thêm prefix `"passage: "` trước khi embed
* Cấu hình: `normalize_embeddings = True`

Do đó:
* Mỗi document chunk → vector **(1 × 768)**
* Query → vector **(1 × 768)**

### 2.4. Lưu trữ vector (`chunks_document.py`)
Các embedding được lưu trong:
* **ChromaDB** (persist directory: `./chroma_economy_db`)
* Thước đo tương đồng: **Cosine Similarity**
* Hỗ trợ `force_rebuild` để xóa DB cũ và tạo lại hoàn toàn

### 2.5. Xây dựng Database (`vector_data_builder.py`)
Pipeline xây dựng:
1. Load documents từ `./Dataset_economy`
2. Lấy embedding model (multilingual-e5-base)
3. Chunking + Dedup + Lưu vào ChromaDB

---

## 3. Truy hồi nâng cao — Energy Retriever (`energy_kmeans.py`)

### 3.1. Truy hồi diện rộng (Initial Retrieval)
Khi nhận truy vấn từ người dùng, hệ thống thực hiện:
1. Embed truy vấn → vector (1 × 768)
2. Truy hồi **top-40 documents** có cosine similarity cao nhất từ ChromaDB

### 3.2. Kiểm tra ngưỡng chất lượng
Sau khi lấy top-40 tài liệu, hệ thống:
1. Embed lại query và toàn bộ 40 documents
2. Tính cosine similarity giữa query vector và từng document vector
3. Kiểm tra `max(cosine similarity)`:
   * Nếu `max similarity ≥ 0.50` → tiếp tục pipeline
   * Nếu `max similarity < 0.50` → **dừng hẳn**, trả về danh sách rỗng (dữ liệu nhiễu)

### 3.3. Lọc theo ngưỡng Cosine Similarity
* Chỉ giữ lại các documents có `cosine similarity ≥ 0.50`
* Nếu sau lọc còn **≤ 3 documents** → trả trực tiếp (sắp xếp theo cosine giảm dần, không cần clustering)

### 3.4. Phân cụm K-Means tự động chọn K tối ưu
Tập documents đã lọc được phân cụm bằng K-Means:
* **K được tự động chọn** bằng **Silhouette Score**:
  * Duyệt K từ 2 đến `min(10, n_samples - 1)`
  * Chọn K có Silhouette Score cao nhất
* Nếu chỉ có 2 docs → gom thành 1 cụm duy nhất

### 3.5. Tính Energy Distance (`energy_base_distance.py`)
Đối với từng cụm, hệ thống tính **Energy Distance** giữa:
* Vector truy vấn X (1 × 768)
* Tập vector trong cụm Y (n × 768)

Công thức:
$$ED(X, Y) = 2 \cdot E[\|X - Y\|] - E[\|X - X'\|] - E[\|Y - Y'\|]$$

Trong đó:
* $E[\|X - Y\|]$ = trung bình khoảng cách Euclidean chéo giữa X và Y
* $E[\|X - X'\|]$ = trung bình khoảng cách nội bộ tập X
* $E[\|Y - Y'\|]$ = trung bình khoảng cách nội bộ tập Y
* Kết quả được clamp về `max(0, ED)` để tránh giá trị âm

### 3.6. Chọn cụm tối ưu & Re-ranking
1. Sắp xếp các cụm theo Energy Distance **tăng dần** (thấp = gần query nhất = tốt nhất)
2. Chọn **top-1 cụm** có Energy Distance nhỏ nhất (`n_top_clusters = 1`)
3. Gom toàn bộ documents từ cụm được chọn
4. **Re-rank** theo cosine similarity (cao → thấp)
5. Loại bỏ trùng lặp, giới hạn tối đa **15 documents** (`max_final_docs = 15`)

---

## 4. Chấm điểm tài liệu — Document Grading (`document_grader.py`)

Sau khi Energy Retriever trả về documents, hệ thống sử dụng **LLM để chấm điểm hàng loạt (Batching)**:

### Quy trình:
1. Gom tất cả documents thành 1 chuỗi duy nhất, đánh số thứ tự `[Tài liệu 1], [Tài liệu 2], ...`
2. Gọi LLM **đúng 1 lần** với prompt yêu cầu trả về mảng JSON chứa số thứ tự các tài liệu liên quan
3. Parse kết quả JSON bằng regex → lọc ra danh sách tài liệu hữu ích

### Prompt chấm điểm:
> *"Bạn là giám khảo chấm điểm mức độ liên quan của tài liệu. Chỉ trả về một mảng JSON chứa SỐ THỨ TỰ của các tài liệu hữu ích."*

### Quyết định tiếp theo (`decide_to_generate`):
* Nếu **có** tài liệu liên quan → chuyển sang bước sinh câu trả lời
* Nếu **không** có tài liệu nào → trả về thông báo "không tìm thấy thông tin"

---

## 5. Sinh câu trả lời (`answer_generator.py`)

### 5.1. Xây dựng context
Ghép nội dung tất cả tài liệu đã lọc thành một chuỗi context duy nhất (nối bằng `\n\n`)

### 5.2. Prompt sinh câu trả lời
Hệ thống sử dụng prompt **trích xuất văn bản tự động** với 3 quy tắc:
1. **COPY TRỌN VẸN** một câu văn từ ngữ cảnh — không tóm tắt
2. **CẤM TỪ ĐỆM** — không thêm "Theo thông tin...", "Ngữ cảnh cho thấy..."
3. **TRÍCH XUẤT LINH HOẠT** — trả về câu có chứa nhiều từ khóa nhất, chỉ trả về "None" khi ngữ cảnh hoàn toàn lạc đề

### 5.3. Xử lý hậu kỳ
Loại bỏ tag `<think>...</think>` (nếu có) khỏi output bằng regex

---

## 6. Mô hình ngôn ngữ — LLM (`llm.py`)

Hỗ trợ nhiều LLM provider (hiện tại active: **OpenAI**):
* `temperature = 0.01` (gần như deterministic)
* `max_tokens = 4096`
* Các provider khả dụng: OpenAI, Gemini, Groq, Grok, Local Ollama (đã comment)

---

## 7. Workflow tổng thể (`files_rag_chat_agent.py`)

Sử dụng **LangGraph StateGraph** với các node:

| Node | Chức năng |
|------|-----------|
| `retrieve` | Truy xuất documents bằng Energy Retriever |
| `grade_documents` | Chấm điểm tài liệu bằng LLM (batch) |
| `generate` | Sinh câu trả lời từ question + context |
| `no_document` | Xử lý khi không có tài liệu liên quan |

### GraphState:
```python
class GraphState(TypedDict):
    question: str       # Câu hỏi người dùng
    generation: str     # Câu trả lời sinh ra
    documents: List     # Danh sách tài liệu
    prompt: str         # Custom system prompt
```

### Luồng:
```
START → retrieve → grade_documents
  ├─ (có docs) → generate → END
  └─ (không docs) → no_document → END
```

---

## 8. Đánh giá hệ thống (Scoring Pipeline)

### 8.1. Tạo dữ liệu đánh giá (`create_eval_data.py`)
* Load câu hỏi từ file Excel (1000 câu hỏi)
* Resolve `contexts_ground_truth` từ tên file .txt → nội dung text đầy đủ
* Chạy chatbot trả lời từng câu → lưu kết quả ra Excel

### 8.2. Các metric đánh giá (`scoring/evaluation_metric/`)

| Metric | Mô tả | File |
|--------|--------|------|
| **ROUGE-N** | Đo n-gram overlap (Recall, Precision, F1) giữa answer và ground_truth | `rouge_n.py` |
| **BLEU-N** | Đo chất lượng dịch máy (n-gram precision) | `bleu.py` |
| **Cosine Similarity** | Đo tương đồng vector embedding giữa answer và ground_truth | `cosine_similarity.py` |
| **MRR** | Mean Reciprocal Rank — vị trí đầu tiên tìm thấy ground_truth trong contexts | `mrr.py` |
| **Hit Rate@k** | Ground truth có xuất hiện trong top-k contexts không | `hit_rate.py` |
| **NDCG@k** | Normalized Discounted Cumulative Gain — context đúng có được xếp lên trên không | `ndcg.py` |

### NDCG Relevance Grading:
* overlap ≥ 60% → relevance = 3
* overlap ≥ 30% → relevance = 2
* overlap ≥ 10% → relevance = 1
* overlap < 10% → relevance = 0

---

## 9. Tóm tắt tham số hệ thống

| Tham số | Giá trị | File |
|---------|---------|------|
| Embedding model | `intfloat/multilingual-e5-base` | `model_embedding.py` |
| Embedding dimension | 768 | — |
| Embedding device | CUDA | `model_embedding.py` |
| Chunk size | 600 | `chunks_document.py` |
| Chunk overlap | 80 | `chunks_document.py` |
| Vector store | ChromaDB (`./chroma_economy_db`) | `chunks_document.py` |
| Top-K retrieval | 40 | `energy_kmeans.py` |
| Filter | Không lọc — toàn bộ 40 docs vào K-Means trực tiếp | `energy_kmeans.py` |
| K-Means range | 2 → min(10, n-1), chọn theo Silhouette | `energy_kmeans.py` |
| Top clusters | 1 | `energy_kmeans.py` |
| Max final docs | Toàn bộ docs trong cluster winner (không giới hạn) | `energy_kmeans.py` |
| LLM provider | OpenAI | `llm.py` |
| Temperature | 0.01 | `llm.py` |
| Evaluation metrics | ROUGE-2, BLEU-2, Cosine, MRR, Hit@5, NDCG@5 | `scoring/` |

---

## 10. Đặc điểm phương pháp

Phương pháp này:
* **Lọc đa tầng**: Top-40 cosine → K-Means + Silhouette → Energy Distance → LLM Grading
* **Tự động chọn K tối ưu** thay vì hardcode số cụm
* **So sánh ở mức phân phối** (Energy Distance) thay vì chỉ so với centroid
* **Batch grading** bằng LLM: giảm từ N lần gọi API xuống còn 1 lần duy nhất
* **Re-ranking** documents theo cosine similarity sau khi chọn cụm
* **Trích xuất nguyên văn** thay vì tóm tắt, đảm bảo trung thực với nguồn


