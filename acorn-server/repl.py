"""
Payment RDBMS - Standalone REPL Mode
Run with: python repl.py

Interactive SQL console for testing the database engine without the web interface.
"""

import sys
import os

# Import the RDBMS from app.py
# This assumes app.py is in the same directory
try:
    from app import PaymentRDBMS
except ImportError:
    print("Error: Cannot import PaymentRDBMS from app.py")
    print("Make sure app.py is in the same directory")
    sys.exit(1)

def print_banner():
    """Print welcome banner"""
    print("=" * 70)
    print("                    Payment RDBMS - REPL Mode")
    print("=" * 70)
    print("Features:")
    print("  • B+ Tree Indexing for fast lookups")
    print("  • Write-Ahead Log (WAL) for durability")
    print("  • Snapshot-based recovery")
    print("  • SQL-like interface")
    print("=" * 70)
    print("\nCommands:")
    print("  CREATE TABLE <name> (<columns>)")
    print("  INSERT INTO <table> (<columns>) VALUES (<values>)")
    print("  SELECT <columns> FROM <table> [WHERE <condition>]")
    print("  UPDATE <table> SET <assignments> WHERE <condition>")
    print("  DELETE FROM <table> WHERE <condition>")
    print("  CREATE INDEX <name> ON <table>(<column>)")
    print("  SHOW TABLES")
    print("  DESCRIBE <table>")
    print("  .stats    - Show database statistics")
    print("  .snapshot - Create database snapshot")
    print("  .help     - Show this help")
    print("  .exit     - Exit REPL")
    print("=" * 70)
    print()

def print_table(result):
    """Pretty print query results as table"""
    if not result.get('rows'):
        print("(0 rows)")
        return
    
    rows = result['rows']
    columns = result.get('columns', list(rows[0].keys()) if rows else [])
    
    # Calculate column widths
    widths = {}
    for col in columns:
        widths[col] = len(str(col))
        for row in rows:
            widths[col] = max(widths[col], len(str(row.get(col, ''))))
    
    # Print header
    header = " | ".join(str(col).ljust(widths[col]) for col in columns)
    print(header)
    print("-" * len(header))
    
    # Print rows
    for row in rows:
        print(" | ".join(str(row.get(col, '')).ljust(widths[col]) for col in columns))
    
    print(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})")

def initialize_sample_data(db):
    """Initialize sample payment schema and data"""
    print("Initializing sample payment schema...")
    
    try:
        # Create tables
        db.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE,
                name TEXT,
                phone TEXT,
                balance DECIMAL,
                created_at TEXT
            )
        """)
        
        db.execute("""
            CREATE TABLE merchants (
                id INTEGER PRIMARY KEY,
                business_name TEXT,
                merchant_id TEXT UNIQUE,
                category TEXT,
                commission_rate DECIMAL,
                created_at TEXT
            )
        """)
        
        db.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY,
                transaction_id TEXT UNIQUE,
                customer_id INTEGER,
                merchant_id INTEGER,
                amount DECIMAL,
                currency TEXT,
                payment_method TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        
        # Create indexes
        db.execute("CREATE INDEX idx_customer_id ON transactions(customer_id)")
        db.execute("CREATE INDEX idx_merchant_id ON transactions(merchant_id)")
        db.execute("CREATE INDEX idx_status ON transactions(status)")
        
        # Insert sample data
        db.execute("INSERT INTO customers (email, name, phone, balance, created_at) VALUES ('alice@example.com', 'Alice Johnson', '+1234567890', 5000.00, '2025-01-10')")
        db.execute("INSERT INTO customers (email, name, phone, balance, created_at) VALUES ('bob@example.com', 'Bob Smith', '+1234567891', 3500.50, '2025-01-11')")
        
        db.execute("INSERT INTO merchants (business_name, merchant_id, category, commission_rate, created_at) VALUES ('Coffee Shop Inc', 'MERCH_001', 'Food & Beverage', 2.5, '2025-01-01')")
        db.execute("INSERT INTO merchants (business_name, merchant_id, category, commission_rate, created_at) VALUES ('Tech Store LLC', 'MERCH_002', 'Electronics', 3.0, '2025-01-02')")
        
        db.execute("INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) VALUES ('TXN_001', 1, 1, 45.50, 'USD', 'credit_card', 'completed', '2025-01-14 10:30:00')")
        db.execute("INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) VALUES ('TXN_002', 2, 2, 1299.99, 'USD', 'debit_card', 'completed', '2025-01-14 11:15:00')")
        
        print("✓ Sample data initialized successfully\n")
        
    except Exception as e:
        print(f"Note: {e}")
        print("(This is normal if database already exists)\n")

def show_stats(db):
    """Display database statistics"""
    stats = db.get_stats()
    print("\n" + "=" * 50)
    print("Database Statistics")
    print("=" * 50)
    print(f"Tables:      {stats['tables']}")
    print(f"B+ Indexes:  {stats['indexes']}")
    print(f"WAL Entries: {stats['wal_entries']}")
    print(f"Total Rows:  {stats['total_rows']}")
    print("=" * 50 + "\n")

def repl():
    """Main REPL loop"""
    print_banner()
    
    # Initialize database
    db = PaymentRDBMS()
    
    # Ask if user wants sample data
    if not db.tables:
        response = input("Initialize sample payment schema? (y/n): ").strip().lower()
        if response == 'y':
            initialize_sample_data(db)
    
    print("Ready. Enter SQL commands (or .help for commands).\n")
    
    while True:
        try:
            # Read input
            sql = input("payment_db> ").strip()
            
            if not sql:
                continue
            
            # Handle special commands
            if sql == '.exit' or sql == '.quit':
                print("Goodbye!")
                break
            
            elif sql == '.help':
                print_banner()
                continue
            
            elif sql == '.stats':
                show_stats(db)
                continue
            
            elif sql == '.snapshot':
                snapshot = db.create_snapshot()
                print(f"✓ Snapshot created: {snapshot.get('timestamp')}")
                print(f"  Saved to: {db.storage.snapshot_file}\n")
                continue
            
            elif sql == '.tables':
                result = db.execute("SHOW TABLES")
                if result['tables']:
                    print("Tables:")
                    for table in result['tables']:
                        print(f"  • {table}")
                else:
                    print("No tables found")
                print()
                continue
            
            # Execute SQL
            result = db.execute(sql)
            
            # Display results
            if result.get('success'):
                if 'rows' in result:
                    print_table(result)
                elif 'message' in result:
                    print(f"✓ {result['message']}")
                elif 'tables' in result:
                    print("Tables:")
                    for table in result['tables']:
                        print(f"  • {table}")
                elif 'columns' in result:
                    print("Columns:")
                    for col in result['columns']:
                        print(f"  • {col['name']:20} {col['type']:10} {'PRIMARY KEY' if col.get('is_primary') else ''} {'UNIQUE' if col.get('is_unique') else ''}")
                    if result.get('primary_key'):
                        print(f"\nPrimary Key: {result['primary_key']}")
                else:
                    print("✓ Query executed successfully")
                print()
            else:
                print(f"✗ Error: {result.get('error', 'Unknown error')}\n")
        
        except KeyboardInterrupt:
            print("\nUse .exit to quit")
            continue
        
        except EOFError:
            print("\nGoodbye!")
            break
        
        except Exception as e:
            print(f"✗ Error: {e}\n")

def main():
    """Entry point"""
    try:
        repl()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()