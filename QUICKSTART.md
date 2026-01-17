# Quick Start Guide

Get the Payment RDBMS running in 5 minutes!

## Option 1: REPL Only (Fastest)

Perfect for testing the database engine without the web interface.

```bash
# 1. Install Python dependencies
pip install flask flask-cors

# 2. Run the REPL
python repl.py
```

You'll see:
```
======================================================================
                    Payment RDBMS - REPL Mode
======================================================================
Features:
  • B+ Tree Indexing for fast lookups
  • Write-Ahead Log (WAL) for durability
  • Snapshot-based recovery
  • SQL-like interface
======================================================================

Initialize sample payment schema? (y/n): y
✓ Sample data initialized successfully

Ready. Enter SQL commands (or .help for commands).

payment_db>
```

### Try These Commands:

```sql
-- Show all tables
.tables

-- View customers
SELECT * FROM customers

-- Complex JOIN query
SELECT 
  customers.name, 
  transactions.amount, 
  merchants.business_name 
FROM transactions 
JOIN customers ON transactions.customer_id = customers.id 
JOIN merchants ON transactions.merchant_id = merchants.id

-- Add a transaction
INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) 
VALUES ('TXN_003', 1, 2, 199.99, 'USD', 'credit_card', 'pending', '2025-01-15 14:30:00')

-- Update status
UPDATE transactions SET status = 'completed' WHERE transaction_id = 'TXN_003'

-- Check database stats
.stats

-- Create snapshot
.snapshot

-- Exit
.exit
```

## Option 2: Full Stack (Web UI)

Run both backend API and React frontend.

### Backend:

```bash
# Terminal 1: Start backend
pip install -r requirements.txt
python app.py
```

You'll see:
```
============================================================
Payment RDBMS Server
============================================================
Features:
  ✓ B+ Tree Indexing
  ✓ Write-Ahead Log (WAL)
  ✓ Snapshot/Recovery
  ✓ SQL-like Interface
  ✓ CRUD Operations
  ✓ JOIN Support
============================================================

Starting server on http://localhost:5000
```

### Frontend:

```bash
# Terminal 2: Setup React (first time only)
npx create-react-app acorn-client
cd acorn-client
npm install lucide-react

# Copy the React component from artifacts to src/App.js

# Start frontend
npm start
```

Browser opens at `http://localhost:3000` 

##  What You'll See

### REPL Mode:
- Interactive SQL console
- Pretty-printed table results
- Database statistics
- Snapshot creation

### Web UI:
- **Transactions Tab**: Add/view payment transactions
- **Customers Tab**: View customer profiles
- **Merchants Tab**: View merchant information
- **SQL REPL Tab**: Execute custom queries in browser
- **Stats Dashboard**: Live database metrics

## Test Scenarios

### 1. Basic CRUD
```sql
-- Create
INSERT INTO customers (email, name, phone, balance, created_at) 
VALUES ('charlie@example.com', 'Charlie Brown', '+1234567892', 2000.00, '2025-01-15')

-- Read
SELECT * FROM customers WHERE email = 'charlie@example.com'

-- Update
UPDATE customers SET balance = 2500.00 WHERE email = 'charlie@example.com'

-- Delete
DELETE FROM customers WHERE email = 'charlie@example.com'
```

### 2. JOIN Query
```sql
SELECT 
  transactions.transaction_id,
  customers.name AS customer,
  merchants.business_name AS merchant,
  transactions.amount,
  transactions.status
FROM transactions
JOIN customers ON transactions.customer_id = customers.id
JOIN merchants ON transactions.merchant_id = merchants.id
WHERE transactions.status = 'completed'
```

### 3. Index Usage
```sql
-- This uses B+ tree index on customer_id (fast!)
SELECT * FROM transactions WHERE customer_id = 1

-- This uses B+ tree index on status (fast!)
SELECT * FROM transactions WHERE status = 'pending'

-- Without index, would do table scan (slower)
SELECT * FROM transactions WHERE amount = 45.50
```

### 4. Verify Persistence
```bash
# In REPL or via API
.snapshot                    # Create snapshot

# Stop the program (Ctrl+C)
# Restart: python repl.py or python app.py

# Data is still there!
SELECT * FROM customers      # Original data persists
```

##  Understanding B+ Trees

```python
# When you create a PRIMARY KEY or UNIQUE constraint:
CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE)

# The database automatically creates B+ tree indexes:
# - B+ tree on 'id' column
# - B+ tree on 'email' column

# Queries using these columns are O(log n):
SELECT * FROM users WHERE id = 5        # Uses B+ tree
SELECT * FROM users WHERE email = 'a@b' # Uses B+ tree

# Other queries do table scan O(n):
SELECT * FROM users WHERE name = 'Bob'  # Table scan (no index)
```

