from app import app, db
from sqlalchemy import text

def add_company_columns():
    """Add company columns directly to database"""
    
    sql = """
    ALTER TABLE pvp_template 
    ADD COLUMN IF NOT EXISTS company_name VARCHAR(300),
    ADD COLUMN IF NOT EXISTS company_address VARCHAR(500),
    ADD COLUMN IF NOT EXISTS company_city VARCHAR(100),
    ADD COLUMN IF NOT EXISTS company_state VARCHAR(100),
    ADD COLUMN IF NOT EXISTS company_country VARCHAR(100),
    ADD COLUMN IF NOT EXISTS company_pincode VARCHAR(20);
    """
    
    with app.app_context():
        try:
            db.session.execute(text(sql))
            db.session.commit()
            print("✅ Successfully added company columns to pvp_template!")
            
            # Verify
            verify_sql = """
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'pvp_template' AND column_name LIKE 'company%'
            ORDER BY column_name;
            """
            result = db.session.execute(text(verify_sql))
            print("\n📋 Company columns in pvp_template:")
            for row in result:
                print(f"  ✓ {row[0]}: {row[1]}({row[2]})")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_company_columns()