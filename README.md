# acorn-db
# Payment RDBMS - Production-Grade Database System

A full-stack application featuring a custom-built relational database management system with B+ tree indexing, Write-Ahead Log (WAL), and snapshot-based recovery for a payment processing domain.

## Features

### Database Engine
-  **B+ Tree Indexing** - O(log n) search performance
-  **Write-Ahead Log (WAL)** - Durability and crash recovery
-  **Snapshot/Recovery** - Point-in-time database backups
-  **SQL-like Interface** - Familiar query syntax
-  **CRUD Operations** - Full Create, Read, Update, Delete support
-  **JOIN Support** - Multi-table queries
-  **Primary & Unique Keys** - Data integrity constraints
-  **REPL Mode** - Interactive SQL console

### Application
-  **Payment Processing Domain** - Realistic financial data types
-  **Transaction Management** - Track payments, customers, merchants
-  **Real-time Statistics** - Monitor database metrics
-  **Live Updates** - React frontend with instant refresh

##  Prerequisites

- Python 3.8+
- Node.js 14+
- pip (Python package manager)
- npm (Node package manager)

## Installation

### Backend Setup

1. **Install Python dependencies:**
```bash
pip install flask flask-cors
```

2. **Run the backend:**
```bash
python app.py
```

The server will start on `http://localhost:5000`

### Frontend Setup

1. **Create React app (if starting fresh):**
```bash
npx create-react-app acorn-client
cd acorn-client
```

2. **Install dependencies:**
```bash
npm install lucide-react
```

3. **Replace `src/App.js` with the provided React component**

4. **Start the development server:**
```bash
npm start
```

The app will open at `http://localhost:3000`

## Project Structure

```
payment-rdbms/
├── app.py                 # Python backend with custom RDBMS
├── db_snapshot.json       # Database snapshot file (created at runtime)
├── wal.log               # Write-Ahead Log (created at runtime)
└── frontend/
    ├── src/
    │   └── App.js        # React frontend
    ├── package.json
    └── public/
```

### 1. **B+ Tree Implementation**
- Why B+ trees over hash indexes? Range queries and ordered traversal
- Node splitting algorithm for maintaining balance
- Leaf node linking for efficient range scans

### 2. **Write-Ahead Log**
- Ensures durability (ACID properties)
- Sequential writes for performance
- Checkpoint mechanism to truncate log
- Recovery: replay WAL from last checkpoint

### 3. **Storage Design**
- Snapshot + WAL hybrid approach
- Snapshot: point-in-time consistent state
- WAL: incremental changes since last snapshot
- Trade-off: snapshot frequency vs. recovery time

### 4. **Query Processing**
- SQL parsing with regex (production would use proper parser)
- Index selection: use B+ tree when available, else table scan
- Join algorithm: nested loop (could optimize to hash join)
- Filter push-down for efficiency

### 5. **Data Types**
- `INTEGER` - Auto-incrementing IDs
- `DECIMAL` - Precise financial calculations
- `TEXT` - Variable-length strings
- `UNIQUE` constraint - Enforced via B+ tree lookup

### 6. **Scalability Considerations**
- Current: single-threaded, in-memory
- Production needs:
  - Disk-based storage with buffer pool
  - Concurrent access with MVCC or locking
  - Query optimizer with statistics
  - Partitioning for horizontal scaling

## Database Schema

### Customers Table
```sql
CREATE TABLE customers (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE,
  name TEXT,
  phone TEXT,
  balance DECIMAL,
  created_at TEXT
)
```

### Merchants Table
```sql
CREATE TABLE merchants (
  id INTEGER PRIMARY KEY,
  business_name TEXT,
  merchant_id TEXT UNIQUE,
  category TEXT,
  commission_rate DECIMAL,
  created_at TEXT
)
```

### Transactions Table
```sql
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
```

### Indexes
```sql
CREATE INDEX idx_customer_id ON transactions(customer_id)
CREATE INDEX idx_merchant_id ON transactions(merchant_id)
CREATE INDEX idx_status ON transactions(status)
```

## Example Queries

### Simple SELECT
```sql
SELECT * FROM customers WHERE email = 'alice@example.com'
```

### JOIN Query
```sql
SELECT 
  customers.name, 
  transactions.amount, 
  merchants.business_name
FROM transactions
JOIN customers ON transactions.customer_id = customers.id
JOIN merchants ON transactions.merchant_id = merchants.id
```

### UPDATE
```sql
UPDATE transactions SET status = 'completed' WHERE id = 1
```

### DELETE
```sql
DELETE FROM transactions WHERE status = 'failed'
```

## Testing the System

1. **Start both servers** (backend and frontend)
2. **Navigate to Transactions tab** - Add new payment transactions
3. **Try the SQL REPL** - Execute custom queries
4. **Monitor statistics** - Watch indexes and WAL entries grow
5. **Create snapshots** - Test backup functionality
6. **Kill and restart backend** - Verify data persists via snapshot/WAL

## What This Demonstrates
### General:
1. **Systems Design** - Understanding database internals
2. **Data Structures** - B+ trees, hash maps, arrays
3. **Algorithms** - Search, insertion, tree balancing
4. **Durability** - WAL and snapshot mechanisms
5. **Full-stack Skills** - Python backend + React frontend
6. **Domain Knowledge** - Payment processing schemas
7. **Trade-offs** - Performance vs. simplicity decisions

### Key Metrics:
- **Index Lookups**: O(log n) with B+ trees
- **WAL Writes**: Sequential, append-only
- **Snapshot Size**: Proportional to data volume
- **Recovery Time**: Snapshot load + WAL replay

## Performance Characteristics

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| Index Search | O(log n) | B+ tree lookup |
| Table Scan | O(n) | No index available |
| Insert | O(log n) | Index update |
| WAL Append | O(1) | Sequential write |
| Snapshot | O(n) | Full table dump |

## Advanced Features to Discuss

### Not Implemented (but can explain):
1. **Transactions** - BEGIN, COMMIT, ROLLBACK
2. **Concurrency** - Two-phase locking, MVCC
3. **Query Optimizer** - Cost-based query planning
4. **Buffer Pool** - In-memory cache for disk pages
5. **Replication** - Master-slave, leader election
6. **Sharding** - Horizontal partitioning

##  Notes

- This is an educational implementation showing database concepts
- Production databases (PostgreSQL, MySQL) have years of optimization

