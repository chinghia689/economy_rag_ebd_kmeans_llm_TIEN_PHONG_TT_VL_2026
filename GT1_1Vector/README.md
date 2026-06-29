# GT1 — Single Vector ERC

## Thuật toán

```
câu hỏi
  → embed(q)  ← phân phối X gồm đúng 1 vector
  → lấy top-40 docs từ ChromaDB
  → K-Means (k=2..10, chọn k tối ưu theo Silhouette Score)
  → Energy Distance giữa X (1 điểm) và từng cluster Y
  → chọn cluster có ED nhỏ nhất
  → DocumentGrader lọc yes/no
  → LLM sinh câu trả lời
```

**Điểm khác biệt so với GT2/Gt2_mutiquery:** Không dùng LLM tách câu hỏi. Phân phối query X là 1 vector duy nhất (phân phối suy biến, E_XX=0). Dùng để đánh giá baseline — xem multi-vector có thực sự tốt hơn không.

---

## Bước 1 — Sinh file kết quả

Chạy từ thư mục gốc (chứa `GT1_1Vector/` và `Folder_All/`):

```bash
# Cơ bản — chạy toàn bộ 1000 câu hỏi
python -m GT1_1Vector.create_eval

# Chạy thử 50 câu
python -m GT1_1Vector.create_eval --max 50

# Tùy chỉnh đầy đủ
python -m GT1_1Vector.create_eval \
    --input  Folder_All/scoring/"file 1000 cau hoi.xlsx" \
    --output GT1_1Vector/GT1_eval_results.xlsx \
    --llm-provider openai \
    --vector-store Folder_All/chroma_economy_db \
    --save-every 1
```

### Tham số

| Tham số | Mặc định | Mô tả |
|---|---|---|
| `--input` | `Folder_All/scoring/file 1000 cau hoi.xlsx` | File Excel đầu vào (cần cột `question`, `ground_truth`, `contexts_ground_truth`) |
| `--output` | `GT1_1Vector/GT1_eval_results.xlsx` | File Excel kết quả |
| `--max` | tất cả | Giới hạn số câu hỏi (test nhanh) |
| `--start` | `0` | Tiếp tục từ câu N (1-indexed) sau khi bị ngắt |
| `--llm-provider` | `openai` | Provider LLM: `openai` / `gemini` / `groq` |
| `--vector-store` | `Folder_All/chroma_economy_db` | Đường dẫn ChromaDB |
| `--save-every` | `1` | Lưu Excel sau mỗi N câu (chống mất dữ liệu) |

**Output:** `GT1_1Vector/GT1_eval_results.xlsx` với các cột:
`question`, `ground_truth`, `contexts_ground_truth`, `answer`, `contexts_answer`, `metadata`, `query_parts`, `algorithm`

`query_parts` luôn là `[question]` (1 phần tử duy nhất).

---

## Bước 2 — Tính điểm

Chạy từ thư mục `Folder_All/`:

```bash
cd Folder_All
python scoring/main.py --file ../GT1_1Vector/GT1_eval_results.xlsx
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

## So sánh với GT2/Gt2_mutiquery

GT1 là baseline cho GT2 (auto-split với giới hạn người dùng chọn) và Gt2_mutiquery (auto-split tối đa 5 vector). Nếu GT2/Gt2_mutiquery không vượt GT1, cần xem lại chất lượng LLM splitting hoặc energy distance implementation.

---

## Yêu cầu môi trường

- File `.env` tại `Folder_All/.env`
- ChromaDB đã được tạo tại `Folder_All/chroma_economy_db`
- Các package: `langchain`, `langchain-chroma`, `scikit-learn`, `scipy`, `pandas`, `openpyxl`
