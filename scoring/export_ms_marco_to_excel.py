import json
import pandas as pd
from datasets import load_dataset

def export_ms_marco_simple(output_path="ms_marco_eval.xlsx", sample_size=10):
    print("🚀 Loading MS MARCO...")
    dataset = load_dataset("ms_marco", "v1.1", split=f"validation[:{sample_size}]")

    rows = []

    for sample in dataset:
        query = sample.get("query", "").strip()
        passages = sample["passages"]["passage_text"]
        labels = sample["passages"]["is_selected"]

        # 1. Lấy passages đúng (Context)
        gt_passages = [
            p.strip() for p, l in zip(passages, labels)
            if l == 1 and p and p.strip()
        ]

        if not gt_passages:
            continue

        # 2. Lấy ĐÁP ÁN CHUẨN (Ground Truth) do con người viết
        # MS MARCO lưu đáp án trong mảng 'answers'.
        answers = sample.get("answers", [])
        if not answers or not answers[0].strip():
            continue # Bỏ qua nếu câu hỏi này không có đáp án chuẩn
            
        ground_truth = answers[0].strip()

        rows.append({
            "question": query,
            "ground_truth": ground_truth, # Lúc này đáp án rất ngắn gọn và chuẩn!
            "contexts_ground_truth": json.dumps(gt_passages, ensure_ascii=False)
        })

    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)

    print(f"✅ Export xong: {output_path}")
    print(f"📊 Số dòng hợp lệ: {len(df)}")
    return output_path

if __name__ == "__main__":
    export_ms_marco_simple(sample_size=10) # Thử để 100 xem lọc ra được bao nhiêu câu nhé