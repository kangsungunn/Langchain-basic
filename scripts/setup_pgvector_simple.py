# -*- coding: utf-8 -*-
"""Neon PostgreSQL pgvector 설정"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# UTF-8 출력 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

def main():
    print("="*60)
    print("Neon PostgreSQL - pgvector 설정")
    print("="*60)

    # 연결 정보
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    dbname = os.getenv("POSTGRES_DB")

    print(f"호스트: {host}")
    print(f"데이터베이스: {dbname}")
    print()

    try:
        # Neon 연결
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            sslmode='require'
        )
        conn.autocommit = True
        cursor = conn.cursor()

        print("[1/3] pgvector 확장 활성화 중...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("OK! pgvector 확장이 활성화되었습니다.")
        print()

        print("[2/3] 테이블 확인 중...")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name LIKE 'langchain%';
        """)
        tables = cursor.fetchall()

        if tables:
            print("기존 LangChain 테이블:")
            for table in tables:
                print(f"  - {table[0]}")

            # 데이터 개수 확인
            try:
                cursor.execute("SELECT COUNT(*) FROM langchain_pg_embedding;")
                count = cursor.fetchone()[0]
                print(f"\n저장된 임베딩: {count}개")
            except:
                print("\n(임베딩 테이블이 아직 생성되지 않았습니다)")
        else:
            print("LangChain 테이블이 아직 없습니다.")
            print("(백엔드 첫 실행 시 자동 생성됩니다)")
        print()

        print("[3/3] 완료!")
        print("="*60)
        print()
        print("다음 단계:")
        print("1. start_backend.bat  - 백엔드 시작")
        print("2. start_frontend.bat - 프론트엔드 시작")
        print("또는")
        print("start_all.bat - 모두 시작")
        print()

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"오류: {e}")
        print()
        print(".env 파일의 DB 설정을 확인하세요.")
        return False

if __name__ == "__main__":
    main()

