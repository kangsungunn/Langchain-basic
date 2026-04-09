#!/usr/bin/env python3
"""
DB 테이블 생성 문제 해결 스크립트

주체: Hub Router (Star)
역할: 충돌하는 인덱스/테이블 삭제 후 재생성

실행 방법:
    python scripts/fix_db_tables.py
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy import text
from app.database.connection import engine, SessionLocal


def drop_conflicting_objects():
    """충돌하는 인덱스/테이블 삭제"""
    print("=" * 70)
    print("충돌하는 DB 객체 삭제")
    print("=" * 70)

    db = SessionLocal()

    try:
        # 삭제할 인덱스 목록
        indexes_to_drop = [
            "ix_branch_results_branch_name",
            "ix_branch_results_task_type",
            "ix_branch_results_label",
            "ix_branch_results_created_at",
            "ix_input_texts_created_at",
            "ix_routing_logs_created_at",
            "ix_policy_decisions_created_at",
        ]

        # 삭제할 테이블 목록
        tables_to_drop = [
            "branch_results",
            "input_texts",
            "routing_logs",
            "policy_decisions",
        ]

        print("\n[1/2] 인덱스 삭제 중...")
        for index_name in indexes_to_drop:
            try:
                db.execute(text(f"DROP INDEX IF EXISTS {index_name} CASCADE;"))
                print(f"  ✅ {index_name}")
            except Exception as e:
                print(f"  ⚠️  {index_name}: {e}")

        db.commit()

        print("\n[2/2] 테이블 삭제 중...")
        for table_name in tables_to_drop:
            try:
                db.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
                print(f"  ✅ {table_name}")
            except Exception as e:
                print(f"  ⚠️  {table_name}: {e}")

        db.commit()

        print("\n✅ 충돌하는 객체 삭제 완료!")

    except Exception as e:
        print(f"\n❌ 삭제 실패: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


def recreate_tables():
    """테이블 재생성"""
    print("\n" + "=" * 70)
    print("테이블 재생성")
    print("=" * 70)

    from app.database.connection import init_db

    try:
        init_db()
        print("\n✅ 테이블 재생성 완료!")
    except Exception as e:
        print(f"\n❌ 재생성 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def verify_tables():
    """테이블 생성 확인"""
    print("\n" + "=" * 70)
    print("테이블 생성 확인")
    print("=" * 70)

    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    required_tables = [
        "input_texts",
        "routing_logs",
        "branch_results",
        "policy_decisions"
    ]

    print(f"\n생성된 테이블: {len(tables)}개")
    for table in sorted(tables):
        status = "✅" if table in required_tables else "ℹ️"
        print(f"  {status} {table}")

    missing = [t for t in required_tables if t not in tables]
    if missing:
        print(f"\n⚠️  누락된 테이블: {missing}")
        return False
    else:
        print("\n✅ 모든 필수 테이블 생성 완료!")
        return True


def main():
    """메인 함수"""
    print("\n" + "=" * 70)
    print("DB 테이블 생성 문제 해결")
    print("=" * 70)

    # 1. 충돌하는 객체 삭제
    drop_conflicting_objects()

    # 2. 테이블 재생성
    recreate_tables()

    # 3. 확인
    success = verify_tables()

    if success:
        print("\n" + "=" * 70)
        print("✅ 모든 작업 완료!")
        print("=" * 70)
        print("\n다음 단계:")
        print("  1. DB 저장 테스트: Swagger에서 save_to_db=true로 요청")
        print("  2. DB 데이터 확인: Neon DB 콘솔에서 쿼리 실행")
    else:
        print("\n" + "=" * 70)
        print("⚠️  일부 테이블이 생성되지 않았습니다.")
        print("=" * 70)
        print("\n수동으로 확인하세요:")
        print("  1. Neon DB 콘솔 접속")
        print("  2. 충돌하는 객체 수동 삭제")
        print("  3. python scripts/init_db.py 재실행")


if __name__ == "__main__":
    main()
