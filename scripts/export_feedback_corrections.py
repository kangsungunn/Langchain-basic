"""
피드백 정정(학습용) 데이터를 JSONL로 내보내기

사용자가 첨삭 결과에 남긴 "정정" / "추가·강조" 의견을 DB에서 읽어 JSONL로 저장합니다.
나중에 SFT나 RAG로 피드백 품질 개선에 활용할 수 있습니다.

사용 예:
  # .env에 DATABASE_URL 설정 후
  python scripts/export_feedback_corrections.py
  python scripts/export_feedback_corrections.py --out data/feedback_corrections.jsonl
  python scripts/export_feedback_corrections.py --format sft --out training/data/feedback_corrections_sft.jsonl
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# .env 로드 (app.main과 동일)
def load_env():
    from dotenv import load_dotenv
    env_path = ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 로드: {env_path}")


async def run(database_url: str, out_path: Path, export_format: str):
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.domain.v1.minso.models.bases.feedback import FeedbackCorrection, Feedback

    # async 엔진 (export 시에는 sync URL이 올 수 있음)
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql+asyncpg://"):
        pass
    else:
        print("지원: PostgreSQL (DATABASE_URL)")
        return

    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        # feedback_corrections 테이블 존재 여부 확인
        r = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'feedback_corrections')"
        ))
        if not r.scalar():
            print("테이블 feedback_corrections 이 없습니다. 마이그레이션을 실행하세요: alembic upgrade head")
            return

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    corrections_data = []

    async with Session() as session:
        # FeedbackCorrection 목록 + 해당 Feedback 요약
        q = (
            select(FeedbackCorrection, Feedback.summary, Feedback.strengths, Feedback.weaknesses)
            .join(Feedback, Feedback.id == FeedbackCorrection.feedback_id)
            .order_by(FeedbackCorrection.created_at.desc())
        )
        result = await session.execute(q)
        rows = result.all()

    for row in rows:
        correction, summary, strengths, weaknesses = row
        rec = {
            "id": correction.id,
            "feedback_id": correction.feedback_id,
            "correction_type": correction.correction_type.value if hasattr(correction.correction_type, "value") else str(correction.correction_type),
            "content": correction.content,
            "created_at": correction.created_at.isoformat() if correction.created_at else None,
            "feedback_summary": summary,
            "feedback_strengths": strengths,
            "feedback_weaknesses": weaknesses,
        }
        corrections_data.append(rec)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if export_format == "sft":
        # SFT용: instruction / input / output 형태 (나중에 모델이 "사용자 의견 반영 피드백"을 생성하도록 학습할 때 사용)
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in corrections_data:
                original = f"요약: {rec.get('feedback_summary') or ''}\n강점: {rec.get('feedback_strengths') or []}\n개선점: {rec.get('feedback_weaknesses') or []}"
                if rec["correction_type"] == "correction":
                    inst = "다음 첨삭 결과에서 사용자가 지적한 대로 수정하라."
                else:
                    inst = "다음 첨삭 결과에 사용자가 요청한 내용을 반영하라."
                sft = {
                    "instruction": inst,
                    "input": f"원래 피드백:\n{original}",
                    "output": rec["content"],
                    "correction_type": rec["correction_type"],
                }
                f.write(json.dumps(sft, ensure_ascii=False) + "\n")
        print(f"✅ SFT 형식으로 {len(corrections_data)}건 저장: {out_path}")
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in corrections_data:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"✅ {len(corrections_data)}건 저장: {out_path}")

    await engine.dispose()


def main():
    load_env()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL이 설정되지 않았습니다. .env를 확인하세요.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Export feedback corrections to JSONL")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "feedback_corrections.jsonl", help="출력 JSONL 경로")
    parser.add_argument("--format", choices=["raw", "sft"], default="raw", help="raw: 원본 필드 | sft: instruction/input/output")
    args = parser.parse_args()

    asyncio.run(run(database_url, args.out, args.format))


if __name__ == "__main__":
    main()
