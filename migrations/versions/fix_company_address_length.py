from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'fix_company_address_length'
down_revision = 'add_company_address_to_pvp_template'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('pvp_template', 'company_address', type_=sa.String(length=500))

def downgrade():
    op.alter_column('pvp_template', 'company_address', type_=sa.String(length=32))