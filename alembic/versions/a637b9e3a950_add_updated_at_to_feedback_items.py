"""add_updated_at_to_feedback_items

Revision ID: a637b9e3a950
Revises: 550c0fbdd8ea
Create Date: 2026-01-27 18:40:04.019501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a637b9e3a950'
down_revision: Union[str, Sequence[str], None] = '550c0fbdd8ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # feedback_items 테이블에 updated_at 컬럼 추가
    op.add_column(
        'feedback_items',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 기존 레코드의 updated_at을 created_at과 동일하게 설정
    op.execute("""
        UPDATE feedback_items
        SET updated_at = created_at
        WHERE updated_at IS NULL
    """)

    # NOT NULL 제약 조건 추가
    op.alter_column('feedback_items', 'updated_at', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # feedback_items 테이블에서 updated_at 컬럼 제거
    op.drop_column('feedback_items', 'updated_at')
