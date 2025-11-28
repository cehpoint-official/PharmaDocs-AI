from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'fix_company_address_length_explicit'
down_revision = 'fix_company_address_length'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('pvp_template', 'company_address', type_=sa.String(length=500), existing_type=sa.String(length=32))

def downgrade():
    op.alter_column('pvp_template', 'company_address', type_=sa.String(length=32), existing_type=sa.String(length=500))