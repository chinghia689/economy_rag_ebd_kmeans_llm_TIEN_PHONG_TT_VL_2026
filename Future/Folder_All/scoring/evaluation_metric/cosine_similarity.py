import os
import pandas as pd
import numpy as np


def cosine_excel(file_path, embeddings, out: str = None):
    """
    Đọc file Excel, tính Cosine Similarity giữa ground_truth và answer bằng batch embedding,
    sau đó lưu kết quả ra file Excel mới.

    Args:
        file_path (str): File Excel input — cột thứ 2 (index=1) là Reference (ground_truth),
                         cột thứ 4 (index=3) là Generated (answer).
        embeddings: Đối tượng embedding (vd: HuggingFace E5).
        out (str, optional): Đường dẫn output. Nếu None → prefix "cosine_".

    Returns:
        str: Đường dẫn file Excel đã tạo (có thêm cột "Cosine Similarity").
    """
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
