"""Add file_path to telegram_message

Revision ID: 0001
Revises: 
Create Date: 2025-01-17 07:17:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add file_path column to telegram_message table
    op.add_column('telegrammessage', sa.Column('file_path', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove file_path column from telegram_message table
    op.drop_column('telegrammessage', 'file_path')

