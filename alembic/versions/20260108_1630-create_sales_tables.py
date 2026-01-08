"""create sales tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-01-08 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sales tables"""

    # Create master_sales_products table
    op.create_table(
        'master_sales_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('product_name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('first_seen_date', sa.Date(), nullable=True),
        sa.Column('last_seen_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_name')
    )

    # Create indexes for master_sales_products
    op.create_index('ix_master_sales_products_product_name', 'master_sales_products', ['product_name'])
    op.create_index('ix_master_sales_products_category', 'master_sales_products', ['category'])
    op.create_index('ix_master_sales_products_is_active', 'master_sales_products', ['is_active'])

    # Create daily_sales table
    op.create_table(
        'daily_sales',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('sale_date', sa.Date(), nullable=False),
        sa.Column('product_name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('source', sa.String(), nullable=True, server_default=sa.text("'flowtide_qc'")),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sale_date', 'product_name', name='uq_daily_sales_date_product')
    )

    # Create indexes for daily_sales
    op.create_index('ix_daily_sales_sale_date', 'daily_sales', ['sale_date'])
    op.create_index('ix_daily_sales_product_name', 'daily_sales', ['product_name'])
    op.create_index('ix_daily_sales_category', 'daily_sales', ['category'])

    # Enable RLS (Row Level Security)
    op.execute('ALTER TABLE master_sales_products ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE daily_sales ENABLE ROW LEVEL SECURITY')

    # Create RLS policies
    op.execute('''
        CREATE POLICY "Allow all for service role" ON master_sales_products
        FOR ALL USING (true) WITH CHECK (true)
    ''')

    op.execute('''
        CREATE POLICY "Allow all for service role" ON daily_sales
        FOR ALL USING (true) WITH CHECK (true)
    ''')


def downgrade() -> None:
    """Drop sales tables"""

    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS "Allow all for service role" ON daily_sales')
    op.execute('DROP POLICY IF EXISTS "Allow all for service role" ON master_sales_products')

    # Drop daily_sales table and indexes
    op.drop_index('ix_daily_sales_category', table_name='daily_sales')
    op.drop_index('ix_daily_sales_product_name', table_name='daily_sales')
    op.drop_index('ix_daily_sales_sale_date', table_name='daily_sales')
    op.drop_table('daily_sales')

    # Drop master_sales_products table and indexes
    op.drop_index('ix_master_sales_products_is_active', table_name='master_sales_products')
    op.drop_index('ix_master_sales_products_category', table_name='master_sales_products')
    op.drop_index('ix_master_sales_products_product_name', table_name='master_sales_products')
    op.drop_table('master_sales_products')
