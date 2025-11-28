import sqlite3

conn = sqlite3.connect('instance/pharmadocs.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE users ADD COLUMN subscription_plan VARCHAR(50) DEFAULT "free" NOT NULL')
    print('Added subscription_plan')
except Exception as e:
    print(f'subscription_plan: {e}')

try:
    cursor.execute('ALTER TABLE users ADD COLUMN subscription_expiry DATETIME')
    print('Added subscription_expiry')
except Exception as e:
    print(f'subscription_expiry: {e}')

try:
    cursor.execute('ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255)')
    print('Added stripe_customer_id')
except Exception as e:
    print(f'stripe_customer_id: {e}')

try:
    cursor.execute('ALTER TABLE users ADD COLUMN razorpay_customer_id VARCHAR(255)')
    print('Added razorpay_customer_id')
except Exception as e:
    print(f'razorpay_customer_id: {e}')

try:
    cursor.execute('ALTER TABLE users ADD COLUMN subscription_status VARCHAR(50) DEFAULT "active" NOT NULL')
    print('Added subscription_status')
except Exception as e:
    print(f'subscription_status: {e}')

try:
    cursor.execute('ALTER TABLE users ADD COLUMN trial_ends_at DATETIME')
    print('Added trial_ends_at')
except Exception as e:
    print(f'trial_ends_at: {e}')

try:
    cursor.execute('ALTER TABLE users ADD COLUMN documents_limit INTEGER DEFAULT 5 NOT NULL')
    print('Added documents_limit')
except Exception as e:
    print(f'documents_limit: {e}')

conn.commit()
conn.close()
print('\nAll columns added successfully!')
