"""
테스트 데이터 팩토리

테스트 및 개발 환경에서 사용할 더미 데이터 생성 유틸리티

주의: 실제 프로덕션 코드에서는 사용자가 명시적으로 데이터를 제공해야 합니다.
이 유틸리티는 테스트 및 개발 환경에서만 사용됩니다.
"""

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.spokes.services.submission_service import UserAnswerService
from app.domain.v1.minso.models.transfers import UserAnswerCreateText, ProblemCreate, ReferenceAnswerCreate
from app.domain.v1.minso.spokes.services.reference_service import ProblemService, ReferenceAnswerService


async def create_test_data_for_analysis(
    session: AsyncSession,
    problem_title: Optional[str] = None,
    problem_content: Optional[str] = None,
    reference_content: Optional[str] = None,
    user_answer_content: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    분석을 위한 테스트 데이터 생성

    실제 데이터 기준으로 작성된 코드를 사용하여 더미 데이터를 생성합니다.
    테스트 및 개발 환경에서 사용됩니다.

    Args:
        session: 데이터베이스 세션
        problem_title: 문제 제목 (기본값: "민사소송법 소송요건")
        problem_content: 문제 내용 (기본값: "민사소송법에서 소송요건의 의미를 설명하시오.")
        reference_content: 모범답안 내용 (기본값: 기본 모범답안)
        user_answer_content: 사용자 답안 내용 (기본값: 기본 사용자 답안)

    Returns:
        tuple: (user_answer_id, reference_answer_id, problem_id)

    Raises:
        ValueError: 데이터 생성 실패 시
    """
    # 기본값 설정
    if problem_title is None:
        problem_title = "민사소송법 소송요건"

    if problem_content is None:
        problem_content = "민사소송법에서 소송요건의 의미를 설명하시오."

    if reference_content is None:
        reference_content = (
            "소송요건은 소송을 제기하기 위해 필요한 요건으로, 소송요건이 충족되지 않으면 소송이 각하됩니다. "
            "주요 소송요건으로는 관할권, 당사자능력, 소송능력 등이 있습니다."
        )

    if user_answer_content is None:
        user_answer_content = (
            "소송요건은 소송을 제기하기 위한 조건입니다. 소송요건이 없으면 소송이 각하됩니다."
        )

    try:
        # 1. Problem 생성 (실제 데이터 기준 코드 사용)
        # Repository를 직접 사용하여 relationship 로딩 문제 회피
        from app.domain.v1.minso.models import Problem
        from app.domain.v1.minso.hub.repositories import ProblemRepository
        import uuid

        problem_repo = ProblemRepository(session)
        problem = Problem(
            id=str(uuid.uuid4()),
            title=problem_title,
            content=problem_content,
            meta={"subject": "민사소송법", "topic": "소송요건"}
        )
        created_problem = await problem_repo.create(problem)
        problem_id = created_problem.id

        # 2. Reference Answer 생성 (실제 데이터 기준 코드 사용)
        from app.domain.v1.minso.models import ReferenceAnswer
        from app.domain.v1.minso.hub.repositories import ReferenceAnswerRepository

        reference_repo = ReferenceAnswerRepository(session)
        reference_answer = ReferenceAnswer(
            id=str(uuid.uuid4()),
            problem_id=problem_id,
            content=reference_content,
            structure=None
        )
        created_reference = await reference_repo.create(reference_answer)
        reference_answer_id = created_reference.id

        # 3. User Answer 생성 (실제 데이터 기준 코드 사용)
        # UserAnswerService는 이미 안전하게 구현되어 있음
        user_answer_service = UserAnswerService(session)
        user_answer_data = UserAnswerCreateText(
            problem_id=problem_id,
            content=user_answer_content
        )
        user_answer = await user_answer_service.create_text_answer(user_answer_data)
        user_answer_id = user_answer.id

        return user_answer_id, reference_answer_id, problem_id

    except Exception as e:
        raise ValueError(f"테스트 데이터 생성 실패: {e}") from e


async def create_test_training_data(
    session: AsyncSession,
    problem_text: Optional[str] = None,
    reference_answer_text: Optional[str] = None,
    user_answer_text: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    학습 데이터 생성을 위한 테스트 데이터 생성

    실제 데이터 기준으로 작성된 코드를 사용하여 더미 데이터를 생성합니다.
    테스트 및 개발 환경에서 사용됩니다.

    Args:
        session: 데이터베이스 세션
        problem_text: 문제 텍스트
        reference_answer_text: 모범답안 텍스트
        user_answer_text: 사용자 답안 텍스트

    Returns:
        tuple: (user_answer_id, reference_answer_id, problem_id)

    Raises:
        ValueError: 데이터 생성 실패 시
    """
    # 기본값 설정
    if problem_text is None:
        problem_text = "민사소송법에서 소송요건의 의미를 설명하시오."

    if reference_answer_text is None:
        reference_answer_text = (
            "소송요건은 소송을 제기하기 위해 필요한 요건으로, 소송요건이 충족되지 않으면 소송이 각하됩니다. "
            "주요 소송요건으로는 관할권, 당사자능력, 소송능력 등이 있습니다."
        )

    if user_answer_text is None:
        user_answer_text = (
            "소송요건은 소송을 제기하기 위한 조건입니다. 소송요건이 없으면 소송이 각하됩니다."
        )

    # Problem 생성 (Repository 직접 사용하여 relationship 로딩 문제 회피)
    from app.domain.v1.minso.models import Problem, ReferenceAnswer
    from app.domain.v1.minso.hub.repositories import ProblemRepository, ReferenceAnswerRepository
    import uuid

    problem_repo = ProblemRepository(session)
    problem = Problem(
        id=str(uuid.uuid4()),
        title="테스트 문제",
        content=problem_text,
        meta={"test": True}
    )
    created_problem = await problem_repo.create(problem)
    problem_id = created_problem.id

    # Reference Answer 생성
    reference_repo = ReferenceAnswerRepository(session)
    reference_answer = ReferenceAnswer(
        id=str(uuid.uuid4()),
        problem_id=problem_id,
        content=reference_answer_text,
        structure=None
    )
    created_reference = await reference_repo.create(reference_answer)
    reference_answer_id = created_reference.id

    # User Answer 생성 (UserAnswerService는 이미 안전하게 구현되어 있음)
    user_answer_service = UserAnswerService(session)
    user_answer_data = UserAnswerCreateText(
        problem_id=problem_id,
        content=user_answer_text
    )
    user_answer = await user_answer_service.create_text_answer(user_answer_data)
    user_answer_id = user_answer.id

    return user_answer_id, reference_answer_id, problem_id
