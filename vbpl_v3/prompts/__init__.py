"""Prompt LLM nằm ở các file .txt trong thư mục này. Sửa file là đủ; không cần sửa code.

Nội dung prompt nằm trong khóa cache, nên sửa prompt làm các kết quả LLM đã lưu của prompt đó chạy lại."""
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=None)
def load(name):
    return (Path(__file__).parent / f'{name}.txt').read_text(encoding='utf-8')
