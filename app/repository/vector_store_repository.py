"""
PGVector Repository 구현

PGVector를 사용하는 구체적인 Repository 구현입니다.
"""
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_postgres import PGVector

from app.repository.base import BaseVectorRepository


class PGVectorRepository(BaseVectorRepository):
    """PGVector를 사용하는 Repository 구현"""

    def __init__(self, vector_store: PGVector):
        """
        PGVector Repository를 초기화합니다.

        Args:
            vector_store: PGVector 인스턴스
        """
        self.vector_store = vector_store

    def search(self, query: str, k: int = 3) -> List[Document]:
        """
        유사도 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수

        Returns:
            관련 문서 리스트
        """
        return self.vector_store.similarity_search(query, k=k)

    def search_with_score(
        self, query: str, k: int = 3
    ) -> List[Tuple[Document, float]]:
        """
        유사도 점수와 함께 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수

        Returns:
            (문서, 유사도 점수) 튜플 리스트
        """
        return self.vector_store.similarity_search_with_score(query, k=k)

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        문서를 벡터 스토어에 추가합니다.

        Args:
            documents: 추가할 문서 리스트

        Returns:
            추가된 문서의 ID 리스트
        """
        return self.vector_store.add_documents(documents)

    def delete_by_ids(self, ids: List[str]) -> None:
        """
        ID로 문서를 삭제합니다.

        Args:
            ids: 삭제할 문서 ID 리스트
        """
        self.vector_store.delete(ids=ids)

