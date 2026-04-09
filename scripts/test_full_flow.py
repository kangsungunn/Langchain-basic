"""
전체 플로우 테스트 스크립트

답안 제출 → 구조 분석 → 추론 분석 → 피드백 생성의 전체 플로우를 테스트합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from app.core.config import Settings

# .env 파일 로드
Settings.load_from_env()

# API 기본 URL
BASE_URL = "http://localhost:8000/api/v1"


async def test_full_flow():
    """전체 플로우 테스트"""

    print("=" * 80)
    print("전체 플로우 테스트 시작")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=60.0) as client:

        # ============================================================
        # Step 1: 문제 조회 (시딩된 데이터 확인)
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 1: 문제 조회")
        print("=" * 80)

        try:
            response = await client.get(f"{BASE_URL}/reference/problems")
            response.raise_for_status()
            problems_data = response.json()

            if not problems_data.get("items"):
                print("❌ 문제가 없습니다. 시딩을 먼저 실행하세요:")
                print("   python database/seed_data.py")
                return

            problem = problems_data["items"][0]
            problem_id = problem["id"]

            print(f"✅ 문제 조회 성공:")
            print(f"   - ID: {problem_id}")
            print(f"   - 제목: {problem['title']}")

            # 모범 답안 조회
            response = await client.get(f"{BASE_URL}/reference/problems/{problem_id}/answers")
            response.raise_for_status()
            reference_answers = response.json()

            if not reference_answers:
                print("❌ 모범 답안이 없습니다.")
                return

            reference_answer = reference_answers[0]
            reference_answer_id = reference_answer["id"]

            print(f"   - 모범 답안 ID: {reference_answer_id}")

        except Exception as e:
            print(f"❌ Step 1 실패: {e}")
            return

        # ============================================================
        # Step 2: 답안 제출
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 2: 답안 제출")
        print("=" * 80)

        user_answer_content = """I. 서론
본 사안은 갑의 을에 대한 대여금 청구가 문제된다.

II. 소비대차계약의 성립
갑과 을 사이에 금전소비대차계약이 체결되었다. 금전의 교부와 변제 약정이 있었으므로 계약은 유효하게 성립하였다.

III. 변제기의 도과
변제기인 2023년 6월 30일이 경과하였으므로, 을은 변제기에 변제할 의무가 있었으나 이를 이행하지 않았다.

IV. 청구권의 행사
갑은 을에 대하여 금 1,000만원의 변제를 청구할 수 있다. 변제기 경과 후부터는 지연손해금을 청구할 수 있다.

V. 결론
따라서 갑은 을을 상대로 대여금 1,000만원 및 이에 대한 지연손해금의 지급을 구하는 소를 제기할 수 있다."""

        try:
            response = await client.post(
                f"{BASE_URL}/submission/answers/text",
                json={
                    "problem_id": problem_id,
                    "content": user_answer_content
                }
            )
            response.raise_for_status()
            user_answer = response.json()
            user_answer_id = user_answer["id"]

            print(f"✅ 답안 제출 성공:")
            print(f"   - 답안 ID: {user_answer_id}")
            print(f"   - 상태: {user_answer['status']}")
            print(f"   - 내용 길이: {len(user_answer_content)}자")

        except Exception as e:
            print(f"❌ Step 2 실패: {e}")
            if hasattr(e, 'response'):
                print(f"   응답: {e.response.text}")
            return

        # ============================================================
        # Step 3: 구조 분석
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 3: 구조 분석")
        print("=" * 80)

        try:
            response = await client.post(
                f"{BASE_URL}/submission/answers/{user_answer_id}/analyze"
            )
            response.raise_for_status()
            structure = response.json()

            print(f"✅ 구조 분석 완료:")
            print(f"   - 문단 수: {structure.get('paragraph_count', {}).get('total', 0)}")
            print(f"   - 문장 수: {structure.get('sentence_count', {}).get('total', 0)}")
            print(f"   - 단어 수: {structure.get('word_count', {}).get('total', 0)}")

        except Exception as e:
            print(f"❌ Step 3 실패: {e}")
            if hasattr(e, 'response'):
                print(f"   응답: {e.response.text}")
            return

        # ============================================================
        # Step 4: 추론 분석 (쟁점 분석)
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 4: 추론 분석 - 쟁점 분석")
        print("=" * 80)

        try:
            response = await client.post(
                f"{BASE_URL}/reasoning/analyze/issues",
                json={
                    "user_answer_id": user_answer_id,
                    "reference_answer_id": reference_answer_id,
                    "problem_id": problem_id
                }
            )
            response.raise_for_status()
            issue_analysis = response.json()

            print(f"✅ 쟁점 분석 완료:")
            print(f"   - 작업 ID: {issue_analysis.get('task_id')}")
            print(f"   - 상태: {issue_analysis.get('status')}")

            if "result" in issue_analysis:
                result = issue_analysis["result"]
                print(f"   - 쟁점 포함률: {result.get('issue_coverage', 'N/A')}")
                print(f"   - 식별된 쟁점: {len(result.get('identified_issues', []))}개")
                print(f"   - 누락된 쟁점: {len(result.get('missing_issues', []))}개")

        except Exception as e:
            print(f"❌ Step 4 실패: {e}")
            if hasattr(e, 'response'):
                try:
                    error_detail = e.response.json()
                    print(f"   응답: {error_detail}")
                except:
                    print(f"   응답: {e.response.text}")
            import traceback
            traceback.print_exc()
            return

        # ============================================================
        # Step 5: 추론 분석 (논리 평가)
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 5: 추론 분석 - 논리 평가")
        print("=" * 80)

        try:
            response = await client.post(
                f"{BASE_URL}/reasoning/analyze/logic",
                json={
                    "user_answer_id": user_answer_id,
                    "reference_answer_id": reference_answer_id,
                    "problem_id": problem_id
                }
            )
            response.raise_for_status()
            logic_analysis = response.json()

            print(f"✅ 논리 평가 완료:")
            print(f"   - 작업 ID: {logic_analysis.get('task_id')}")

            if "result" in logic_analysis:
                result = logic_analysis["result"]
                print(f"   - 논리 점수: {result.get('logic_score', 'N/A')}")
                print(f"   - 논리 문제: {len(result.get('logic_issues', []))}개")

        except Exception as e:
            print(f"❌ Step 5 실패: {e}")
            if hasattr(e, 'response'):
                print(f"   응답: {e.response.text}")
            return

        # ============================================================
        # Step 6: 추론 분석 (표현 검토)
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 6: 추론 분석 - 표현 검토")
        print("=" * 80)

        try:
            response = await client.post(
                f"{BASE_URL}/reasoning/analyze/expression",
                json={
                    "user_answer_id": user_answer_id,
                    "reference_answer_id": reference_answer_id,
                    "problem_id": problem_id
                }
            )
            response.raise_for_status()
            expression_analysis = response.json()

            print(f"✅ 표현 검토 완료:")
            print(f"   - 작업 ID: {expression_analysis.get('task_id')}")

            if "result" in expression_analysis:
                result = expression_analysis["result"]
                print(f"   - 표현 점수: {result.get('expression_score', 'N/A')}")
                print(f"   - 표현 문제: {len(result.get('expression_issues', []))}개")

        except Exception as e:
            print(f"❌ Step 6 실패: {e}")
            if hasattr(e, 'response'):
                print(f"   응답: {e.response.text}")
            return

        # ============================================================
        # Step 7: 종합 분석
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 7: 종합 분석")
        print("=" * 80)

        try:
            response = await client.post(
                f"{BASE_URL}/reasoning/analyze/comprehensive",
                json={
                    "user_answer_id": user_answer_id,
                    "reference_answer_id": reference_answer_id,
                    "problem_id": problem_id
                }
            )
            response.raise_for_status()
            comprehensive_analysis = response.json()

            print(f"✅ 종합 분석 완료:")
            print(f"   - 작업 ID: {comprehensive_analysis.get('task_id')}")
            print(f"   - 상태: {comprehensive_analysis.get('status')}")

        except Exception as e:
            print(f"❌ Step 7 실패: {e}")
            if hasattr(e, 'response'):
                print(f"   응답: {e.response.text}")
            return

        # ============================================================
        # Step 8: 피드백 생성
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 8: 피드백 생성")
        print("=" * 80)

        try:
            # 먼저 추론 작업 목록 조회
            response = await client.get(f"{BASE_URL}/reasoning/answers/{user_answer_id}/tasks")
            response.raise_for_status()
            tasks_data = response.json()

            # API 응답은 {"total": int, "items": List[...]} 형식
            tasks = tasks_data.get("items", [])

            if not tasks:
                print("⚠️  추론 작업이 없습니다. 피드백 생성을 건너뜁니다.")
            else:
                # 가장 최근 작업 사용
                latest_task = tasks[-1]
                task_id = latest_task["id"]

                response = await client.post(
                    f"{BASE_URL}/feedback/generate",
                    json={
                        "user_answer_id": user_answer_id,
                        "reasoning_task_id": task_id,
                        "feedback_type": "comprehensive"
                    }
                )
                response.raise_for_status()
                feedback = response.json()

                print(f"✅ 피드백 생성 완료:")
                print(f"   - 피드백 ID: {feedback.get('id')}")
                print(f"   - 타입: {feedback.get('feedback_type')}")
                print(f"   - 종합 점수: {feedback.get('overall_score', 'N/A')}")

                if feedback.get('summary'):
                    print(f"   - 요약: {feedback['summary'][:100]}...")

                if feedback.get('strengths'):
                    print(f"   - 강점: {len(feedback['strengths'])}개")

                if feedback.get('weaknesses'):
                    print(f"   - 약점: {len(feedback['weaknesses'])}개")

        except Exception as e:
            print(f"❌ Step 8 실패: {e}")
            if hasattr(e, 'response'):
                try:
                    error_detail = e.response.json()
                    print(f"   응답: {error_detail}")
                except:
                    print(f"   응답: {e.response.text}")
            import traceback
            traceback.print_exc()
            return

        # ============================================================
        # Step 9: 최종 결과 확인
        # ============================================================
        print("\n" + "=" * 80)
        print("Step 9: 최종 결과 확인")
        print("=" * 80)

        try:
            # 답안 조회
            response = await client.get(f"{BASE_URL}/submission/answers/{user_answer_id}")
            response.raise_for_status()
            final_answer = response.json()

            # 추론 작업 목록
            response = await client.get(f"{BASE_URL}/reasoning/answers/{user_answer_id}/tasks")
            response.raise_for_status()
            final_tasks = response.json()

            # 피드백 목록
            response = await client.get(f"{BASE_URL}/feedback/answers/{user_answer_id}/feedbacks")
            response.raise_for_status()
            final_feedbacks = response.json()

            print(f"✅ 최종 상태:")
            print(f"   - 답안 상태: {final_answer.get('status')}")
            print(f"   - 추론 작업 수: {len(final_tasks)}개")
            print(f"   - 피드백 수: {len(final_feedbacks.get('items', []))}개")

        except Exception as e:
            print(f"⚠️  Step 9 확인 실패: {e}")

        # ============================================================
        # 완료
        # ============================================================
        print("\n" + "=" * 80)
        print("✅ 전체 플로우 테스트 완료!")
        print("=" * 80)

        print("\n📊 생성된 데이터:")
        print(f"   - 답안 ID: {user_answer_id}")
        print(f"   - 문제 ID: {problem_id}")
        print(f"   - 모범 답안 ID: {reference_answer_id}")

        print("\n🔍 확인 방법:")
        print(f"   1. API 문서: http://localhost:8000/api/v1/docs")
        print(f"   2. 답안 조회: GET /api/v1/submission/answers/{user_answer_id}")
        print(f"   3. 피드백 조회: GET /api/v1/feedback/answers/{user_answer_id}/feedbacks")
        print(f"   4. NeonDB 콘솔에서 직접 확인")


async def main():
    """메인 실행"""
    try:
        # 서버 연결 테스트는 첫 번째 API 호출로 확인
        await test_full_flow()

    except KeyboardInterrupt:
        print("\n\n⚠️  테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
