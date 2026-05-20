import os
import pandas as pd
import numpy as np


def cosine_similarity(vec_a, vec_b):
    """
    Tính toán Cosine Similarity giữa hai vector embedding.

    Args:
        vec_a (np.ndarray): Vector embedding thứ nhất.
        vec_b (np.ndarray): Vector embedding thứ hai.

    Returns:
        float: Giá trị cosine similarity trong khoảng [-1, 1].
               - Gần 1  → hai câu gần giống nghĩa.
               - Gần 0  → không liên quan.
               - Âm    → nghĩa trái ngược (hiếm gặp trong embeddings).
    """
    # Tích vô hướng của 2 vector
    dot = np.dot(vec_a, vec_b)

    # Chuẩn hóa (norm) từng vector
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    # Trả về similarity (nếu norm khác 0)
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def cosine_excel(file_path, embeddings, out: str = None):
    df = pd.read_excel(file_path)

    refs = df.iloc[:, 1].astype(str).tolist()
    gens = df.iloc[:, 3].astype(str).tolist()

    # Batch embedding (NHANH HƠN RẤT NHIỀU)
    ref_vecs = np.array(embeddings.embed_documents(refs))
    gen_vecs = np.array(embeddings.embed_documents(gens))

    # Vectorized cosine similarity
    ref_norm = ref_vecs / np.linalg.norm(ref_vecs, axis=1, keepdims=True)
    gen_norm = gen_vecs / np.linalg.norm(gen_vecs, axis=1, keepdims=True)

    df["Cosine Similarity"] = np.sum(ref_norm * gen_norm, axis=1)

    if not out:
        base = os.path.basename(file_path)
        out = os.path.join(os.path.dirname(file_path), "cosine_" + base)

    df.to_excel(out, index=False)
    print(f"✅ Đã tạo file: {out}")
    return out


# def cosine_excel(file_path, embeddings, out: str = None):
#     """
#     Đọc file Excel, tính Cosine Similarity giữa câu tham chiếu (reference)
#     và câu sinh ra bởi LLM (generated), sau đó lưu kết quả ra file Excel mới.

#     Args:
#         file_path (str): Đường dẫn tới file Excel gốc.
#                          Giả định:
#                            - Cột thứ 2 (index=1) là Reference (ground truth).
#                            - Cột thứ 4 (index=3) là Generated (mô hình sinh).
#         embeddings (OpenAIEmbeddings | OllamaEmbeddings):
#             Đối tượng embeddings đã khởi tạo để sinh vector.
#         out (str, optional): Đường dẫn file Excel output.
#                              Nếu không truyền → tạo tên file mới
#                              với prefix "cosine_".

#     Returns:
#         str: Đường dẫn file Excel đã tạo (có thêm cột "Cosine Similarity").
#     """
#     # Đọc dữ liệu gốc từ Excel
#     df = pd.read_excel(file_path)

#     # ========================
#     # Tính Cosine Similarity cho từng dòng
#     # ========================
#     df["Cosine Similarity"] = df.apply(
#         lambda row: cosine_similarity(
#             np.array(embeddings.embed_query(str(row[1]))),  # vector của Reference
#             np.array(embeddings.embed_query(str(row[3]))),  # vector của Generated
#         ),
#         axis=1,
#     )

#     # ========================
#     # Xác định đường dẫn file output
#     # ========================
#     if out:
#         out_path = out
#     else:
#         base_name = os.path.basename(file_path)
#         dir_name = os.path.dirname(file_path)
#         out_path = os.path.join(dir_name, f"cosine_" + base_name)

#     # ========================
#     # Xuất kết quả ra Excel
#     # ========================
#     df.to_excel(out_path, index=False)

#     # In toàn bộ bảng ra màn hình (debug/kiểm tra nhanh)
#     with pd.option_context("display.max_rows", None, "display.max_columns", None):
#         print(df)

#     print(f"✅ Đã tạo file: {out_path}")
#     return out_path
