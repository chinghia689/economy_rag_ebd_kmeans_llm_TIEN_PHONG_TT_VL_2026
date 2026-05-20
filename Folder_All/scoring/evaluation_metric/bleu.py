import os
import pandas as pd
import nltk.translate.bleu_score as bleu


# === HÀM TÍNH BLEU-N ===
def calculate_BLEU(generated_summary, reference_summary, n=2):
    """
    Tính điểm BLEU-n giữa văn bản sinh ra (generated) và văn bản tham chiếu (reference).

    Args:
        generated_summary (str): Văn bản do mô hình sinh ra.
        reference_summary (str): Văn bản tham chiếu (ground truth).
        n (int): Cấp độ n-gram để tính BLEU.
                 - n=1 → BLEU-1 (unigram)
                 - n=2 → BLEU-2 (bigram)
                 - n=3 → BLEU-3 (trigram)
                 - n=4 → BLEU-4 (4-gram)

    Returns:
        float: Điểm BLEU-n (giá trị từ 0.0 → 1.0).
               - Gần 1.0 → văn bản generated rất giống reference.
               - Gần 0.0 → văn bản generated khác nhiều so với reference.
    """
    # Chia văn bản thành tokens (theo khoảng trắng)
    generated_tokens = str(generated_summary).split()
    reference_tokens = str(reference_summary).split()

    # Trọng số cho n-gram (ví dụ n=2 → (0.5, 0.5))
    weights = tuple([1.0 / n] * n)

    # Tính điểm BLEU
    bleu_score = bleu.sentence_bleu(
        [reference_tokens],  # danh sách reference (BLEU hỗ trợ multi-reference)
        generated_tokens,  # câu generated
        weights=weights,  # trọng số cho n-gram
    )

    return bleu_score


# === HÀM CHÍNH: ĐỌC FILE, TÍNH BLEU-N, LƯU EXCEL ===
def bleu_excel(file_path, n=2, out: str = None):
    """
    Đọc file Excel, tính BLEU-n cho từng cặp câu (reference vs generated),
    sau đó ghi kết quả ra file Excel mới.

    Args:
        file_path (str): Đường dẫn file Excel gốc.
                         Giả định:
                           - Cột thứ 2 (index=1) chứa Reference (ground truth).
                           - Cột thứ 4 (index=3) chứa Generated (mô hình sinh).
        n (int): Cấp độ n-gram để tính BLEU (1 → 4).
        out (str, optional): Đường dẫn file Excel output.
                             Nếu không truyền, sẽ tạo file mới cùng thư mục,
                             thêm tiền tố "bleu{n}_" trước tên file gốc.

    Returns:
        str: Đường dẫn file Excel đã tạo (có thêm cột BLEU-n).
    """
    # Đọc dữ liệu từ file Excel gốc
    df = pd.read_excel(file_path)

    # Thêm cột BLEU-n vào DataFrame
    df[f"BLEU-{n}"] = df.apply(lambda row: calculate_BLEU(row[3], row[1], n), axis=1)

    # Xác định đường dẫn file output
    if out:
        out_path = out
    else:
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        out_path = os.path.join(dir_name, f"bleu{n}_" + base_name)

    # Ghi DataFrame (có thêm cột BLEU-n) ra Excel
    df.to_excel(out_path, index=False)

    # In toàn bộ dữ liệu ra terminal (debug / kiểm tra nhanh)
    with pd.option_context("display.max_rows", None, "display.max_columns", None):
        print(df)

    print(f"✅ Đã tạo file: {out_path}")
    return out_path
