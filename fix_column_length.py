import psycopg2

# Database connection details
conn = psycopg2.connect(
    dbname="your_database_name",
    user="your_username",
    password="your_password",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# SQL command to alter column length
try:
    cursor.execute("ALTER TABLE pvp_template ALTER COLUMN company_address TYPE VARCHAR(500);")
    conn.commit()
    print("Column length updated successfully!")
except Exception as e:
    print(f"Error: {e}")
finally:
    cursor.close()
    conn.close()