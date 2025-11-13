"""
Phase2用のPydanticモデル
埋め込み誤りのデータ構造を定義
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class EmbeddedError(BaseModel):
    """埋め込む誤りを表すPydanticモデル"""

    error_id: int = Field(..., description="誤りID")
    checklist_item: str = Field(..., description="チェックリスト項目", min_length=1)
    category: str = Field(..., description="カテゴリ", min_length=1)
    before: str = Field(..., description="誤りを含む元の文", min_length=1)
    after: str = Field(..., description="誤りを埋め込んだ文", min_length=1)
    location: str = Field(..., description="論文中の位置", min_length=1)
    description: str = Field(default="", description="誤りの説明")

    @field_validator('checklist_item', 'category', 'before', 'after', 'location', 'description')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """前後の空白を削除"""
        return v.strip()

    def __repr__(self):
        return (
            f"Error {self.error_id}:\n"
            f"  Item: {self.checklist_item}\n"
            f"  Category: {self.category}\n"
            f"  Location: {self.location}\n"
            f"  Before: {self.before[:50]}...\n"
            f"  After: {self.after[:50]}..."
        )


class EmbeddingResponse(BaseModel):
    """埋め込み誤り応答全体を表すPydanticモデル"""

    errors: List[EmbeddedError] = Field(
        default_factory=list,
        description="埋め込む誤りのリスト"
    )
    total_count: int = Field(default=0, description="誤りの総数")

    @field_validator('total_count')
    @classmethod
    def validate_total_count(cls, v: int, info) -> int:
        """total_countがerrorsの数と一致するか確認"""
        errors = info.data.get('errors', [])
        if v == 0 and errors:
            return len(errors)
        return v
