# GT3 — LLM Auto Split + Multi-Vector ERC

## Thuật toán

```
câu hỏi
  → LLM tự quyết 1–4 sub-queries (best-effort, không cố định)
  → [embed(q_gốc), embed(sub_1), ..., embed(sub_N)]  ← phân phối X
  → mỗi query part lấy top-40 docs từ ChromaDB, dedup
  → K-Means (k=2..10, chọn k tối ưu theo Silhouette Score)
  → Energy Distance giữa X và từng cluster Y
  → chọn cluster có ED nhỏ nhất
  → DocumentGrader lọc yes/no
  → LLM sinh câu trả lời
```

**Điểm khác biệt so với GT1_1Vector/GT2_Manual_N:** LLM tự quyết số lượng sub-queries (không cố định), tối đa `--max-parts`. Phân phối X có kích thước thay đổi theo từng câu hỏi.

---

## Bước 1 — Sinh file kết quả

Chạy từ thư mục gốc (chứa `GT3_Auto/` và `Folder_All/`):

```bash
# Cơ bản — chạy toàn bộ 1000 câu hỏi
python -m GT3_Auto.create_eval

# Chạy thử 50 câu
python -m GT3_Auto.create_eval --max 50

# Tùy chỉnh đầy đủ
python -m GT3_Auto.create_eval \
    --input  Folder_All/scoring/"file 1000 cau hoi.xlsx" \
    --output GT3_Auto/GT3_eval_results.xlsx \
    --max-parts 4 \
    --llm-provider openai \
    --vector-store Folder_All/chroma_economy_db \
    --save-every 1
```

### Tham số

| Tham số | Mặc định | Mô tả |
|---|---|---|
| `--input` | `Folder_All/scoring/file 1000 cau hoi.xlsx` | File Excel đầu vào (cần cột `question`, `ground_truth`, `contexts_ground_truth`) |
| `--output` | `GT3_Auto/GT3_eval_results.xlsx` | File Excel kết quả |
| `--max` | tất cả | Giới hạn số câu hỏi (test nhanh) |
| `--start` | `0` | Tiếp tục từ câu N (1-indexed) sau khi bị ngắt |
| `--max-parts` | `4` | Số sub-queries tối đa LLM được phép tạo |
| `--llm-provider` | `openai` | Provider LLM: `openai` / `gemini` / `groq` |
| `--vector-store` | `Folder_All/chroma_economy_db` | Đường dẫn ChromaDB |
| `--save-every` | `1` | Lưu Excel sau mỗi N câu (chống mất dữ liệu) |

**Output:** `GT3_Auto/GT3_eval_results.xlsx` với các cột:
`question`, `ground_truth`, `contexts_ground_truth`, `answer`, `contexts_answer`, `metadata`, `query_parts`, `algorithm`

---

## Bước 2 — Tính điểm

Chạy từ thư mục `Folder_All/`:

```bash
cd Folder_All
python scoring/main.py --file ../GT3_Auto/GT3_eval_results.xlsx
```

### Metrics được tính

| Metric | Mô tả |
|---|---|
| ROUGE-2 | N-gram overlap giữa `answer` và `ground_truth` |
| BLEU-2 | Precision n-gram |
| Cosine Similarity | Độ tương đồng embedding giữa `answer` và `ground_truth` |
| MRR | Mean Reciprocal Rank — dùng `contexts_answer` vs `contexts_ground_truth` |
| Hit@5 | Tỷ lệ câu hỏi có ít nhất 1 context đúng trong top-5 |
| NDCG@5 | Normalized Discounted Cumulative Gain |

**Output:** File Excel gốc được cập nhật thêm cột điểm, in tóm tắt `MRR` và `HIT@5` ra console.

---

## Lưu ý

GT3_Auto **không phải** thuật toán nghiên cứu chính của luận văn — đây là module demo dùng cho frontend production (`Folder_All/chatbot/`). Hai thuật toán nghiên cứu chính là **GT1_1Vector** (phân phối suy biến) và **GT2_Manual_N** (phân phối thực với N cố định).

---

## Yêu cầu môi trường

- File `.env` tại `Folder_All/.env` (xem `Folder_All/app/config.py` để biết các biến cần thiết)
- ChromaDB đã được tạo tại `Folder_All/chroma_economy_db`
- Các package: `langchain`, `langchain-chroma`, `scikit-learn`, `scipy`, `pandas`, `openpyxl`
