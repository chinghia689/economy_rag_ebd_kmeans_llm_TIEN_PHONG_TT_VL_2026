# GT1 Single-Vector ERC

`Folder_All` chứa toàn bộ ứng dụng chatbot và pipeline đánh giá GT1.

## Thuật toán

```text
câu hỏi
  -> embed(q), chỉ một query vector
  -> lấy top-40 tài liệu từ ChromaDB
  -> K-Means, thử k=2..10 và chọn theo Silhouette Score
  -> tính Energy Distance từ query vector tới từng cụm tài liệu
  -> chọn cụm có Energy Distance nhỏ nhất
  -> DocumentGrader lọc tài liệu
  -> LLM sinh câu trả lời
```

GT1 không tách câu hỏi bằng LLM. `query_parts` luôn chứa đúng câu hỏi gốc.

## Chào hỏi miễn phí

Các câu chào độc lập như `xin chào`, `hello`, `chào buổi sáng` được trả lời
ngay tại backend, không tải model, không chạy ChromaDB/RAG và không trừ token.
Câu có thêm nội dung thực, ví dụ `xin chào, GDP là gì?`, vẫn đi qua pipeline GT1
và được tính token bình thường.

## Chạy chatbot

Từ thư mục `Folder_All`:

```bash
python -m chatbot.main --llm openai
```

Hoặc chạy API - Frontend-Backend:

Chạy backend server
```bash
python chatbot/services/server.py 
```
Chạy frontend
```bash
cd DEMO_ERC/Folder_ALL/frontend_react -> npm run dev
```
## Sinh kết quả đánh giá

```bash
# Toàn bộ tập câu hỏi
python -m scoring.create_eval

# Chạy thử 50 câu
python -m scoring.create_eval --max 50

# Tùy chỉnh
python -m scoring.create_eval \
    --input "scoring/file 1000 cau hoi.xlsx" \
    --output scoring/GT1_eval_results.xlsx \
    --llm-provider openai \
    --vector-store chroma_economy_db \
    --save-every 1
```

Các tham số chính:

| Tham số | Mặc định |
|---|---|
| `--input` | `scoring/file 1000 cau hoi.xlsx` |
| `--output` | `scoring/GT1_eval_results.xlsx` |
| `--max` | Toàn bộ câu hỏi |
| `--start` | `0` |
| `--llm-provider` | `openai` |
| `--vector-store` | `chroma_economy_db` |
| `--save-every` | `1` |

## Tính điểm

```bash
python scoring/main.py --file scoring/GT1_eval_results.xlsx
```

Các metric gồm ROUGE-2, BLEU-2, Cosine Similarity, MRR, Hit@5 và NDCG@5.

## Yêu cầu

- `.env` nằm trong `Folder_All`.
- ChromaDB nằm tại `Folder_All/chroma_economy_db`.
- Cài dependency bằng `pip install -r requirements.txt`.
