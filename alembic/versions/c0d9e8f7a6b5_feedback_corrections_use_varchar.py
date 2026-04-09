"""feedback_corrections.correction_type: enum -> varchar (PostgreSQL enum 대소문자 이슈 방지)

Revision ID: c0d9e8f7a6b5
Revises: b9c8d7e6f5a4
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c0d9e8f7a6b5'
down_revision: Union[str, Sequence[str], None] = 'b9c8d7e6f5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE feedback_corrections
        ALTER COLUMN correction_type TYPE VARCHAR(20)
        USING correction_type::text
    """)
    op.execute('DROP TYPE IF EXISTS feedbackcorrectiontype')


def downgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE feedbackcorrectiontype AS ENUM ('correction', 'addition'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute("""
        ALTER TABLE feedback_corrections
        ALTER COLUMN correction_type TYPE feedbackcorrectiontype
        USING correction_type::feedbackcorrectiontype
    """)

