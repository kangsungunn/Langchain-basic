"""
Repository 베이스 클래스

데이터 접근의 추상 인터페이스를 정의합니다.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple

from langchain_core.documents import Document


class BaseVectorRepository(ABC):
    """벡터 스토어 Repository의 추상 인터페이스"""

    @abstractmethod
    def search(self, query: str, k: int = 3) -> List[Document]:
        """
        유사도 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수

        Returns:
            관련 문서 리스트
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        문서를 벡터 스토어에 추가합니다.

        Args:
            documents: 추가할 문서 리스트

        Returns:
            추가된 문서의 ID 리스트
        """
        pass

    @abstractmethod
    def delete_by_ids(self, ids: List[str]) -> None:
        """
        ID로 문서를 삭제합니다.

        Args:
            ids: 삭제할 문서 ID 리스트
        """
        pass

