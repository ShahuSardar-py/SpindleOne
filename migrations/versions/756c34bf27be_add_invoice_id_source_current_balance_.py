from alembic import op
import sqlalchemy as sa

revision = '756c34bf27be'
down_revision = 'a10086e19b3c'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('AccountCashflow', schema=None) as batch_op:
        batch_op.add_column(sa.Column('invoice_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('current_balance', sa.Float(), nullable=False, server_default='0'))

def downgrade():
    with op.batch_alter_table('AccountCashflow', schema=None) as batch_op:
        batch_op.drop_column('current_balance')
        batch_op.drop_column('source')
        batch_op.drop_column('invoice_id')