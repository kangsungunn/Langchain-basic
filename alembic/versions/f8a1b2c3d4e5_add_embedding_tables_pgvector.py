"""Add embedding tables (pgvector)

Revision ID: f8a1b2c3d4e5
Revises: a637b9e3a950
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'f8a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'a637b9e3a950'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: enable pgvector extension and create embedding tables."""
    # 1. Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. feedback_embeddings
    op.create_table(
        'feedback_embeddings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자'),
        sa.Column('feedback_id', sa.String(length=36), nullable=False, comment='피드백 ID'),
        sa.Column('content', sa.Text(), nullable=False, comment='임베딩 생성에 사용된 원본 텍스트'),
        sa.Column('embedding', Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoELECTRA)'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False, comment='레코드 생성 시간'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['feedback_id'], ['feedbacks.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_feedback_embeddings_feedback_id'), 'feedback_embeddings', ['feedback_id'], unique=False)

    # 3. reference_answer_embeddings
    op.create_table(
        'reference_answer_embeddings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자'),
        sa.Column('reference_answer_id', sa.String(length=36), nullable=False, comment='모범답안 ID'),
        sa.Column('content', sa.Text(), nullable=False, comment='임베딩 생성에 사용된 원본 텍스트'),
        sa.Column('embedding', Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoELECTRA)'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False, comment='레코드 생성 시간'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['reference_answer_id'], ['reference_answers.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_reference_answer_embeddings_reference_answer_id'), 'reference_answer_embeddings', ['reference_answer_id'], unique=False)

    # 4. user_answer_embeddings
    op.create_table(
        'user_answer_embeddings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자'),
        sa.Column('user_answer_id', sa.String(length=36), nullable=False, comment='사용자 답안 ID'),
        sa.Column('content', sa.Text(), nullable=False, comment='임베딩 생성에 사용된 원본 텍스트'),
        sa.Column('embedding', Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoELECTRA)'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False, comment='레코드 생성 시간'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_answer_id'], ['user_answers.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_user_answer_embeddings_user_answer_id'), 'user_answer_embeddings', ['user_answer_id'], unique=False)

    # 5. reasoning_task_embeddings
    op.create_table(
        'reasoning_task_embeddings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자'),
        sa.Column('reasoning_task_id', sa.String(length=36), nullable=False, comment='추론 작업 ID'),
        sa.Column('content', sa.Text(), nullable=False, comment='임베딩 생성에 사용된 원본 텍스트'),
        sa.Column('embedding', Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoELECTRA)'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False, comment='레코드 생성 시간'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['reasoning_task_id'], ['reasoning_tasks.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_reasoning_task_embeddings_reasoning_task_id'), 'reasoning_task_embeddings', ['reasoning_task_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop embedding tables."""
    op.drop_index(op.f('ix_reasoning_task_embeddings_reasoning_task_id'), table_name='reasoning_task_embeddings')
    op.drop_table('reasoning_task_embeddings')

    op.drop_index(op.f('ix_user_answer_embeddings_user_answer_id'), table_name='user_answer_embeddings')
    op.drop_table('user_answer_embeddings')

    op.drop_index(op.f('ix_reference_answer_embeddings_reference_answer_id'), table_name='reference_answer_embeddings')
    op.drop_table('reference_answer_embeddings')

    op.drop_index(op.f('ix_feedback_embeddings_feedback_id'), table_name='feedback_embeddings')
    op.drop_table('feedback_embeddings')

    # Optionally drop extension (comment out if other DB objects use it)
    # op.execute("DROP EXTENSION IF EXISTS vector")
