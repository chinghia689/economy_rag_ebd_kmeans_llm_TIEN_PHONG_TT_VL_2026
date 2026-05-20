import os
import re
import pandas as pd


# === HÀM TẠO N-GRAM ===
def generate_ngrams(text, n):
    """
    Sinh danh sách n-grams từ một đoạn văn bản.

    Args:
        text (str): Văn bản đầu vào.
        n (int): Kích thước n-gram (ví dụ n=2 → bigram).

    Returns:
        list[tuple[str]]: Danh sách n-gram dạng tuple.
                          Ví dụ: "xin chào bạn" với n=2 → [("xin","chào"), ("chào","bạn")]
    """
    # Chuẩn hoá: bỏ dấu câu, lowercase
    text = re.sub(r"[^\w\s]", "", str(text).lower())
    words = text.split()

    # Sinh n-grams liên tiếp
    return [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]


# === HÀM TÍNH ROUGE-N (Recall, Precision, F1) ===
def calculate_ROUGE(generated_summary, reference_summary, n=2):
    """
    Tính ROUGE-N (Recall, Precision, F1) giữa văn bản sinh ra và văn bản tham chiếu.

    Args:
        generated_summary (str): Văn bản sinh ra (mô hình).
        reference_summary (str): Văn bản tham chiếu (ground truth).
        n (int): Kích thước n-gram (1 → unigram, 2 → bigram, ...).

    Returns:
        tuple(float, float, float): (Recall, Precision, F1)
    """
    # Tạo n-grams
    generated_ngrams = generate_ngrams(generated_summary, n)
    reference_ngrams = generate_ngrams(reference_summary, n)

    # Tập hợp n-grams
    set_gen = set(generated_ngrams)
    set_ref = set(reference_ngrams)

    # Đếm số n-grams trùng khớp
    matching = len(set_gen & set_ref)

    # Tính Recall, Precision, F1
    recall = matching / len(set_ref) if len(set_ref) > 0 else 0
    precision = matching / len(set_gen) if len(set_gen) > 0 else 0
    f1 = (
        (2 * precision * recall / (precision + recall))
        if (precision + recall) > 0
        else 0
    )

    return recall, precision, f1


# === HÀM CHÍNH: ĐỌC FILE, TÍNH ROUGE-N, XUẤT FILE EXCEL ===
def rouge_excel(file_path, n=2, out: str = None):
    """
    Đọc file Excel, tính ROUGE-N cho từng cặp reference–generated,
    rồi lưu ra file Excel mới (có thêm 3 cột Recall, Precision, F1).

    Args:
        file_path (str): Đường dẫn file Excel input.
                         Giả định:
                           - Cột thứ 2 (index=1) chứa Reference (ground truth).
                           - Cột thứ 4 (index=3) chứa Generated (mô hình sinh).
        n (int): Kích thước n-gram (ví dụ n=2 → ROUGE-2).
        out (str, optional): Đường dẫn file Excel output.
                             Nếu không truyền → thêm prefix "rouge{n}_" vào tên gốc.

    Returns:
        str: Đường dẫn file Excel đã tạo.
    """
    # Đọc file input
    df = pd.read_excel(file_path)

    # Thêm 3 cột ROUGE-n (Recall, Precision, F1)
    df[[f"ROUGE-{n} Recall", f"ROUGE-{n} Precision", f"ROUGE-{n} F1"]] = df.apply(
        lambda row: pd.Series(calculate_ROUGE(row[3], row[1], n)), axis=1
    )

    # Xác định đường dẫn output
    if out:
        out_path = out
    else:
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        out_path = os.path.join(dir_name, f"rouge{n}_" + base_name)

    # Xuất file Excel
    df.to_excel(out_path, index=False)

    # Hiển thị toàn bộ bảng (debug/kiểm tra nhanh)
    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print(df)

    print(f"✅ Đã tạo file: {out_path}")
    return out_path
