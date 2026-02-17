from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'add_company_address_to_pvp_template'
down_revision = 'add_company_name_to_pvp_template'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('pvp_template', sa.Column('company_address', sa.String(length=500), nullable=True))

def downgrade():
    op.drop_column('pvp_template', 'company_address')