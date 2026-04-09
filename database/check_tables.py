"""
NeonDB 연결 및 테이블 확인 스크립트
"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# .env 파일 로드
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] Loaded .env file: {env_path}")
else:
    print(f"[ERROR] .env file not found: {env_path}")
    sys.exit(1)

# DATABASE_URL 가져오기
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("[ERROR] DATABASE_URL not found in environment")
    sys.exit(1)

print(f"\n{'='*60}")
print("NeonDB 연결 및 테이블 확인")
print('='*60)

# asyncpg용 URL로 변환 (확인용)
if "postgresql+psycopg2://" in database_url:
    check_url = database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
elif "postgresql://" in database_url:
    check_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
else:
    check_url = database_url

# 쿼리 파라미터 제거 (asyncpg는 지원하지 않음)
from urllib.parse import urlparse, urlunparse
parsed = urlparse(check_url)
clean_url = urlunparse((
    parsed.scheme,
    parsed.netloc,
    parsed.path,
    parsed.params,
    '',  # 모든 쿼리 파라미터 제거
    parsed.fragment
))

# SSL 설정
connect_args = {}
if "sslmode=require" in database_url or "sslmode=prefer" in database_url:
    connect_args['ssl'] = True

print(f"\n[1] 데이터베이스 연결 테스트")
print(f"    URL: {parsed.scheme}://{parsed.netloc}{parsed.path}")

async def check_database():
    """데이터베이스 연결 및 테이블 확인"""
    try:
        # 엔진 생성
        engine = create_async_engine(
            clean_url,
            connect_args=connect_args if connect_args else None,
            echo=False
        )

        print(f"    [OK] 엔진 생성 완료")

        # 연결 테스트
        async with engine.connect() as conn:
            print(f"    [OK] 데이터베이스 연결 성공!")

            # 현재 데이터베이스 이름 확인
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"    [OK] 현재 데이터베이스: {db_name}")

            # 테이블 목록 조회
            print(f"\n[2] 테이블 목록 확인")
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()

            if tables:
                print(f"    [OK] 총 {len(tables)}개의 테이블 발견:")
                for table in tables:
                    print(f"        - {table[0]}")
            else:
                print(f"    [WARNING] 테이블이 없습니다!")

            # alembic_version 테이블 확인
            print(f"\n[3] 마이그레이션 상태 확인")
            result = await conn.execute(text("""
                SELECT version_num
                FROM alembic_version
                LIMIT 1
            """))
            version = result.scalar_one_or_none()

            if version:
                print(f"    [OK] 현재 마이그레이션 버전: {version}")
            else:
                print(f"    [WARNING] alembic_version 테이블이 없습니다!")

            # 예상되는 테이블 목록
            expected_tables = [
                'problems',
                'reference_answers',
                'issues',
                'user_answers',
                'answer_structures',
                'reasoning_tasks',
                'reasoning_results',
                'feedbacks',
                'feedback_items',
                'alembic_version'
            ]

            print(f"\n[4] 예상 테이블 vs 실제 테이블 비교")
            actual_table_names = [t[0] for t in tables]
            missing_tables = [t for t in expected_tables if t not in actual_table_names]

            if missing_tables:
                print(f"    [WARNING] 누락된 테이블 ({len(missing_tables)}개):")
                for table in missing_tables:
                    print(f"        - {table}")
            else:
                print(f"    [OK] 모든 예상 테이블이 존재합니다!")

            # problems 테이블 데이터 확인
            print(f"\n[5] 시딩 데이터 확인")
            result = await conn.execute(text("SELECT COUNT(*) FROM problems"))
            problem_count = result.scalar()
            print(f"    problems 테이블 레코드 수: {problem_count}")

            if problem_count > 0:
                result = await conn.execute(text("SELECT id, title FROM problems LIMIT 5"))
                problems = result.fetchall()
                print(f"    [OK] 시딩 데이터 확인:")
                for prob in problems:
                    print(f"        - {prob[0]}: {prob[1][:30]}...")
            else:
                print(f"    [WARNING] problems 테이블에 데이터가 없습니다!")

        await engine.dispose()
        print(f"\n{'='*60}")
        print("[OK] 확인 완료!")
        print('='*60)

    except Exception as e:
        print(f"\n[ERROR] 데이터베이스 확인 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_database())
