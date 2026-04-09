"""add feedback_corrections table (user feedback on feedback, for learning)

Revision ID: b9c8d7e6f5a4
Revises: f8a1b2c3d4e5
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b9c8d7e6f5a4'
down_revision: Union[str, Sequence[str], None] = 'f8a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE feedbackcorrectiontype AS ENUM ('correction', 'addition'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.create_table(
        'feedback_corrections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('feedback_id', sa.String(length=36), nullable=False),
        sa.Column(
            'correction_type',
            postgresql.ENUM('correction', 'addition', name='feedbackcorrectiontype', create_type=False),
            nullable=False,
        ),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['feedback_id'], ['feedbacks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feedback_corrections_feedback_id'), 'feedback_corrections', ['feedback_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_feedback_corrections_feedback_id'), table_name='feedback_corrections')
    op.drop_table('feedback_corrections')
    op.execute('DROP TYPE IF EXISTS feedbackcorrectiontype')
