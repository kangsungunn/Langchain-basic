"""add_updated_at_to_reasoning_results

Revision ID: 550c0fbdd8ea
Revises: deaccc34e525
Create Date: 2026-01-27 15:42:37.128242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '550c0fbdd8ea'
down_revision: Union[str, Sequence[str], None] = 'deaccc34e525'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # reasoning_results 테이블에 updated_at 컬럼 추가
    op.add_column(
        'reasoning_results',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 기존 레코드의 updated_at을 created_at과 동일하게 설정
    op.execute("""
        UPDATE reasoning_results
        SET updated_at = created_at
        WHERE updated_at IS NULL
    """)

    # NOT NULL 제약 조건 추가
    op.alter_column('reasoning_results', 'updated_at', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # reasoning_results 테이블에서 updated_at 컬럼 제거
    op.drop_column('reasoning_results', 'updated_at')
