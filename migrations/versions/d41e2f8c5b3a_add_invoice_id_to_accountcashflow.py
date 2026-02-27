"""Add invoice_id column to AccountCashflow table

This migration adds the missing invoice_id column to the AccountCashflow table
to fix the issue where the dashboard fails with:
sqlalchemy.exc.OperationalError: no such column: AccountCashflow.invoice_id

This migration is designed to be idempotent - it can be run multiple times safely.

Revision ID: d41e2f8c5b3a
Revises: ab328ab7aa51
Create Date: 2026-02-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd41e2f8c5b3a'
down_revision = '756c34bf27be'
branch_labels = None
depends_on = None


def upgrade():
    # First, check if the column already exists to make this migration idempotent
    # Get the table info using reflection
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('AccountCashflow')]
    
    if 'invoice_id' not in columns:
        # Add the invoice_id column
        with op.batch_alter_table('AccountCashflow', schema=None) as batch_op:
            batch_op.add_column(sa.Column('invoice_id', sa.Integer(), nullable=True))
    
    # Check if the foreign key exists before creating it
    foreign_keys = inspector.get_foreign_keys('AccountCashflow')
    fk_names = [fk.get('name') for fk in foreign_keys]
    
    if 'fk_accountcashflow_invoice' not in fk_names:
        # Create the foreign key constraint
        op.create_foreign_key(
            'fk_accountcashflow_invoice',
            'AccountCashflow',
            'Invoice',
            ['invoice_id'],
            ['inv_id'],
        )


def downgrade():
    # Drop the foreign key first
    op.drop_constraint('fk_accountcashflow_invoice', 'AccountCashflow', type_='foreignkey')
    # Then drop the column
    with op.batch_alter_table('AccountCashflow', schema=None) as batch_op:
        batch_op.drop_column('invoice_id')

