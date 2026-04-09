"""
데이터베이스 시딩 스크립트

테스트용 초기 데이터를 데이터베이스에 삽입합니다.

실행:
- 기본(하드코딩 1건):  python database/seed_data.py
- 민사소송법 JSONL:   python database/seed_data.py --from-jsonl
  → data/raw/civil_procedure/problems/gy_saeryejip_all.jsonl
  → data/raw/civil_procedure/model_answers/gy_saeryejip_all.jsonl
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database.connection import DatabaseConnection
from app.core.database.session import SessionManager
import app.domain.v1.minso.models as ref_models
from app.core.config import Settings

# 민사소송법 JSONL 기본 경로
CIVIL_PROBLEMS_JSONL = project_root / "data" / "raw" / "civil_procedure" / "problems" / "gy_saeryejip_all.jsonl"
CIVIL_MODEL_ANSWERS_JSONL = project_root / "data" / "raw" / "civil_procedure" / "model_answers" / "gy_saeryejip_all.jsonl"


async def seed_reference_data():
    """Reference Domain 테스트 데이터 삽입"""

    print("\n" + "=" * 60)
    print("Reference Domain 데이터 시딩 시작")
    print("=" * 60)

    # .env 파일 로드
    Settings.load_from_env()

    # .env 로드 후 DATABASE_URL 다시 읽기 (클래스 변수는 모듈 로드 시점에 설정되므로)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL이 설정되지 않았습니다. .env 파일을 확인하세요.")

    db = DatabaseConnection.get_instance()
    db.connect(database_url)

    async with SessionManager() as session:
        # 1. 문제 생성
        problem = ref_models.Problem(
            id="prob-seed-001",
            title="대여금 청구 사건",
            content="""갑은 을에게 2023년 1월 1일 금 1,000만원을 대여하였고, 을은 2023년 6월 30일까지 이를 변제하기로 약정하였다.
그러나 변제기가 도과하였음에도 을이 변제하지 않자, 갑은 을을 상대로 대여금 청구의 소를 제기하고자 한다.
이 사건에서 문제되는 법률관계를 검토하시오.""",
            meta={
                "category": "민사소송법",
                "difficulty": "중",
                "keywords": ["대여금청구", "소비대차", "채무불이행"]
            }
        )
        session.add(problem)
        print(f"✅ 문제 생성: {problem.title}")

        # 2. 모범 답안 생성
        reference_answer = ref_models.ReferenceAnswer(
            id="ref-seed-001",
            problem_id=problem.id,
            content="""I. 서론
본 사안은 갑의 을에 대한 대여금 청구가 문제된다.

II. 청구권의 발생
1. 소비대차계약의 성립
갑과 을 사이에 금 1,000만원에 대한 소비대차계약이 체결되었다(민법 제598조). 금전의 교부와 변제 약정이 있었으므로 계약은 유효하게 성립하였다.

2. 변제기의 도과
변제기인 2023년 6월 30일이 경과하였으므로, 을은 변제기에 변제할 의무가 있었으나 이를 이행하지 않았다.

III. 청구권의 행사
1. 이행청구권
갑은 을에 대하여 금 1,000만원의 변제를 청구할 수 있다(민법 제603조).

2. 지연손해금
변제기 경과 후부터는 지연손해금을 청구할 수 있다(민법 제397조).

IV. 결론
따라서 갑은 을을 상대로 대여금 1,000만원 및 이에 대한 지연손해금의 지급을 구하는 소를 제기할 수 있다.""",
            structure={
                "outline": ["서론", "청구권의 발생", "청구권의 행사", "결론"],
                "main_issues": ["소비대차계약의 성립", "변제기의 도과", "이행청구권", "지연손해금"]
            }
        )
        session.add(reference_answer)
        print(f"✅ 모범 답안 생성: {reference_answer.id}")

        # 3. 쟁점 생성
        issues = [
            ref_models.Issue(
                id="issue-seed-001",
                reference_answer_id=reference_answer.id,
                issue_type="main",
                title="소비대차계약의 성립",
                description="갑과 을 사이에 금전소비대차계약이 유효하게 성립하였는지 검토",
                order=1,
                keywords=["소비대차", "계약성립", "금전대여"],
                related_cases=None
            ),
            ref_models.Issue(
                id="issue-seed-002",
                reference_answer_id=reference_answer.id,
                issue_type="main",
                title="변제기의 도과",
                description="변제기가 도과하여 채무불이행 상태에 있는지 검토",
                order=2,
                keywords=["변제기", "이행지체", "기한도과"],
                related_cases=None
            ),
            ref_models.Issue(
                id="issue-seed-003",
                reference_answer_id=reference_answer.id,
                issue_type="main",
                title="이행청구권",
                description="갑이 을에게 대여금 변제를 청구할 수 있는지 검토",
                order=3,
                keywords=["이행청구", "대여금반환청구권"],
                related_cases=None
            ),
            ref_models.Issue(
                id="issue-seed-004",
                reference_answer_id=reference_answer.id,
                issue_type="sub",
                title="지연손해금",
                description="변제기 경과 후 지연손해금을 청구할 수 있는지 검토",
                order=4,
                keywords=["지연손해금", "이행지체", "손해배상"],
                related_cases=None
            )
        ]

        for issue in issues:
            session.add(issue)
            print(f"✅ 쟁점 생성: {issue.title}")

        # 커밋
        await session.commit()
        print(f"\n✅ Reference Domain 시딩 완료!")
        print(f"  - 문제: 1개")
        print(f"  - 모범 답안: 1개")
        print(f"  - 쟁점: {len(issues)}개")

    await db.disconnect()


def _load_jsonl(path: Path):
    """JSONL 한 줄씩 로드. 없으면 빈 리스트."""
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


async def seed_from_civil_procedure_jsonl():
    """
    data/raw/civil_procedure/problems/gy_saeryejip_all.jsonl
    data/raw/civil_procedure/model_answers/gy_saeryejip_all.jsonl
    에서 문제·모범답안을 읽어 DB에 넣습니다. 이미 존재하는 id는 건너뜁니다.
    """
    print("\n" + "=" * 60)
    print("민사소송법 JSONL 시딩")
    print("=" * 60)

    Settings.load_from_env()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL이 설정되지 않았습니다.")

    problems_data = _load_jsonl(CIVIL_PROBLEMS_JSONL)
    answers_data = _load_jsonl(CIVIL_MODEL_ANSWERS_JSONL)

    if not problems_data:
        print(f"⚠ 문제 파일이 비어있거나 없음: {CIVIL_PROBLEMS_JSONL}")
        return
    # problem_id -> 모범답안 본문 (첫 번째 답안)
    ref_content_by_id = {}
    for row in answers_data:
        pid = row.get("id")
        answers = row.get("answers") or []
        if pid and answers:
            first = answers[0] if isinstance(answers[0], dict) else {}
            a = first.get("answer")
            if isinstance(a, str):
                ref_content_by_id[pid] = a

    db = DatabaseConnection.get_instance()
    db.connect(database_url)

    async with SessionManager() as session:
        from sqlalchemy import select

        existing_p = set()
        existing_r = set()
        try:
            rp = await session.execute(select(ref_models.Problem.id))
            existing_p = {r[0] for r in rp.fetchall()}
            rr = await session.execute(select(ref_models.ReferenceAnswer.id))
            existing_r = {r[0] for r in rr.fetchall()}
        except Exception:
            pass

        added_p, added_r = 0, 0
        for row in problems_data:
            pid = row.get("id")
            title = (row.get("title") or "")[:500]
            content = row.get("content") or ""
            if not pid or not content:
                continue
            if pid in existing_p:
                continue
            problem = ref_models.Problem(
                id=pid,
                title=title or pid,
                content=content,
                meta={"source": "gy_saeryejip_all.jsonl"},
            )
            session.add(problem)
            existing_p.add(pid)
            added_p += 1

            ref_content = ref_content_by_id.get(pid)
            if ref_content:
                ref_id = f"ref-{pid}"
                if ref_id not in existing_r:
                    ref_answer = ref_models.ReferenceAnswer(
                        id=ref_id,
                        problem_id=pid,
                        content=ref_content,
                        structure=None,
                    )
                    session.add(ref_answer)
                    existing_r.add(ref_id)
                    added_r += 1

        await session.commit()
        print(f"✅ 문제 {added_p}건, 모범답안 {added_r}건 추가 (기존 건너뜀)")
        print(f"   문제 파일: {CIVIL_PROBLEMS_JSONL}")
        print(f"   모범답안 파일: {CIVIL_MODEL_ANSWERS_JSONL}")

    await db.disconnect()


async def main():
    """메인 실행"""
    print("=" * 60)
    print("데이터베이스 시딩 스크립트")
    print("=" * 60)

    use_jsonl = "--from-jsonl" in sys.argv

    try:
        if use_jsonl:
            await seed_from_civil_procedure_jsonl()
        else:
            await seed_reference_data()

        print("\n" + "=" * 60)
        print("✅ 시딩 완료!")
        print("=" * 60)

        print("\n다음 단계:")
        print("  1. 서버 시작: uvicorn app.main:app --reload")
        print("  2. API 테스트: http://localhost:8000/api/v1/docs")
        print("  3. 데이터 확인: GET /api/v1/reference/problems")
        if not use_jsonl:
            print("\n  민사소송법 JSONL 시딩: python database/seed_data.py --from-jsonl")

    except Exception as e:
        print(f"\n❌ 시딩 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
