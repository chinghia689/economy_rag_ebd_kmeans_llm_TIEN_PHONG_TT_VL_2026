# import re


# def remove_think_tags(text: str) -> str:
#     """
#     Xóa toàn bộ nội dung nằm trong cặp <think>...</think> khỏi chuỗi.

#     Args:
#         text (str): Chuỗi đầu vào.

#     Returns:
#         str: Chuỗi đã được làm sạch.
#     """
#     cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
#     return cleaned_text.strip()
