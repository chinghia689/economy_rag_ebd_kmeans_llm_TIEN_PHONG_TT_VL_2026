# GT3 — LLM Fixed-N Split + Multi-Vector ERC

## Thuật toán

```
câu hỏi
  → LLM tách thành ĐÚNG N sub-queries (N do người dùng chọn: 1/2/3/4)
  → [embed(sub_1), ..., embed(sub_N)]  ← phân phối X
  → mỗi sub-query lấy top-40 docs từ ChromaDB, dedup
  → K-Means (k=2..10, chọn k tối ưu theo Silhouette Score)
  → Energy Distance giữa X và từng cluster Y
  → chọn cluster có ED nhỏ nhất
  → DocumentGrader lọc yes/no
  → LLM sinh câu trả lời
```

**Điểm khác biệt so với GT1:** Số sub-queries **cố định** theo `--num-queries` (LLM phải tuân thủ đúng số đó, có padding nếu thiếu). GT1 để LLM tự quyết. GT3 giúp đánh giá xem N cụ thể nào cho kết quả tốt nhất.

---

## Bước 1 — Sinh file kết quả

Chạy từ thư mục gốc (chứa `GT3_Manual_N/` và `Folder_All/`):

```bash
# N=2 (mặc định)
python -m GT3_Manual_N.create_eval --num-queries 2

# N=1 — đánh giá single sub-query (không có câu gốc)
python -m GT3_Manual_N.create_eval --num-queries 1 --max 50

# N=3
python -m GT3_Manual_N.create_eval --num-queries 3

# N=4
python -m GT3_Manual_N.create_eval --num-queries 4

# Tùy chỉnh đầy đủ
python -m GT3_Manual_N.create_eval \
    --num-queries 2 \
    --input  Folder_All/scoring/"file 1000 cau hoi.xlsx" \
    --output GT3_Manual_N/GT3_N2_eval_results.xlsx \
    --llm-provider openai \
    --vector-store Folder_All/chroma_economy_db \
    --save-every 1
```

### Tham số

| Tham số | Mặc định | Mô tả |
|---|---|---|
| `--num-queries` | `2` | Số sub-queries cố định: `1`, `2`, `3`, hoặc `4` |
| `--input` | `Folder_All/scoring/file 1000 cau hoi.xlsx` | File Excel đầu vào (cần cột `question`, `ground_truth`, `contexts_ground_truth`) |
| `--output` | `GT3_N{N}_eval_results.xlsx` | File xuất — tự động đặt tên theo N nếu không chỉ định |
| `--max` | tất cả | Giới hạn số câu hỏi (test nhanh) |
| `--llm-provider` | `openai` | Provider LLM: `openai` / `gemini` / `groq` |
| `--vector-store` | `Folder_All/chroma_economy_db` | Đường dẫn ChromaDB |
| `--save-every` | `1` | Lưu Excel sau mỗi N câu (chống mất dữ liệu) |

**Output:** `GT3_Manual_N/GT3_N{N}_eval_results.xlsx` với các cột:
`question`, `ground_truth`, `contexts_ground_truth`, `answer`, `contexts_answer`, `metadata`, `query_parts`, `algorithm`, `num_queries`

Cột `num_queries` lưu giá trị N — hữu ích khi gộp kết quả nhiều lần chạy vào một file để so sánh.

---

## Bước 2 — Tính điểm

Chạy từ thư mục `Folder_All/`:

```bash
# Chấm điểm từng N riêng
cd Folder_All
python scoring/main.py --file ../GT3_Manual_N/GT3_N1_eval_results.xlsx
python scoring/main.py --file ../GT3_Manual_N/GT3_N2_eval_results.xlsx
python scoring/main.py --file ../GT3_Manual_N/GT3_N3_eval_results.xlsx
python scoring/main.py --file ../GT3_Manual_N/GT3_N4_eval_results.xlsx
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

## Workflow so sánh N=1..4

```bash
# Chạy cả 4 cấu hình
for N in 1 2 3 4; do
    python -m GT3_Manual_N.create_eval --num-queries $N --max 100
done

# Chấm điểm tất cả
cd Folder_All
for N in 1 2 3 4; do
    python scoring/main.py --file ../GT3_Manual_N/GT3_N${N}_eval_results.xlsx
done
```

So sánh MRR và HIT@5 giữa N=1/2/3/4 để tìm giá trị N tối ưu cho dataset.

---

## Yêu cầu môi trường

- File `.env` tại `Folder_All/.env`
- ChromaDB đã được tạo tại `Folder_All/chroma_economy_db`
- Các package: `langchain`, `langchain-chroma`, `scikit-learn`, `scipy`, `pandas`, `openpyxl`
