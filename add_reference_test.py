from database import db
from app import app
from models import User, ReferenceProduct

app.app_context().push()

# Find your user
user = User.query.filter_by(email='pujithagedela1217@gmail.com').first()
print(f'Your user_id: {user.id}')

# Check existing reference products
refs = ReferenceProduct.query.filter_by(company_id=user.id).all()
print(f'Reference products for your company: {len(refs)}')

if len(refs) == 0:
    # Add test reference product
    ref = ReferenceProduct(
        company_id=user.id,
        standard_type='USP Reference',
        standard_name='Paracetamol Reference Standard',
        code='REF-PAR-001',
        potency='99.8%',
        due_date='2026-12-31'
    )
    db.session.add(ref)
    db.session.commit()
    print('✓ Added reference product for your company')
else:
    print('Existing reference products:')
    for r in refs:
        print(f'  - {r.standard_name} ({r.code})')
