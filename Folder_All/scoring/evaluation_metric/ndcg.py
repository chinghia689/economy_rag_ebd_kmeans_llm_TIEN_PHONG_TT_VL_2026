"""
Vai trò trong NDCG

Dùng để xác định context nào là liên quan

So với contexts_answer để gán relevance

2. contexts_answer là gì?
Định nghĩa đúng

contexts_answer = danh sách top-k đoạn văn (chunks) được retrieve

Output của retriever (BM25 / FAISS / vector DB)

Đã được xếp hạng

Thứ tự rất quan trọng

Ví dụ:

contexts_answer = [
   chunk_1,  # rank 1
   chunk_2,  # rank 2
   chunk_3,  # rank 3
]

3. Mối quan hệ giữa hai cột (cốt lõi NDCG)
Thành phần	Vai trò
ground_truth	“Câu trả lời đúng là gì?”
contexts_answer[i]	“Đoạn này có giúp trả lời không?”
relevance	mức độ giúp trả lời
NDCG	context đúng có nằm trên cao không
4. Minh họa trực quan
Ví dụ
ground_truth:
"73,75 triệu đồng/lượng (mua vào)"

contexts_answer:
1. "79,5 triệu đồng/lượng (mua vào)" ❌
2. "73,75 triệu đồng/lượng (mua vào)" ✅
3. "Giá vàng thế giới tăng..." ❌

relevance (graded)
[0, 3, 0]

NDCG@3

Context đúng nằm ở vị trí 2

NDCG < 1 (bị phạt vì không đứng top-1)

👉 Đúng ý nghĩa NDCG

5. Những hiểu nhầm hay gặp (nên tránh)
❌ Dùng contexts_ground_truth để tính NDCG

→ sai, đó chỉ là nguồn file

❌ So answer với context

→ đó là QA accuracy, không phải retrieval

❌ So context chứa toàn bộ bài báo

→ không thực tế với chunking

6. Rule vàng (nhớ kỹ)

ground_truth = đáp án
contexts_answer = tài liệu để tìm đáp án
NDCG = tài liệu đúng có được xếp lên trên không

7. Tóm tắt 1 dòng

NDCG trả lời câu hỏi: “Retriever có đưa tài liệu đúng lên đầu danh sách không?”
"""

import math
import ast
import pandas as pd
import re
import os


# =====================
# TOKENIZE ĐƠN GIẢN
# =====================
def tokenize(text: str):
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return set(text.split())


# =====================
# RELEVANCE (GRADED)
# =====================
def relevance_graded(ground_truth: str, context: str) -> int:
    gt_tokens = tokenize(ground_truth)
    ctx_tokens = tokenize(context)

    if not gt_tokens:
        return 0

    overlap = len(gt_tokens & ctx_tokens) / len(gt_tokens)

    if overlap >= 0.6:
        return 3
    elif overlap >= 0.3:
        return 2
    elif overlap >= 0.1:
        return 1
    return 0


# =====================
# DCG / NDCG
# =====================
def dcg_at_k(rels, k):
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(rels[:k]))


def ndcg_at_k(rels, k):
    dcg = dcg_at_k(rels, k)
    ideal = sorted(rels, reverse=True)
    idcg = dcg_at_k(ideal, k)
    return dcg / idcg if idcg > 0 else 0.0


# =====================
# TÍNH NDCG CHO 1 DÒNG
# =====================
def calc_ndcg_row(row, k=5):
    ground_truth = str(row["ground_truth"]).strip()

    try:
        contexts = ast.literal_eval(row["contexts_answer"])
        if not isinstance(contexts, list):
            return 0.0
    except Exception:
        return 0.0

    relevances = [relevance_graded(ground_truth, ctx) for ctx in contexts]

    if sum(relevances) == 0:
        return 0.0

    return ndcg_at_k(relevances, k)


# =====================
# CHẠY TRÊN EXCEL
# =====================
def ndcg_excel(path, k=5, out=None):
    df = pd.read_excel(path)

    df[f"NDCG@{k}"] = df.apply(lambda r: calc_ndcg_row(r, k), axis=1)

    if not out:
        dir_name = os.path.dirname(path)
        base_name = os.path.basename(path)
        out = os.path.join(
            dir_name, f"END_{base_name.replace('.xlsx', f'_ndcg{k}.xlsx')}"
        )

    df.to_excel(out, index=False)

    print("✅ Done:", out)
    print("📊 Mean NDCG:", df[f"NDCG@{k}"].mean())

    return out
