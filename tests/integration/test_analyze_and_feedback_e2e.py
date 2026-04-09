"""
E2E: analyze-and-feedback 한 번에 플로우 (Phase 1~4 검증)

전제:
- 백엔드 서버 기동 (localhost:8000)
- DB에 문제 1개 이상, 해당 문제에 모범답안 1개 이상 존재 (없으면 시딩: database/seed_data.py)

실행:
- pytest:  python -m pytest tests/integration/test_analyze_and_feedback_e2e.py -v -s
- 스크립트: python tests/integration/test_analyze_and_feedback_e2e.py
"""

import os
import sys
from pathlib import Path

import httpx

# 프로젝트 루트
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000/api/v1")
TIMEOUT = 60.0
# 추론+피드백+임베딩은 모델 로드/추론으로 오래 걸릴 수 있음
ANALYZE_FEEDBACK_TIMEOUT = float(os.getenv("TEST_ANALYZE_FEEDBACK_TIMEOUT", "300"))


def _get_problem_and_reference(client: httpx.Client):
    """문제 목록 → 첫 문제의 모범답안 1개 반환. 없으면 (None, None)."""
    r = client.get(f"{BASE_URL}/reference/problems", timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    items = data.get("items") or []
    if not items:
        return None, None
    problem = items[0]
    problem_id = problem["id"]

    r2 = client.get(f"{BASE_URL}/reference/problems/{problem_id}/answers", timeout=TIMEOUT)
    r2.raise_for_status()
    raw = r2.json()
    refs = raw if isinstance(raw, list) else (raw.get("items") or [])
    if not refs:
        return problem, None
    return problem, refs[0]


def _create_submission(client: httpx.Client, problem_id: str, content: str):
    """텍스트 답안 제출, 생성된 답안 ID 반환."""
    r = client.post(
        f"{BASE_URL}/submission/answers/text",
        json={"problem_id": problem_id, "content": content},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["id"]


def test_analyze_and_feedback_e2e():
    """
    제출답안 생성 → analyze-and-feedback 호출 → 200 + 응답 구조 검증.
    ExaOne 없어도 200 + analysis_summary, feedback 있으면 성공.
    """
    with httpx.Client(timeout=TIMEOUT) as client:
        # 1) 문제·모범답안 확보
        problem, ref = _get_problem_and_reference(client)
        if not problem or not ref:
            raise RuntimeError(
                "문제 또는 모범답안이 없습니다. database/seed_data.py 를 실행한 뒤 다시 시도하세요."
            )
        problem_id = problem["id"]

        # 2) 제출답안 생성
        content = "갑은 을에 대하여 대여금 채권을 가지고 있으므로, 변제기를 도과한 을에게 변제를 청구할 수 있다."
        user_answer_id = _create_submission(client, problem_id, content)

        # 3) analyze-and-feedback 호출 (추론·피드백·임베딩으로 시간 소요 가능)
        r = client.post(
            f"{BASE_URL}/submission/answers/{user_answer_id}/analyze-and-feedback",
            timeout=ANALYZE_FEEDBACK_TIMEOUT,
        )

        assert r.status_code == 200, (
            f"analyze-and-feedback 실패: {r.status_code}, body={r.text}"
        )
        data = r.json()

        # 4) 필수 필드 검증
        assert "user_answer_id" in data, "user_answer_id 없음"
        assert data["user_answer_id"] == user_answer_id
        assert "reasoning_task_id" in data, "reasoning_task_id 없음"
        assert "analysis_summary" in data, "analysis_summary 없음"
        assert "feedback" in data, "feedback 없음"

        summary = data["analysis_summary"]
        assert isinstance(summary, dict), "analysis_summary는 dict"
        # Phase 1~4: 기존 점수 필드(폴백 시에도 있음)
        assert "issue_coverage" in summary or "exaone_analysis" in summary or len(summary) >= 1, (
            "analysis_summary에 issue_coverage 또는 exaone_analysis 등이 있어야 함"
        )

        feedback = data["feedback"]
        assert "id" in feedback, "feedback.id 없음"
        assert "summary" in feedback or "overall_score" in feedback or "meta" in feedback, (
            "feedback에 summary/overall_score/meta 중 하나 이상 있어야 함"
        )

        # ExaOne 있을 때만 있을 수 있는 필드 (선택 검증)
        if "exaone_analysis" in summary:
            assert isinstance(summary["exaone_analysis"], str), "exaone_analysis는 문자열"
        if isinstance(feedback.get("meta"), dict) and "exaone_analysis" in feedback["meta"]:
            assert isinstance(feedback["meta"]["exaone_analysis"], str)


def run_as_script():
    """스크립트로 실행 시 (python tests/integration/test_analyze_and_feedback_e2e.py)"""
    try:
        test_analyze_and_feedback_e2e()
        print("OK E2E: analyze-and-feedback 통과")
    except Exception as e:
        print(f"FAIL: {e}")
        raise


if __name__ == "__main__":
    run_as_script()
