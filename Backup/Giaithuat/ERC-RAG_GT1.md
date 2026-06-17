# ERC-RAG: An Energy-based Retrieval Clustering for RAG in Vietnamese Economy Chatbots

**Anh-Khoi Ngo-Ho¹, Chi-Nghia Ngo¹, Anh-Khoa Ngo-Ho¹**
¹ Faculty of Information Technology, Nam Can Tho University, 168 Nguyen Van Cu Street, An Binh Ward, Can Tho City, Vietnam.
{nhakhoi@nctu.edu.vn; nhakhoa@nctu.edu.vn; nghia220321@student.nctu.edu.vn}

---

## Abstract

Retrieval-Augmented Generation (RAG) đã trở thành khung làm việc hiệu quả để nâng cao độ chính xác về sự kiện và độ tin cậy cho chatbot dựa trên large language model (LLM), đặc biệt trong question answering theo lĩnh vực chuyên biệt. Tuy nhiên, hầu hết các hệ thống RAG hiện nay dựa vào cosine similarity trên dense embeddings cho khâu truy hồi tài liệu, vốn chỉ là một xấp xỉ tuyến tính của độ tương thích ngữ nghĩa và có thể chưa đủ tinh tế cho các lĩnh vực phức tạp như hỏi đáp kinh tế. Trong nghiên cứu này, chúng tôi đề xuất khung **Energy-based Retrieval Clustering RAG (ERC-RAG)** cho chatbot kinh tế Việt Nam. Cách tiếp cận đề xuất nhúng truy vấn người dùng thành một vector duy nhất, áp dụng cosine similarity để lấy tập tài liệu ứng viên, sau đó dùng **energy distance** giữa vector truy vấn và từng cụm tài liệu KMeans để chọn cụm liên quan nhất phục vụ sinh câu trả lời. Chúng tôi đánh giá khung trên Vietnamese Economy Information Database (VEID) bằng benchmark VNEIQAD. Kết quả thực nghiệm cho thấy ERC-RAG cải thiện hiệu năng truy hồi so với các biến thể RAG quy ước, tạo ra câu trả lời tập trung hơn và chính xác về mặt số liệu. Phát hiện của chúng tôi cung cấp bằng chứng thực nghiệm rằng energy distance giữa truy vấn và phân phối tài liệu là một hướng tiếp cận hứa hẹn cho cluster-level retrieval trong các hệ thống RAG chuyên biệt theo lĩnh vực, đặc biệt với các ngôn ngữ ít tài nguyên như tiếng Việt.

**Keywords:** automatic question answering, chatbot, Vietnamese language, generative AI, retrieval-augmented generation, energy-based models, energy distance, KMeans clustering, retrieval clustering.

---

## 1. Introduction

Chatbots là các hệ thống phần mềm mô phỏng đối thoại con người qua giao tiếp văn bản hoặc giọng nói. Chúng đã được áp dụng cho nhiều lĩnh vực chuyên biệt, bao gồm hiểu ngôn ngữ tự nhiên dựa trên đồ thị tri thức (Ait-Mlouk & Jiang, 2020) và tư vấn y tế thông minh (Ni et al., 2024). Những năm gần đây, hầu hết chatbot hiệu năng cao được xây dựng trên LLM, cho phép sinh phản hồi mạch lạc, có ngữ cảnh và trôi chảy. RAG đã nổi lên như giải pháp được chấp nhận rộng rãi để cải thiện độ tin cậy và bám sát sự kiện của các hệ thống dựa trên LLM. Thay vì chỉ dựa vào tri thức tham số mã hoá trong trọng số mô hình, RAG truy hồi các tài liệu liên quan từ nguồn tri thức ngoài và điều kiện hoá quá trình sinh trên ngữ cảnh đã truy hồi. Mô hình này đã được chứng minh giúp giảm ảo giác, nâng cao tính đúng đắn của câu trả lời và cho phép cập nhật tri thức mà không cần huấn luyện lại mô hình ngôn ngữ. Các nghiên cứu gần đây đã chứng minh hiệu quả của RAG cho chatbot tiếng Việt, đặc biệt trong các nhiệm vụ hỏi đáp chuyên biệt theo lĩnh vực (Ngo-Ho et al., 2024a; Ngo-Ho et al., 2024b).

Trong các hệ thống RAG dựa trên tài liệu, nhiều kỹ thuật đã được đề xuất để cải thiện chất lượng truy hồi, bao gồm maximal marginal relevance để cân bằng tính liên quan và tính đa dạng (Ye et al., 2023), các chiến lược truy hồi lai kết hợp dense vector search với phương pháp dựa trên từ khoá thưa như BM25 (Chen et al., 2023; Sawarkar et al., 2024). Dù vậy, hầu hết các retriever RAG hiện đại vẫn dựa vào cosine similarity trên dense embeddings như hàm cho điểm liên quan chính. Mặc dù hiệu quả về mặt tính toán, cosine similarity giả định một quan hệ hình học tuyến tính giữa các embedding và có thể không nắm bắt được sự tương thích truy vấn–tài liệu phức tạp hay đặc thù theo nhiệm vụ, đặc biệt trong các lĩnh vực yêu cầu căn chỉnh chính xác về số liệu như hỏi đáp kinh tế.

Hạn chế này đặc biệt rõ trong chatbot kinh tế Việt Nam, nơi sự lệch ngữ nghĩa nhỏ hay đoạn văn bản liên quan lỏng lẻo có thể dẫn tới diễn giải số liệu sai. Các quan sát này thúc đẩy việc khám phá các cách tiếp cận mô hình hoá độ liên quan vượt ra ngoài các phép đo tương tự tuyến tính trong khi vẫn tương thích với các pipeline RAG thực tế.

Trong bài báo này, chúng tôi đề xuất khung **ERC-RAG** dành cho chatbot kinh tế Việt Nam. Cách tiếp cận đề xuất dùng kiến trúc hai giai đoạn: (i) cosine similarity trên embedding truy vấn đơn để truy hồi tập tài liệu ứng viên một cách hiệu quả; và (ii) energy distance giữa vector truy vấn và từng cụm tài liệu KMeans để chọn cụm tương thích ngữ nghĩa nhất làm ngữ cảnh sinh. Cách thiết kế này cho phép một biểu diễn về độ liên quan tài liệu phong phú hơn so với việc xếp hạng tài liệu riêng lẻ theo cosine.

Chúng tôi thực hiện đánh giá thực nghiệm trên Vietnamese Economy Information Database (VEID) sử dụng benchmark VNEIQAD. Kết quả cho thấy ERC-RAG cải thiện hiệu năng truy hồi so với các baseline RAG được dùng rộng rãi. Phát hiện của chúng tôi gợi ý rằng energy distance giữa một truy vấn và phân phối cụm tài liệu là một hướng khả thi cho cluster-level retrieval trong RAG chuyên biệt và ít tài nguyên.

---

## 2. Energy-based Concepts in LLMs and RAG

Một khung RAG thường bao gồm thành phần truy hồi thông tin (retriever) tìm kiếm tri thức ngoài từ các nguồn có hoặc không có cấu trúc như cơ sở dữ liệu, sách, bài báo và tài liệu web. Tuỳ vào yêu cầu ngữ nghĩa, retriever có thể được hiện thực bằng các cơ chế lưu trữ và truy hồi khác nhau, gồm vector database, graph database hoặc SQL database. Trong nghiên cứu này, khung RAG của chúng tôi dùng vector database để lưu tri thức kinh tế, các chiến lược truy hồi khác để dành cho nghiên cứu tương lai.

Các nghiên cứu gần đây cũng đã khảo sát việc tích hợp energy-based models (EBM) với LLM để cải thiện hiệu năng truy hồi và sinh. Được LeCun et al. (2006) giới thiệu, EBM gán điểm năng lượng thấp cho các cặp đầu vào–đầu ra tương thích, cung cấp một khung mô hình xác suất linh hoạt mà không cần chuẩn hoá rõ ràng. Bhattacharyya et al. (2021) giới thiệu xếp hạng lại dựa trên năng lượng cho dịch máy. Shankar et al. (2025) áp dụng EBM trong RAG y tế để học một energy landscape mượt trên các cặp truy vấn–tài liệu. Cai et al. (2025) đề xuất Entriever, retriever dựa trên năng lượng cho hệ thống đối thoại tri thức.

Lấy cảm hứng từ khái niệm năng lượng như một thế năng vô hướng — trong đó các cấu hình mong muốn ứng với năng lượng thấp và cấu hình không khớp ứng với năng lượng cao — chúng tôi áp dụng **energy distance** (Rizzo & Székely, 2016) như một độ đo trong giai đoạn truy hồi của RAG. Khác với cosine similarity vốn đo căn chỉnh góc trong không gian embedding, energy distance có thể được hiểu như một khoảng cách thống kê giữa các phân phối xác suất, cho phép so sánh giữa truy vấn và các cụm tài liệu một cách giàu thông tin hơn (Kayal et al., 2021).

Mặc dù các công trình này cho thấy tiềm năng, việc khám phá energy distance cho việc chọn cụm trong các pipeline RAG vẫn ở giai đoạn sơ khai. Thuật toán đề xuất trong bài báo này đóng góp vào dòng nghiên cứu mới nổi này bằng cách kết hợp tính điểm cụm dựa trên năng lượng vào RAG cho các ứng dụng LLM chuyên biệt theo lĩnh vực.

---

## 3. ERC-RAG Framework for Vietnamese Economy Chatbots

Trong phần này, theo các công trình của (Ngo-Ho et al., 2024a; Ngo-Ho et al., 2024b), chúng tôi mô tả khung ERC-RAG cho Generative Vietnamese Economy Chatbot (GVEC), bổ sung pipeline RAG quy ước hai thành phần chính: **KMeans clustering** trên tài liệu ứng viên và **energy distance scoring** giữa vector truy vấn và từng cụm tài liệu.

Pipeline RAG quy ước bắt đầu bằng việc nhúng truy vấn của người dùng và các tài liệu trong vector database bằng một embedding model để tạo ra biểu diễn dày. Truy hồi sau đó xác định các tài liệu liên quan bằng cách tính độ tương tự ngữ nghĩa, thường thông qua cosine similarity. Các tài liệu có điểm cosine cao nhất được chọn làm top-k ứng viên. Các ngữ cảnh này được nối vào prompt và đưa vào LLM để sinh, đảm bảo phản hồi bám sát tri thức ngoài để giảm ảo giác. Cách tiếp cận này, dù hiệu quả cho căn chỉnh ngữ nghĩa chung, thường gặp khó khăn với tính tương thích tinh tế trong các nhiệm vụ chuyên biệt như hỏi đáp kinh tế.

Thuật toán đề xuất được thúc đẩy bởi quan sát rằng trong hầu hết hệ thống RAG hiện có, cosine similarity chủ yếu nắm bắt độ gần hình học trong không gian embedding và có thể chỉ cung cấp một xấp xỉ giới hạn cho độ tương thích ngữ nghĩa thực sự giữa truy vấn và tài liệu ứng viên. Để giải quyết hạn chế này mà không hy sinh hiệu suất, chúng tôi áp dụng kiến trúc truy hồi hai giai đoạn kết hợp **single-query cosine-based candidate retrieval** và **energy-based cluster selection**.

Ở giai đoạn đầu, truy vấn người dùng được nhúng thành một vector duy nhất và được dùng để truy hồi top-N tài liệu ứng viên từ vector database thông qua cosine similarity. Đây là cơ chế truy hồi hạng nhẹ chuẩn, cung cấp một pool tài liệu liên quan có chất lượng làm đầu vào cho giai đoạn chọn cụm.

Ở giai đoạn hai, các tài liệu ứng viên được nhóm thành các cụm ngữ nghĩa nhất quán bằng KMeans, với số cụm tối ưu được xác định tự động qua silhouette score. Với mỗi cụm, energy distance được tính giữa vector truy vấn X = {f(q)} (một điểm) và phân phối tài liệu cụm Y = {f(d) | d ∈ cluster}, theo công thức của Rizzo & Székely (2016):

$$
\mathcal{E}(X, Y) = 2\,\mathbb{E}\|X - Y\| - \mathbb{E}\|X - X'\| - \mathbb{E}\|Y - Y'\|
$$

trong đó khoảng cách giữa vector truy vấn và embedding tài liệu được tính bằng Euclidean distance, theo Kayal et al. (2021). Vì X chỉ có một điểm, thành phần E‖X − X'‖ = 0, và công thức rút gọn về:

$$
\mathcal{E}(X, Y) = 2 \cdot \frac{1}{|Y|}\sum_{y \in Y} \|f(q) - y\| - \frac{1}{|Y|^2}\sum_{y, y' \in Y}\|y - y'\|
$$

Trong thực tế, energy distance được clip về không âm để tránh sai số số học.

Cụm có energy distance tối thiểu so với truy vấn được chọn, và các tài liệu trong cụm được đưa qua LLM để lọc liên quan trước khi sử dụng làm ngữ cảnh cho sinh câu trả lời. Bằng việc đánh giá cụm như một phân phối tài liệu thay vì các tài liệu riêng lẻ, energy-based scoring nắm bắt được cấu trúc ngữ nghĩa của cụm và cho phép chọn cụm có nhận biết phân phối trong pipeline RAG.

Khung ERC-RAG đề xuất có thể được đặt trong bối cảnh tài liệu hiện đại về truy hồi và RAG như một cách tiếp cận truy hồi dựa trên cụm có nhận biết phân phối, tích hợp hai thành phần bổ sung: **KMeans document clustering** và **energy-based distribution matching**. Các cách tiếp cận RAG dựa trên cụm trước đây thường chọn tài liệu từ các cụm dựa trên điểm tương đồng cấp tài liệu hoặc tổng hợp heuristic. Ngược lại, ERC-RAG sử dụng energy distance giữa truy vấn và mỗi phân phối cụm tài liệu làm tiêu chí chọn cụm, xem mỗi cụm là một phân phối xác suất. Cách đối sánh truy vấn–phân phối này phù hợp với nền tảng lý thuyết của energy distance (Székely & Rizzo, 2013; Rizzo & Székely, 2016) và khung k-groups (Li & Rizzo, 2017).

---

## 4. Algorithm: Energy-based Retrieval Clustering RAG (ERC-RAG)

**Input:**
- Truy vấn `q`
- Tập tài liệu `D`
- Embedding model `f(·)`
- Kích thước pre-retrieval `N = 40`

**Output:** Câu trả lời sinh `r`

---

**Step 1 — Query Input.** Hệ thống nhận một truy vấn văn bản từ người dùng:
$$
q \in \mathcal{Q}
$$

**Step 2 — Query Embedding.** Truy vấn được nhúng bằng mô hình **multilingual E5** (Wang et al., 2022) để tạo vector biểu diễn:
$$
\mathbf{x} = f(q), \qquad X = \{\mathbf{x}\}
$$

Phân phối truy vấn X là một phân phối suy biến (degenerate) chỉ gồm một điểm duy nhất.

**Step 3 — Cosine Similarity Retrieval.** Truy hồi top-N tài liệu ứng viên từ vector database thông qua cosine similarity:
$$
\mathcal{C} = \text{TopN}_{d \in D} \cos\!\left(f(q),\, f(d)\right), \qquad |\mathcal{C}| = N
$$

**Step 4 — Document Embedding Matrix.** Xây dựng ma trận embedding của các tài liệu đã truy hồi:
$$
\mathbf{V} = \big[f(d_1), f(d_2), \ldots, f(d_N)\big] \in \mathbb{R}^{N \times 768}
$$

**Step 5 — Automatic Cluster Number Selection.** Với mỗi cấu hình clustering `k ∈ {2, …, min(10, N − 1)}`, áp dụng KMeans và tính silhouette score. Số cụm tối ưu được chọn theo:
$$
k^* = \arg\max_{k}\; \mathrm{Silhouette}(k)
$$

**Step 6 — Final KMeans Clustering.** Áp dụng KMeans với số cụm tối ưu `k*`:
$$
\{\mathcal{C}_1, \mathcal{C}_2, \ldots, \mathcal{C}_{k^*}\} = \text{KMeans}(\mathbf{V},\, k^*)
$$

Mỗi cụm nhóm các tài liệu ngữ nghĩa tương tự.

**Step 7 — Energy-based Cluster Scoring.** Với mỗi cụm `C_j`, tính energy distance giữa vector truy vấn X = {f(q)} và phân phối tài liệu cụm Y_j = {f(d) | d ∈ C_j}:

$$
\mathcal{E}(X, Y_j) = \frac{2}{|Y_j|}\sum_{y \in Y_j}\|f(q) - y\| \;-\; \frac{1}{|Y_j|^2}\sum_{y, y' \in Y_j}\|y - y'\|
$$

Vì |X| = 1, thành phần `E‖X − X'‖ = 0` được rút gọn khỏi công thức. Trong thực tế, energy distance được clip về không âm.

**Step 8 — Cluster Selection.** Chọn cụm có energy distance tối thiểu:
$$
j^* = \arg\min_{j}\; \mathcal{E}(X, Y_j)
$$

Tập tài liệu tương ứng:
$$
\mathcal{D}_{j^*} = \{d \mid d \in \mathcal{C}_{j^*}\}
$$

**Step 9 — LLM-based Document Relevance Filtering.** Các tài liệu trong cụm được chọn được LLM đánh giá để xác định xem chúng có chứa thông tin liên quan đến truy vấn hay không. Tập tài liệu sau lọc:
$$
\mathcal{D}_{\text{filtered}} = \{d \in \mathcal{D}_{j^*} \mid \text{LLM-grade}(q, d) = \text{yes}\}
$$

**Step 10 — Response Generation.** Các tài liệu đã lọc được dùng làm ngữ cảnh trong khung RAG:
$$
r = \text{LLM}\big(\text{prompt}(q, \mathcal{D}_{\text{filtered}})\big)
$$

---

## 5. Related Work

### 5.1 Energy Distance and Clustering Methods

Energy distance đã được nghiên cứu rộng rãi như một độ đo thống kê để so sánh các phân phối xác suất. Khác với cosine similarity vốn đánh giá tương tự góc giữa các vector, energy distance nắm bắt sự khác biệt cấp phân phối bằng cách tổng hợp khoảng cách cặp giữa các mẫu (Székely & Rizzo, 2013; Rizzo & Székely, 2016). Tính chất này khiến nó đặc biệt phù hợp để so sánh các tập embedding thay vì biểu diễn riêng lẻ.

Nghiên cứu trước đây đã khám phá tích hợp energy distance vào các thuật toán clustering. Đáng chú ý, phương pháp k-groups tổng quát hoá KMeans bằng cách thay mục tiêu dựa trên centroid bằng energy distance, cho phép clustering trên các phân phối thay vì dựa vào trung bình Euclidean (Li & Rizzo, 2017).

Trong xử lý ngôn ngữ tự nhiên, phương pháp dựa trên năng lượng đã được áp dụng cho ranking và compatibility modeling. Bhattacharyya et al. (2021) đề xuất xếp hạng lại dựa trên năng lượng cho neural machine translation. Cai et al. (2025) giới thiệu Entriever, retriever dựa trên năng lượng mô hình hoá tương thích query–document. Shankar et al. (2025) khám phá EBM trong RAG để cải thiện độ tin cậy và ước lượng bất định.

Mặc dù có những tiến bộ này, các công trình hiện hữu chủ yếu sử dụng phương pháp năng lượng cho clustering, reranking cấp tài liệu hoặc ước lượng độ tin cậy, chứ không phải để **xếp hạng cụm** dựa trên độ tương tự phân phối với truy vấn — vốn vẫn còn ít được nghiên cứu.

### 5.2 Clustering for Retrieval-Augmented Generation

Clustering đã nổi lên như chiến lược hiệu quả để cải thiện chất lượng truy hồi và hiệu quả ngữ cảnh trong RAG. Bằng cách nhóm các tài liệu ngữ nghĩa tương tự, clustering có thể giảm dư thừa, cải thiện tính đa dạng và giảm tràn ngữ cảnh khi tương tác với LLM.

Các nghiên cứu gần đây đề xuất các khung truy hồi dựa trên cụm để nâng cao hiệu năng RAG. Một số công trình tổ chức các tài liệu đã truy hồi thành các cụm ngữ nghĩa để nén ngữ cảnh và cải thiện lập luận downstream của LLM bằng cách chỉ trình bày thông tin đại diện nhất từ mỗi cụm. Tuy nhiên, các phương pháp này thường dựa vào điểm tương tự cấp tài liệu (ví dụ cosine similarity) hoặc các chiến lược tổng hợp heuristic. Chúng không mô hình hoá rõ ràng quan hệ phân phối giữa truy vấn và toàn bộ cụm, hạn chế khả năng nắm bắt cấu trúc ngữ nghĩa bậc cao trong tài liệu đã truy hồi.

### 5.3 Reranking and Retrieval Optimization in RAG

Reranking là thành phần cốt lõi trong các hệ thống truy hồi hiện đại, nhằm tinh chỉnh thứ tự các tài liệu ứng viên sau giai đoạn truy hồi ban đầu. Các cách tiếp cận truyền thống dựa vào kiến trúc cross-encoder mã hoá đồng thời cặp truy vấn–tài liệu để cho điểm liên quan (Nogueira & Cho, 2019). Công trình gần đây khám phá các chiến lược truy hồi lai kết hợp biểu diễn dày và thưa (Chen & Wiseman, 2023; Sawarkar et al., 2024), cũng như các phương pháp reranking dựa trên LLM (Sun et al., 2023).

Trong bối cảnh RAG, reranking thường được dùng để cải thiện chất lượng ngữ cảnh đã truy hồi trước khi sinh. Tuy nhiên, hầu hết các cách tiếp cận reranking hiện có hoạt động ở cấp tài liệu riêng lẻ, bỏ qua quan hệ cấu trúc giữa các tài liệu đã truy hồi.

### 5.4 Research Gap

Tóm lại, các công trình trước đây đã nghiên cứu:
- energy distance cho clustering và compatibility modeling,
- clustering để cải thiện hiệu quả truy hồi và tổ chức ngữ cảnh,
- và các kỹ thuật reranking để tinh chỉnh độ liên quan tài liệu trong RAG.

Tuy nhiên, vẫn thiếu các cách tiếp cận tích hợp các hướng này để thực hiện: **xếp hạng cụm cấp phân phối dùng energy distance trong khung RAG**. Khoảng trống này thúc đẩy cách tiếp cận đề xuất, giới thiệu cơ chế dựa trên năng lượng để đánh giá độ liên quan của các cụm như những phân phối, cho phép một quá trình truy hồi biểu cảm hơn cho hệ thống RAG.

---

## 6. Experimental Protocol

Chúng tôi sử dụng **Vietnamese Economy Information Database (VEID)**, phát hành năm 2024 và được giới thiệu trong các nghiên cứu trước (Ngo-Ho et al., 2024a; Ngo-Ho et al., 2024b). Theo hiểu biết của chúng tôi, VEID là cơ sở dữ liệu đầu tiên được thiết kế đặc biệt để đánh giá hệ thống chatbot trong lĩnh vực kinh tế Việt Nam. Trong Ngo-Ho et al. (2025), các tác giả đã trình bày một dataset benchmark gồm 1.000 cặp câu hỏi–trả lời được sinh tự động từ VEID. Trong nghiên cứu này, chúng tôi áp dụng dataset benchmark này.

Thí nghiệm tuân theo cùng giao thức như các nghiên cứu trước (Ngo-Ho et al., 2024a, 2024b, 2025), cho phép so sánh hiệu năng trực tiếp giữa các cấu hình mô hình khác nhau. Để đánh giá hiệu năng truy hồi của ERC-RAG, chúng tôi kiểm tra xem tài liệu top-1 được trả về bởi cụm có energy tối thiểu có chứa câu trả lời đúng hay không.

Cấu hình thực nghiệm như sau:
- **Chunking:** `RecursiveCharacterTextSplitter` với `chunk_size=600` ký tự, `chunk_overlap=80`, tạo ra **120.165** vector được index trong **ChromaDB**.
- **Embedding:** `intfloat/multilingual-e5-base` (768 chiều, L2-normalized), với E5 prefix protocol (`query:` và `passage:`).
- **Cosine retrieval:** lấy top **N = 40** tài liệu ứng viên cho truy vấn đơn.
- **KMeans:** `k ∈ {2, …, min(10, |C| − 1)}`, chọn k tối ưu theo silhouette score (`random_state=42`, `n_init='auto'`).
- **Document grading:** một lần gọi LLM theo batch trên tất cả tài liệu trong cụm được chọn, LLM trả về JSON array các index liên quan.
- **LLM:** cùng instance dùng cho document grading và answer generation.

Để đánh giá, chúng tôi sử dụng nhiều metric bổ sung lẫn nhau:
- **ROUGE-2** (Recall / Precision / F1) — đo trùng lặp n-gram.
- **BLEU-2** (Papineni et al., 2002) — đo trôi chảy và tương tự lexical.
- **Cosine Similarity** giữa câu trả lời sinh và câu trả lời tham chiếu.
- **MRR / Hit@5 / NDCG@5** — đo chất lượng xếp hạng truy hồi.

---

## 7. Results and Discussion

Về hiệu năng truy hồi, khi chỉ dùng cosine similarity, chatbot xác định đúng tài liệu top-relevant cho **42,3%** số cặp câu hỏi–trả lời. Bằng cách tích hợp ERC-RAG với truy vấn đơn, độ chính xác này tăng lên đáng kể. ERC-RAG đạt **MRR = 0,62**, **Hit@5 = 0,64** và **NDCG@5 = 0,83** trên benchmark VEID. Các metric truy hồi này cho thấy cơ chế chọn cụm dựa trên năng lượng hiệu quả trong việc đưa các tài liệu liên quan vào top-5, với chất lượng xếp hạng cao đo bằng NDCG@5.

Bảng 1 trình bày so sánh chi tiết giữa ERC-RAG đề xuất, Energy-based Reranking RAG baseline, và các baseline RAG quy ước trên dataset VEID, sử dụng các metric ROUGE-2 (Recall, Precision, F1), BLEU-2, Cosine Similarity, MRR, Hit@5 và NDCG@5. Các mô hình RAG baseline (ghép cặp với VinaLLaMA-7B-chat, Vistral-7B-chat, Openchat-3.5-7B, GPT-3.5-turbo hoặc GPT-4o-mini) chỉ báo cáo BLEU-2 từ 0,21 đến 0,46. Energy-based Reranking RAG baseline cung cấp thêm các metric ROUGE-2, trong khi ERC-RAG báo cáo thêm Cosine Similarity, MRR, Hit@5 và NDCG@5, mang lại đánh giá toàn diện nhất.

**Bảng 1.** So sánh hiệu năng của ERC-RAG (single-vector), Energy-based Reranking RAG baseline, và các mô hình RAG quy ước trên ROUGE-2 R/P/F1, BLEU-2, Cosine, MRR, Hit@5 và NDCG@5 trên VEID.

| # | Method | LLM | ROUGE-2 R | ROUGE-2 P | ROUGE-2 F1 | BLEU-2 | Cos | MRR | Hit@5 | NDCG@5 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Vanilla RAG | VinaLLaMA-7B | – | – | – | 0.21 | – | – | – | – |
| 2 | Vanilla RAG | Vistral-7B | – | – | – | 0.28 | – | – | – | – |
| 3 | Vanilla RAG | OpenChat-3.5 | – | – | – | 0.33 | – | – | – | – |
| 4 | Vanilla RAG | GPT-3.5-turbo | – | – | – | 0.41 | – | – | – | – |
| 5 | Vanilla RAG | GPT-4o-mini | – | – | – | 0.46 | – | – | – | – |
| 6 | Energy-Rerank RAG | Grok-4-1-fast | 0.49 | 0.59 | 0.49 | 0.34 | – | – | – | – |
| 7 | Energy-Rerank RAG | Gemini-2.5-flash-lite | 0.51 | 0.62 | 0.51 | 0.55 | – | – | – | – |
| 8 | Energy-Rerank RAG | GPT-4o-mini | 0.49 | 0.74 | 0.49 | 0.61 | – | – | – | – |
| 9 | **ERC-RAG (single-vector)** | **GPT-5.0-mini** | **0.68** | **0.70** | **0.68** | **0.65** | **0.95** | **0.62** | **0.64** | **0.83** |

Khung **ERC-RAG (single-vector)** với GPT-5.0-mini (hàng 9) đạt ROUGE-2 F1 = 0,68, ROUGE-2 Recall = 0,68, ROUGE-2 Precision = 0,70 và BLEU-2 = 0,65, cải thiện đáng kể so với cấu hình Energy-based Reranking RAG tốt nhất (ROUGE-2 F1: +0,19, BLEU-2: +0,04). F1 score cải thiện phản ánh cân bằng tốt hơn giữa coverage và precision đạt được bởi cơ chế chọn cụm có nhận biết phân phối.

ERC-RAG cũng báo cáo các metric ở cấp truy hồi không có sẵn cho các baseline. Cosine Similarity = 0,95 xác nhận căn chỉnh ngữ nghĩa mạnh giữa cụm được chọn và truy vấn. MRR = 0,62 và Hit@5 = 0,64 cho thấy tài liệu đúng xuất hiện trong top-5 ở khoảng 64% trường hợp, với NDCG@5 = 0,83 phản ánh chất lượng xếp hạng cao.

Tổng thể, ERC-RAG mang lại hiệu năng tốt nhất trên tất cả metric được báo cáo. Các kết quả này chứng minh rằng kết hợp **KMeans clustering ngữ nghĩa** và **energy-based distribution matching** giữa một truy vấn đơn và phân phối cụm tài liệu là một chiến lược mạnh để nâng cao chất lượng truy hồi và sinh trong các hệ thống RAG chuyên biệt theo lĩnh vực, đặc biệt cho các nhiệm vụ yêu cầu phản hồi chính xác và bám sát sự kiện trong lĩnh vực kinh tế Việt Nam.

---

## 8. Conclusion

Bài báo này giới thiệu khung **Energy-based Retrieval Clustering RAG (ERC-RAG)** cho chatbot kinh tế Việt Nam chuyên biệt theo lĩnh vực. Được thúc đẩy bởi các hạn chế của cosine similarity trong việc nắm bắt tính tương thích truy vấn–tài liệu phức tạp, chúng tôi đề xuất một kiến trúc hai giai đoạn: **cosine-based candidate retrieval** dùng truy vấn đơn, và **energy distance scoring** giữa vector truy vấn và từng cụm tài liệu KMeans. Bằng cách chọn cụm có energy distance tối thiểu làm ngữ cảnh sinh, ERC-RAG cho phép cơ chế truy hồi có nhận biết phân phối, biểu cảm hơn so với các cách tiếp cận dựa trên tương tự cấp tài liệu quy ước.

Từ một góc nhìn rộng hơn, công trình này đóng góp vào dòng nghiên cứu mới nổi khám phá các mô hình dựa trên năng lượng trong RAG. Không như các nghiên cứu trước chủ yếu dùng hàm năng lượng cho ước lượng độ tin cậy, reranking cấp tài liệu hoặc abstention, cách tiếp cận của chúng tôi vận hành hoá energy distance giữa truy vấn và các phân phối cụm như tín hiệu chọn cụm cốt lõi trong một pipeline RAG thực tế. Công trình tương lai sẽ khám phá mở rộng sang các phép đo phân phối khác (MMD, Wasserstein), tích hợp với phản hồi con người, và tối ưu hoá hiệu quả để cân bằng độ chính xác truy hồi, chất lượng phản hồi và chi phí tính toán trong triển khai thực tế.

---

## References

Ait-Mlouk, A., & Jiang, L. (2020). KBot: a Knowledge graph based chatBot for natural language understanding over linked data. *IEEE Access, 8*, 149220-149230.

Bhattacharyya, S., Rooshenas, A., Naskar, S., Sun, S., Iyyer, M., & McCallum, A. (2021). Energy-based reranking: Improving neural machine translation using energy-based models. In *Proceedings of ACL 2021*, 4528–4537.

Cai, Y., Li, K., Huang, Y., Feng, J., & Ou, Z. (2025). Entriever: Energy-based retriever for knowledge-grounded dialog systems. In *Findings of ACL 2025*, 21462–21474.

Chen, X., & Wiseman, S. (2023). BM25 query augmentation learned end-to-end. *arXiv:2305.14087*.

Chien Van Nguyen, et al. (2023). Vistral-7B-Chat — Towards a State-of-the-Art Large Language Model for Vietnamese.

Gutmann, M., & Hyvärinen, A. (2010). Noise-contrastive estimation. *AISTATS*.

Kayal, S. (2021). Unsupervised sentence-embeddings by manifold approximation and projection. *EACL*, 1–11.

Khattab, O., & Zaharia, M. (2020). ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT. *SIGIR*.

LeCun, Y., Chopra, S., Hadsell, R., Ranzato, M., & Huang, F. (2006). A tutorial on energy-based learning. In *Predicting Structured Data*, MIT Press.

Li, S., & Rizzo, M. L. (2017). K-groups: A Generalization of K-means Clustering. *arXiv:1711.04359*.

Ngo-Ho, A.-K., Vo, K.-D., & Ngo-Ho, A.-K. (2024a). GVEC: A Vietnamese Large Language Models Chatbot For Economy. *MAPR 2024*.

Ngo-Ho, A.-K., Vo, K.-D., & Ngo-Ho, A.-K. (2024b). GVEC: Generative Vietnamese Economy Chatbots using VNEIQAD benchmark. *ATC 2024*.

Ngo-Ho, A.-K., Vo, K.-D., & Ngo-Ho, A.-K. (2024c). VQABG: Vietnamese question/answers benchmark generator. *CTU Journal of Innovation and Sustainable Development, 16*(Special issue), 80-90.

Ngo-Ho, A.-K., Vo, K.-D., & Ngo-Ho, A.-K. (2025). Evaluation of Large Language Models for Vietnamese Language in GVEC Services. *ICESP 2024*, Springer Cham.

Nguyen, Q., Pham, H., & Dao, D. (2023). VinaLLaMA: LLaMA-based Vietnamese Foundation Model. *arXiv:2312.11011*.

Ni, P., Okhrati, R., Guan, S., & Chang, V. (2024). Knowledge graph and deep learning-based text-to-GraphQL model. *Information Systems Frontiers, 26*(1), 137-156.

Nogueira, R., & Cho, K. (2019). Passage re-ranking with BERT. *arXiv:1901.04085*.

Papineni, K., et al. (2002). BLEU: a method for automatic evaluation of machine translation. *ACL*.

Rizzo, M. L., & Székely, G. J. (2016). Energy distance. *WIREs Computational Statistics, 8*(1), 27–38.

Sawarkar, K., Mangal, A., & Solanki, S. R. (2024). Blended RAG. *IEEE MIPR 2024*, 155-161.

Shankar, R., et al. (2025). Energy landscapes enable reliable abstention in retrieval-augmented LLMs for healthcare. *arXiv:2509.04482*.

Sun, W., et al. (2023). Is ChatGPT good at search? *arXiv:2304.09542*.

Székely, G. J., & Rizzo, M. L. (2013). Energy statistics. *Journal of Statistical Planning and Inference, 143*(8), 1249–1272.

Wang, G., et al. (2023). Openchat: Advancing open-source language models with mixed-quality data. *arXiv:2309.11235*.

Wang, L., et al. (2022). Text embeddings by weakly-supervised contrastive pre-training. *arXiv:2212.03533*.

Ye, X., et al. (2023). Complementary explanations for effective in-context learning. *Findings of ACL 2023*, 4469-4484.
