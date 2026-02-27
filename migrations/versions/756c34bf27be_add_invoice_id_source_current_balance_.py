from alembic import op
import sqlalchemy as sa

revision = '756c34bf27be'
down_revision = 'a10086e19b3c'
branch_labels = None
depends_on = None

def upgrade():
    # The initial migration already created current_balance and source, so only
    # add the missing invoice_id column.  We'll also wire up the foreign key
    # here to keep related changes together.
    with op.batch_alter_table('AccountCashflow', schema=None) as batch_op:
        batch_op.add_column(sa.Column('invoice_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_accountcashflow_invoice',
            'Invoice',
            ['invoice_id'],
            ['inv_id'],
        )

def downgrade():
    with op.batch_alter_table('AccountCashflow', schema=None) as batch_op:
        batch_op.drop_column('current_balance')
        batch_op.drop_column('source')
        batch_op.drop_column('invoice_id')