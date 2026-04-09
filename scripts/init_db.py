#!/usr/bin/env python3
"""
DB 초기화 스크립트

주체: Hub Router (Star)
역할: PostgreSQL 데이터베이스 초기화 (테이블 생성)

실행 방법:
    python scripts/init_db.py
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.database.connection import init_db, check_db_connection


def main():
    """DB 초기화 메인 함수"""
    print("=" * 70)
    print("PostgreSQL 데이터베이스 초기화")
    print("=" * 70)

    # 1. DB 연결 확인
    print("\n[1/3] DB 연결 확인 중...")

    if not check_db_connection():
        print("\n❌ DB 연결 실패!")
        print("\n확인 사항:")
        print("  1. PostgreSQL이 실행 중인지 확인하세요")
        print("  2. DATABASE_URL 환경 변수가 올바른지 확인하세요")
        print(f"     현재: {os.getenv('DATABASE_URL', '(없음)')}")
        print("  3. 데이터베이스가 생성되어 있는지 확인하세요")
        sys.exit(1)

    print("✅ DB 연결 성공!")

    # 2. 기존 테이블 확인
    print("\n[2/3] 기존 테이블 확인 중...")

    from app.database.connection import Base, engine
    from sqlalchemy import inspect

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        print(f"✅ 기존 테이블 발견: {len(existing_tables)}개")
        print(f"   테이블: {', '.join(existing_tables)}")
        print("\n📌 기존 테이블은 유지하고, 없는 테이블만 새로 생성합니다.")
    else:
        print("✅ 기존 테이블 없음 (새로 생성)")

    # 3. 테이블 생성 (기존 테이블은 건드리지 않음)
    print("\n[3/3] 테이블 생성 중...")

    try:
        # checkfirst=True가 기본값이므로, 이미 존재하는 테이블은 건너뜀
        init_db()

        # 생성 후 최종 테이블 목록 확인
        inspector = inspect(engine)
        final_tables = inspector.get_table_names()

        print("\n✅ 데이터베이스 초기화 완료!")
        print(f"\n현재 테이블: {len(final_tables)}개")
        for i, table in enumerate(sorted(final_tables), 1):
            print(f"  {i}. {table}")

        print("\n" + "=" * 70)

    except Exception as e:
        error_msg = str(e)

        # 인덱스/테이블 중복 에러는 경고만 표시 (치명적이지 않음)
        if "already exists" in error_msg or "DuplicateTable" in error_msg or "DuplicateObject" in error_msg:
            print(f"\n⚠️  일부 객체가 이미 존재합니다: {error_msg.split(':')[0]}")
            print("\n📌 기존 테이블 구조와 새 정의가 다를 수 있습니다.")
            print("\n옵션:")
            print("  1. 그대로 사용 (기존 테이블 유지)")
            print("  2. 테이블 구조 변경이 필요하면 수동 마이그레이션:")
            print("     - Alembic 사용 권장")
            print("     - 또는 기존 테이블 삭제 후 재생성")

            # 현재 테이블 상태 표시
            inspector = inspect(engine)
            final_tables = inspector.get_table_names()
            print(f"\n현재 테이블: {len(final_tables)}개")
            for i, table in enumerate(sorted(final_tables), 1):
                print(f"  {i}. {table}")
        else:
            # 다른 치명적 에러
            print(f"\n❌ 테이블 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
