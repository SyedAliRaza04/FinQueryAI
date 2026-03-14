from sqlalchemy import create_engine, text

def main():
    db_path = "bank_customers.db"
    engine = create_engine(f'sqlite:///{db_path}')
    
    with engine.connect() as connection:
        # 1. Drop the old 'customers' table
        print("Dropping 'customers' table...")
        try:
            connection.execute(text("DROP TABLE IF EXISTS customers"))
            print("'customers' table dropped.")
        except Exception as e:
            print(f"Error dropping table: {e}")

        # 2. Rename 'customers_enriched' to 'customers'
        print("Renaming 'customers_enriched' to 'customers'...")
        try:
            connection.execute(text("ALTER TABLE customers_enriched RENAME TO customers"))
            print("Table renamed successfully.")
        except Exception as e:
            print(f"Error renaming table: {e}")

        # 3. Verify
        print("Verifying tables...")
        result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print("Current tables:", tables)

if __name__ == "__main__":
    main()
