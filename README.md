# ERC-RAG

**ERC-RAG (Energy-based Retrieval Clustering for Retrieval-Augmented Generation)** là phương pháp truy xuất tăng cường cho chatbot hỏi đáp kinh tế tiếng Việt. Phương pháp kết hợp tìm kiếm vector, phân cụm tài liệu và khoảng cách năng lượng (*energy distance*) để chọn ngữ cảnh phù hợp trước khi mô hình ngôn ngữ tạo câu trả lời.

Xem [README hướng dẫn ứng dụng và pipeline ERC](Folder_All/README.md).

## Ý tưởng

RAG thông thường thường xếp hạng từng đoạn tài liệu riêng lẻ bằng cosine similarity. ERC-RAG bổ sung bước đánh giá các nhóm tài liệu: sau khi lấy tập ứng viên ban đầu, hệ thống gom các đoạn có embedding gần nhau thành cụm, rồi so sánh embedding của câu hỏi với phân bố embedding trong từng cụm. Cụm có khoảng cách năng lượng nhỏ nhất được chọn làm nguồn ngữ cảnh.

## Quy trình

1. Mã hóa câu hỏi thành vector và dùng cosine similarity lấy 40 đoạn tài liệu ứng viên.
2. Phân cụm các vector tài liệu bằng K-Means; số cụm được chọn theo silhouette score.
3. Tính energy distance giữa vector câu hỏi và các vector trong từng cụm.
4. Chọn cụm có energy distance thấp nhất.
5. Dùng mô hình ngôn ngữ lọc các tài liệu liên quan trong cụm được chọn, sau đó tạo câu trả lời dựa trên phần ngữ cảnh còn lại.

## Đánh giá

ERC-RAG được đánh giá cho bài toán hỏi đáp kinh tế tiếng Việt trên Vietnamese Economy Information Database (VEID), sử dụng bộ câu hỏi VNEIQAD. Tài liệu nghiên cứu báo cáo các chỉ số chất lượng câu trả lời như ROUGE-2 và BLEU-2, cùng các chỉ số truy xuất như MRR, Hit@5 và NDCG@5.

## Tài liệu tham khảo

Chi-Nghia Ngo và Anh-Khoi Ngo-Ho, “ERC-RAG: An Energy-based Retrieval Clustering for RAG in Vietnamese Economy Chatbots.”
