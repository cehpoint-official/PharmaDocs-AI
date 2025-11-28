from app import app, db
from sqlalchemy import text, inspect

def check_database_status():
    """Check if database schema matches models"""
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("=" * 70)
        print("DATABASE SCHEMA CHECK")
        print("=" * 70)
        
        # Check pvp_template table
        print("\n📋 Checking pvp_template table...")
        
        if 'pvp_template' in inspector.get_table_names():
            print("✅ Table 'pvp_template' exists")
            
            # Get all columns
            columns = inspector.get_columns('pvp_template')
            
            print(f"\n📊 Found {len(columns)} columns:")
            print("-" * 70)
            
            for col in columns:
                col_type = str(col['type'])
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                print(f"  {col['name']:30} {col_type:20} {nullable}")
            
            # Check for company columns specifically
            print("\n🔍 Checking for company columns:")
            print("-" * 70)
            
            required_company_cols = [
                'company_name',
                'company_address', 
                'company_city',
                'company_state',
                'company_country',
                'company_pincode'
            ]
            
            existing_cols = [col['name'] for col in columns]
            
            all_exist = True
            for req_col in required_company_cols:
                if req_col in existing_cols:
                    print(f"  ✅ {req_col}")
                else:
                    print(f"  ❌ {req_col} - MISSING!")
                    all_exist = False
            
            if all_exist:
                print("\n🎉 All company columns exist! Database is ready.")
                return True
            else:
                print("\n⚠️  Some company columns are missing!")
                return False
                
        else:
            print("❌ Table 'pvp_template' does NOT exist!")
            return False

if __name__ == "__main__":
    status = check_database_status()
    
    if not status:
        print("\n" + "=" * 70)
        print("❌ DATABASE NOT READY - Run add_columns.py to fix")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✅ DATABASE IS READY - You can upload PVP files now!")
        print("=" * 70)