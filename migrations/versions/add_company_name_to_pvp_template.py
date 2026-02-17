from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'add_company_name_to_pvp_template'
down_revision = '6f343ba85986'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('pvp_template', sa.Column('company_name', sa.String(length=300), nullable=True))

def downgrade():
    op.drop_column('pvp_template', 'company_name')