"""add image table

Revision ID: 110a4d54db34
Revises: 778e0667ed67
Create Date: 2024-03-24 18:33:16.399601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '110a4d54db34'
down_revision: Union[str, None] = '778e0667ed67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('imageModel',
        sa.Column('id', sa.Integer(), nullable=True),
        sa.Column('image_object', sa.LargeBinary(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('text', sa.String(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['userModel.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    pass


def downgrade() -> None:
    op.drop_table('imageModel')
    pass
