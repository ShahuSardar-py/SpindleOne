"""Add alert_threshold to raw_material

Revision ID: a6361bbacf2e
Revises: 5acdf0880cfb
Create Date: 2026-03-06 10:43:09.326129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a6361bbacf2e'
down_revision = '5acdf0880cfb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('raw_material', schema=None) as batch_op:
        batch_op.add_column(sa.Column('alert_threshold', sa.Float(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('raw_material', schema=None) as batch_op:
        batch_op.drop_column('alert_threshold')

    # ### end Alembic commands ###
