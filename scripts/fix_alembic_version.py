"""
DB의 alembic_version을 유효한 리비전으로 한 번에 수정합니다.
'Can't locate revision identified by ...' 오류 시 사용하세요.

사용법 (프로젝트 루트에서):
  python scripts/fix_alembic_version.py
  python scripts/fix_alembic_version.py a1e0c566a622   # 특정 리비전으로 지정
  python scripts/fix_alembic_version.py base          # 버전 삭제 → 처음부터 upgrade 가능

기본값: a637b9e3a950 (embedding 마이그레이션 직전)
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

def main():
    target_revision = (sys.argv[1] if len(sys.argv) > 1 else "a637b9e3a950").strip().lower()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)
    # psycopg2 expects postgresql:// (no +asyncpg or +psycopg2)
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg2://"):
        if database_url.startswith(prefix):
            database_url = "postgresql://" + database_url[len(prefix):]
            break

    import psycopg2

    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()

    if target_revision in ("base", "reset", ""):
        cur.execute("DELETE FROM alembic_version")
        print("Cleared alembic_version. Run: alembic upgrade head  (applies all migrations from scratch)")
        cur.close()
        conn.close()
        return

    cur.execute("SELECT version_num FROM alembic_version")
    row = cur.fetchone()
    if row:
        old = row[0]
        cur.execute("UPDATE alembic_version SET version_num = %s", (target_revision,))
        print(f"Updated alembic_version: {old} -> {target_revision}")
    else:
        cur.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", (target_revision,))
        print(f"Inserted alembic_version: {target_revision}")
    cur.close()
    conn.close()
    print("Done. Run: alembic upgrade head")

if __name__ == "__main__":
    main()
