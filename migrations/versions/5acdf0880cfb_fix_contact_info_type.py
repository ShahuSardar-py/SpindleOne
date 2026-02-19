"""fix contact_info type

Revision ID: 5acdf0880cfb
Revises: 756c34bf27be
Create Date: 2026-02-19 20:53:36.563190

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5acdf0880cfb'
down_revision = '756c34bf27be'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column('contact_info',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=250),
               existing_nullable=True)

def downgrade():
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column('contact_info',
               existing_type=sa.String(length=250),
               type_=sa.INTEGER(),
               existing_nullable=True)
