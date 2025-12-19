"""
RAG 서비스

RAG(Retrieval-Augmented Generation) 로직을 처리하는 서비스입니다.

😎😎 rag_service.py 서빙 관련 서비스

사용자의 질문을 받아:

벡터 검색,

LLM 호출,

응답 후처리까지 담당.

rag_chain.py를 실제로 호출하는 “애플리케이션 서비스”.

"""

from typing import List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.models.base import BaseEmbeddings, BaseLLM
from app.repository.base import BaseVectorRepository


class RAGService:
    """RAG 서비스 클래스"""

    def __init__(
        self,
        llm: BaseLLM,
        embeddings: BaseEmbeddings,
        repository: BaseVectorRepository,
        similarity_threshold: float = 0.5,
    ):
        """
        RAG 서비스를 초기화합니다.

        Args:
            llm: LLM 모델 제공자
            embeddings: Embeddings 모델 제공자
            repository: 벡터 스토어 Repository
            similarity_threshold: 유사도 임계값
        """
        self.llm = llm
        self.embeddings = embeddings
        self.repository = repository
        self.similarity_threshold = similarity_threshold

    def create_rag_prompt(self) -> ChatPromptTemplate:
        """RAG용 프롬프트 템플릿을 생성합니다."""
        template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content="다음 문서 내용을 바탕으로 질문에 답하세요."),
                (
                    "human",
                    """참고 문서:
{context}

{question}""",
                ),
            ]
        )
        return template

    def clean_answer(self, answer) -> str:
        """답변에서 불필요한 메타 정보를 제거합니다."""
        # 먼저 문자열로 변환
        if not isinstance(answer, str):
            answer = str(answer)

        # 제거할 패턴들 (더 많이 추가)
        patterns = [
            "System:",
            "시스템:",
            "Human:",
            "Answer:",
            "답변:",
            "질문:",
            "질문에 자연스럽게 답변하세요.",
            "질문에 답변하세요.",
            "다음 문서 내용을 바탕으로 질문에 답하세요.",
            "참고 문서:",
            "H:",
            "A:",
        ]

        result = answer.strip()

        # 프롬프트 텍스트가 포함된 경우 제거
        prompt_indicators = [
            "질문에 자연스럽게 답변하세요",
            "질문에 답변하세요",
            "다음 문서 내용을 바탕으로",
        ]

        # 프롬프트가 답변에 포함되어 있으면, 실제 답변 부분만 추출
        for indicator in prompt_indicators:
            if indicator in result:
                parts = result.split(indicator, 1)
                if len(parts) > 1:
                    result = parts[1].strip()

        # 각 줄에서 패턴을 찾아서 제거 (라인은 유지)
        lines = result.split("\n")
        cleaned_lines = []

        for line in lines:
            cleaned_line = line.strip()

            # 완전히 패턴으로만 이루어진 라인은 건너뛰기
            skip_line = False
            for pattern in patterns:
                if cleaned_line == pattern.rstrip(":").rstrip("?").rstrip("."):
                    skip_line = True
                    break

            if skip_line:
                continue

            # 라인 시작 부분의 패턴만 제거
            for pattern in patterns:
                if cleaned_line.startswith(pattern):
                    cleaned_line = cleaned_line[len(pattern) :].strip()
                    break

            # 빈 줄이 아니면 추가
            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        result = "\n".join(cleaned_lines)

        return result

    def search_relevant_documents(
        self, query: str, k: int = 3
    ) -> List[Tuple[Document, float]]:
        """
        관련 문서를 검색합니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수

        Returns:
            (문서, 유사도 점수) 튜플 리스트
        """
        docs_with_scores = self.repository.search_with_score(query, k=k)
        relevant_docs = [
            (doc, score)
            for doc, score in docs_with_scores
            if score <= self.similarity_threshold
        ]
        return relevant_docs

    def generate_answer(self, question: str, context: Optional[str] = None) -> str:
        """
        답변을 생성합니다.

        Args:
            question: 사용자 질문
            context: 컨텍스트 (None이면 일반 대화)

        Returns:
            생성된 답변
        """
        if context:
            # RAG 모드
            prompt_template = self.create_rag_prompt()
            prompt = prompt_template.format_messages(context=context, question=question)
        else:
            # 일반 대화 모드
            general_prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content="질문에 자연스럽게 답변하세요."),
                    ("human", "{question}"),
                ]
            )
            prompt = general_prompt.format_messages(question=question)

        chat_model = self.llm.get_model()
        response = chat_model.invoke(prompt)

        # content가 str이 아닐 수 있으므로 안전하게 처리
        if isinstance(response.content, str):
            answer = response.content
        else:
            answer = str(response.content)

        # 불필요한 메타 정보 제거
        answer = self.clean_answer(answer)

        return answer
