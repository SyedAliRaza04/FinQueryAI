import pandas as pd
from sqlalchemy import create_engine
from faker import Faker
import random

def main():
    db_path = "bank_customers.db"
    engine = create_engine(f'sqlite:///{db_path}')
    
    # 1. Read existing data
    print("Reading existing data...")
    df = pd.read_sql("SELECT * FROM customers", engine)
    print(f"Original shape: {df.shape}")
    
    # 2. Check for missing or 'unknown' values
    print("\nChecking for missing or 'unknown' values...")
    missing_counts = df.isnull().sum()
    unknown_counts = (df == 'unknown').sum()
    
    print("Missing values per column:\n", missing_counts[missing_counts > 0])
    print("\n'unknown' values per column:\n", unknown_counts[unknown_counts > 0])
    
    # 3. Populate synthetic data for missing/unknown entities
    # We will replace 'unknown' in categorical columns with realistic values based on distribution or random choice
    # For simplicity, we'll replace 'unknown' job, education, contact, poutcome with random valid choices from the existing data (excluding 'unknown')
    
    def replace_unknown(series):
        valid_values = series[series != 'unknown'].dropna().unique()
        if len(valid_values) == 0:
            return series # No valid values to sample from
        
        return series.apply(lambda x: random.choice(valid_values) if x == 'unknown' else x)

    columns_to_fix = ['job', 'education', 'contact', 'poutcome']
    for col in columns_to_fix:
        if col in df.columns:
            print(f"Fixing '{col}' column...")
            df[col] = replace_unknown(df[col])

    # 4. Add new necessary columns
    print("\nAdding new columns (Name, Account Number, Branch, etc.)...")
    fake = Faker()
    
    # Pre-generate data to speed up
    num_rows = len(df)
    
    # Generate Names
    print("Generating Names...")
    df['customer_name'] = [fake.name() for _ in range(num_rows)]
    
    # Generate Account Numbers (10 digits)
    print("Generating Account Numbers...")
    df['account_number'] = [fake.unique.random_number(digits=10, fix_len=True) for _ in range(num_rows)]
    
    # Generate Branch (let's assume a set of branches)
    branches = [fake.city() + " Branch" for _ in range(20)]
    print("Assigning Branches...")
    df['branch_name'] = [random.choice(branches) for _ in range(num_rows)]
    
    # Generate Customer ID (if not exists, though rowid exists in sqlite, explicit ID is good)
    print("Generating Customer IDs...")
    df['customer_id'] = [fake.unique.uuid4() for _ in range(num_rows)]
    
    # Generate Email
    print("Generating Emails...")
    df['email'] = [fake.email() for _ in range(num_rows)]
    
    # Generate Phone Number
    print("Generating Phone Numbers...")
    df['phone_number'] = [fake.phone_number() for _ in range(num_rows)]

    # 5. Save back to database
    print("\nSaving enriched data back to database...")
    df.to_sql('customers_enriched', engine, if_exists='replace', index=False)
    
    # Verify
    print("\nVerifying enriched data...")
    df_enriched = pd.read_sql("SELECT * FROM customers_enriched LIMIT 5", engine)
    print(df_enriched.head())
    print(f"\nEnriched dataset shape: {df.shape}")
    
    # Check if 'unknown' remains
    unknown_counts_new = (df == 'unknown').sum()
    print("\nRemaining 'unknown' values:\n", unknown_counts_new[unknown_counts_new > 0])

if __name__ == "__main__":
    main()
