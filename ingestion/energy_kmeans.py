import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings("ignore", category=UserWarning) # Ẩn cảnh báo của K-Means
from sklearn.metrics.pairwise import cosine_similarity
from ingestion.energy_base_distance import energy_base_distance


class EnergyRetriever:
    """
    Module Truy xuất thông tin nâng cao sử dụng Energy-Based Distance và K-Means.

    Lưu ý: retrieve() trong class này là code cũ, không đúng với pipeline
    Energy Distance hiện tại vì X chỉ có 1 vector query gốc, chưa tạo thành
    phân phối query từ nhiều query vectors.

    Pipeline chatbot hiện tại dùng SplitQueryEnergyRetriever trong
    ingestion/query_splitter.py để tính Energy Distance đúng giữa 2 phân phối:
        X = phân phối query vectors [câu hỏi gốc + các câu hỏi con]
        Y = phân phối document vectors trong từng cụm K-Means.
    """
    def __init__(self, vector_store, embeddings_model, k_retrieve=40, n_top_clusters=1):
        """
        Khởi tạo Energy Retriever.
        
        Args:
            vector_store: Chroma vector store
            embeddings_model: Model embedding (HuggingFace embeddings)
            k_retrieve: Số top documents để retrieve (mặc định 40)
            n_top_clusters: Số clusters tốt nhất để lấy docs (mặc định 1)
        """
        # retriever chuẩn dùng Cosine (Lấy diện rộng)
        self.retriever = vector_store.as_retriever(search_kwargs={'k': k_retrieve})
        self.embeddings = embeddings_model
        self.n_top_clusters = n_top_clusters
        self.vector_store = vector_store

    def retrieve(self, query):
        """
        Truy xuất documents dựa trên query sử dụng Energy Distance.
        
        Args:
            query (str): Câu hỏi/query của người dùng
            
        Returns:
            List[Document]: Danh sách Document objects liên quan nhất
        """
        print(f"\n🔎 [Energy Retriever] Đang xử lý câu hỏi: '{query}'")
        
        # 1. Truy xuất diện rộng (Top 40 từ cosine similarity)
        docs = self.retriever.invoke(query)
        if not docs:
            print("   -> ⚠️ Không tìm thấy tài liệu thô nào.")
            return []

        context = [doc.page_content for doc in docs]

        # 2. Embedding lại query và context.
        # Code cũ: query chỉ có 1 vector nên không biểu diễn đúng phân phối query.
        # Pipeline chính dùng query_splitter.py để tạo nhiều query vectors trước khi tính ED.
        doc_vectors = np.array(self.embeddings.embed_documents(context))
        query_vector = np.array(self.embeddings.embed_query(query)).reshape(1, -1)

        # 3. Tính cosine similarity cho từng doc (dùng để log)
        sims = cosine_similarity(query_vector, doc_vectors)[0]
        print(f"   -> Max Cosine Similarity: {np.max(sims):.4f}")

        # 4. Đưa toàn bộ 40 docs vào K-Means 
        n_samples = len(doc_vectors)
        print(f"   -> 📋 Đưa toàn bộ {n_samples} docs vào K-Means")

        # 5. Gom cụm K-Means
        max_possible_k = min(10, n_samples - 1)
        
        best_k = 2
        best_labels = None
        
        if n_samples > 2:
            best_score = -1.0
            
            for k in range(2, max_possible_k + 1):
                kmeans_temp = KMeans(n_clusters=k, random_state=42, n_init='auto')
                labels_temp = kmeans_temp.fit_predict(doc_vectors)
                
                score = silhouette_score(doc_vectors, labels_temp)
                
                if score > best_score:
                    best_score = score
                    best_k = k
                    best_labels = labels_temp
            
            print(f"   -> 🤖 Tự động chọn K tối ưu = {best_k} (Silhouette Score cao nhất: {best_score:.4f})")
            labels = best_labels
            actual_k = best_k
            
        else:
            best_k = 1
            labels = np.zeros(n_samples, dtype=int)
            actual_k = best_k
            print(f"   -> ⚠️ Số lượng docs quá ít ({n_samples}), tự động gom thành 1 cụm.")


        # 6. Tính Energy Distance cho từng cụm và xếp hạng
        cluster_energies = []
        for i in range(actual_k):
            cluster_mask = labels == i
            if not np.any(cluster_mask):
                continue
                
            cluster_vectors = doc_vectors[cluster_mask]
            # Code cũ: không dùng kết quả này để mô tả pipeline hiện tại,
            # vì X chỉ có 1 query vector. Với chatbot hiện tại, ED được tính bằng:
            # energy_base_distance(query_vectors, cluster_vectors)
            # trong SplitQueryEnergyRetriever, trong đó query_vectors gồm câu hỏi gốc + câu hỏi con.
            energy = energy_base_distance(query_vector, cluster_vectors)
            cluster_energies.append((i, energy))
        
        cluster_energies.sort(key=lambda x: x[1])
        
        # 7. Lấy docs từ top N clusters
        n_select = min(self.n_top_clusters, len(cluster_energies))
        selected_clusters = cluster_energies[:n_select]
        
        for idx, (cluster_id, energy) in enumerate(selected_clusters):
            print(f"   -> {'🏆' if idx == 0 else '📌'} Cụm {cluster_id} - Energy Distance = {energy:.4f}")
        
        # Gom tất cả docs từ các cụm được chọn
        final_docs = []
        seen = set()
        for cluster_id, _ in selected_clusters:
            win_mask = labels == cluster_id
            win_local_indices = np.where(win_mask)[0]
            for li in win_local_indices:
                if li not in seen:
                    seen.add(li)
                    final_docs.append(docs[li])

        print(f"   -> ✅ Truy xuất {len(final_docs)} documents từ top {n_select} clusters")
        return final_docs

