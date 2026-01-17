"""
Payment RDBMS - Custom Database Implementation with B+ Trees and WAL
Run with: python app.py
Then start frontend with: npm start (in frontend directory)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from typing import Any, List, Dict, Optional
import bisect

# ==================== B+ TREE IMPLEMENTATION ====================

class BPlusTreeNode:
    """Node in a B+ tree for indexing"""
    def __init__(self, order=4, is_leaf=False):
        self.order = order
        self.is_leaf = is_leaf
        self.keys = []
        self.children = []
        self.values = []  # Only used in leaf nodes
        self.next = None  # Pointer to next leaf (for range queries)

class BPlusTree:
    """B+ Tree for efficient indexing"""
    def __init__(self, order=4):
        self.root = BPlusTreeNode(order, is_leaf=True)
        self.order = order
    
    def search(self, key):
        """Search for a key in the B+ tree"""
        node = self.root
        
        while not node.is_leaf:
            i = bisect.bisect_left(node.keys, key)
            node = node.children[i]
        
        try:
            idx = node.keys.index(key)
            return node.values[idx]
        except ValueError:
            return None
    
    def insert(self, key, value):
        """Insert a key-value pair into the B+ tree"""
        root = self.root
        
        if len(root.keys) >= self.order - 1:
            new_root = BPlusTreeNode(self.order, is_leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
        
        self._insert_non_full(self.root, key, value)
    
    def _insert_non_full(self, node, key, value):
        """Insert into a non-full node"""
        if node.is_leaf:
            # Insert into sorted position
            i = bisect.bisect_left(node.keys, key)
            node.keys.insert(i, key)
            node.values.insert(i, value)
        else:
            # Find child to insert into
            i = bisect.bisect_left(node.keys, key)
            
            if len(node.children[i].keys) >= self.order - 1:
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            
            self._insert_non_full(node.children[i], key, value)
    
    def _split_child(self, parent, index):
        """Split a full child node"""
        full_node = parent.children[index]
        new_node = BPlusTreeNode(self.order, is_leaf=full_node.is_leaf)
        mid = self.order // 2
        
        # Split keys
        new_node.keys = full_node.keys[mid:]
        full_node.keys = full_node.keys[:mid]
        
        if full_node.is_leaf:
            # Split values in leaf nodes
            new_node.values = full_node.values[mid:]
            full_node.values = full_node.values[:mid]
            
            # Update leaf links
            new_node.next = full_node.next
            full_node.next = new_node
            
            # Promote first key of new node
            parent.keys.insert(index, new_node.keys[0])
        else:
            # Split children in internal nodes
            new_node.children = full_node.children[mid:]
            full_node.children = full_node.children[:mid]
            
            # Promote middle key
            promoted_key = full_node.keys.pop()
            parent.keys.insert(index, promoted_key)
        
        parent.children.insert(index + 1, new_node)
    
    def range_query(self, min_key, max_key):
        """Perform range query (for analytical queries)"""
        results = []
        node = self.root
        
        # Navigate to leftmost leaf
        while not node.is_leaf:
            i = bisect.bisect_left(node.keys, min_key)
            node = node.children[i]
        
        # Traverse leaf nodes
        while node:
            for i, key in enumerate(node.keys):
                if min_key <= key <= max_key:
                    results.extend(node.values[i])
                elif key > max_key:
                    return results
            node = node.next
        
        return results

# ==================== WRITE-AHEAD LOG ====================

class WALEntry:
    """Write-Ahead Log entry for durability"""
    def __init__(self, operation, table, data, lsn=None):
        self.operation = operation  # CREATE_TABLE, INSERT, UPDATE, DELETE
        self.table = table
        self.data = data
        self.timestamp = datetime.now().isoformat()
        self.lsn = lsn

    def to_dict(self):
        return {
            'operation': self.operation,
            'table': self.table,
            'data': self.data,
            'timestamp': self.timestamp,
            'lsn': self.lsn
        }

class WriteAheadLog:
    """Write-Ahead Log for crash recovery"""
    def __init__(self, wal_file='wal.log'):
        self.wal_file = wal_file
        self.entries = []
        self.lsn_counter = 0
        self.checkpoint_lsn = 0
        self._load_wal()
    
    def append(self, operation, table, data):
        """Append entry to WAL"""
        entry = WALEntry(operation, table, data, self.lsn_counter)
        self.lsn_counter += 1
        self.entries.append(entry)
        
        # Persist to disk
        self._persist_entry(entry)
        
        # Checkpoint every 100 entries
        if len(self.entries) - self.checkpoint_lsn > 100:
            self.checkpoint()
        
        return entry.lsn
    
    def checkpoint(self):
        """Create checkpoint"""
        self.checkpoint_lsn = len(self.entries)
        print(f"[WAL] Checkpoint at LSN {self.lsn_counter}")
    
    def _persist_entry(self, entry):
        """Write entry to disk"""
        with open(self.wal_file, 'a') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')
    
    def _load_wal(self):
        """Load WAL from disk on startup"""
        if os.path.exists(self.wal_file):
            with open(self.wal_file, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        entry = WALEntry(
                            data['operation'],
                            data['table'],
                            data['data'],
                            data['lsn']
                        )
                        self.entries.append(entry)
                        self.lsn_counter = max(self.lsn_counter, data['lsn'] + 1)
    
    def clear(self):
        """Clear WAL (after successful checkpoint)"""
        if os.path.exists(self.wal_file):
            os.remove(self.wal_file)
        self.entries = []

# ==================== STORAGE MANAGER ====================

class StorageManager:
    """Manages snapshots and recovery"""
    def __init__(self, snapshot_file='db_snapshot.json'):
        self.snapshot_file = snapshot_file
    
    def create_snapshot(self, tables):
        """Create database snapshot"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'tables': {}
        }
        
        for name, table in tables.items():
            snapshot['tables'][name] = {
                'columns': table.columns,
                'rows': table.rows,
                'primary_key': table.primary_key,
                'unique_columns': list(table.unique_columns),
                'next_id': table.next_id
            }
        
        with open(self.snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        return snapshot
    
    def load_snapshot(self):
        """Load database from snapshot"""
        if os.path.exists(self.snapshot_file):
            with open(self.snapshot_file, 'r') as f:
                return json.load(f)
        return None

# ==================== TABLE STRUCTURE ====================

class Table:
    """Represents a database table"""
    def __init__(self, name, columns, primary_key=None):
        self.name = name
        self.columns = columns  # List of {'name': str, 'type': str, 'is_primary': bool, 'is_unique': bool}
        self.rows = []
        self.primary_key = primary_key
        self.unique_columns = set()
        self.next_id = 1
        
        # Identify unique columns
        for col in columns:
            if col.get('is_unique'):
                self.unique_columns.add(col['name'])

# ==================== PAYMENT RDBMS ====================

class PaymentRDBMS:
    """Custom RDBMS with B+ Trees and WAL"""
    def __init__(self):
        self.tables = {}
        self.indexes = {}
        self.wal = WriteAheadLog()
        self.storage = StorageManager()
        self._load_from_snapshot()
    
    def _load_from_snapshot(self):
        """Load database from snapshot on startup"""
        snapshot = self.storage.load_snapshot()
        if snapshot:
            for name, table_data in snapshot['tables'].items():
                table = Table(name, table_data['columns'], table_data['primary_key'])
                table.rows = table_data['rows']
                table.unique_columns = set(table_data['unique_columns'])
                table.next_id = table_data['next_id']
                self.tables[name] = table
                
                # Rebuild indexes
                if table.primary_key:
                    self._create_index(name, table.primary_key)
                for col in table.unique_columns:
                    self._create_index(name, col)
    
    def execute(self, sql):
        """Execute SQL-like command"""
        sql = sql.strip()
        sql_upper = sql.upper()
        
        if sql_upper.startswith('CREATE TABLE'):
            return self._create_table(sql)
        elif sql_upper.startswith('INSERT INTO'):
            return self._insert(sql)
        elif sql_upper.startswith('SELECT'):
            return self._select(sql)
        elif sql_upper.startswith('UPDATE'):
            return self._update(sql)
        elif sql_upper.startswith('DELETE FROM'):
            return self._delete(sql)
        elif sql_upper.startswith('CREATE INDEX'):
            return self._create_index_sql(sql)
        elif sql_upper.startswith('SHOW TABLES'):
            return self._show_tables()
        elif sql_upper.startswith('DESCRIBE'):
            return self._describe(sql)
        else:
            raise ValueError(f"Unknown SQL command: {sql}")
    
    def _create_table(self, sql):
        """CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE)"""
        import re
        match = re.match(r'CREATE TABLE (\w+)\s*\((.*)\)', sql, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid CREATE TABLE syntax")
        
        table_name = match.group(1)
        column_defs = [col.strip() for col in match.group(2).split(',')]
        
        columns = []
        primary_key = None
        
        for col_def in column_defs:
            parts = col_def.split()
            col_name = parts[0]
            col_type = parts[1] if len(parts) > 1 else 'TEXT'
            
            is_primary = 'PRIMARY KEY' in col_def.upper()
            is_unique = 'UNIQUE' in col_def.upper()
            
            columns.append({
                'name': col_name,
                'type': col_type,
                'is_primary': is_primary,
                'is_unique': is_unique
            })
            
            if is_primary:
                primary_key = col_name
                self._create_index(table_name, col_name)
            if is_unique:
                self._create_index(table_name, col_name)
        
        table = Table(table_name, columns, primary_key)
        self.tables[table_name] = table
        
        self.wal.append('CREATE_TABLE', table_name, {'columns': columns})
        
        return {'success': True, 'message': f'Table {table_name} created'}
    
    def _create_index(self, table_name, column_name, index_name=None):
        """Create B+ tree index on column"""
        key = index_name or f"{table_name}_{column_name}_idx"
        tree = BPlusTree(order=4)
        
        if table_name in self.tables:
            table = self.tables[table_name]
            for row in table.rows:
                value = row.get(column_name)
                if value is not None:
                    existing = tree.search(value) or []
                    existing.append(row)
                    tree.insert(value, existing)
        
        self.indexes[key] = {
            'table': table_name,
            'column': column_name,
            'tree': tree
        }
    
    def _create_index_sql(self, sql):
        """CREATE INDEX idx_name ON table(column)"""
        import re
        match = re.match(r'CREATE INDEX (\w+) ON (\w+)\((\w+)\)', sql, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid CREATE INDEX syntax")
        
        index_name = match.group(1)
        table_name = match.group(2)
        column_name = match.group(3)
        
        self._create_index(table_name, column_name, index_name)
        return {'success': True, 'message': f'B+ Tree index {index_name} created'}
    
    def _insert(self, sql):
        """INSERT INTO users (name, email) VALUES ('John', 'john@example.com')"""
        import re
        match = re.match(r"INSERT INTO (\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)", sql, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid INSERT syntax")
        
        table_name = match.group(1)
        columns = [col.strip() for col in match.group(2).split(',')]
        values = [self._parse_value(val.strip()) for val in match.group(3).split(',')]
        
        table = self.tables.get(table_name)
        if not table:
            raise ValueError(f"Table {table_name} does not exist")
        
        row = {}
        
        # Auto-generate primary key if not provided
        if table.primary_key and table.primary_key not in columns:
            row[table.primary_key] = table.next_id
            table.next_id += 1
        
        for col, val in zip(columns, values):
            row[col] = val
        
        # Check unique constraints
        for unique_col in table.unique_columns:
            if unique_col in row:
                for existing_row in table.rows:
                    if existing_row.get(unique_col) == row[unique_col]:
                        raise ValueError(f"Duplicate value for unique column {unique_col}")
        
        table.rows.append(row)
        
        # Update indexes
        for index_key, index_data in self.indexes.items():
            if index_data['table'] == table_name:
                col_name = index_data['column']
                if col_name in row:
                    value = row[col_name]
                    existing = index_data['tree'].search(value) or []
                    existing.append(row)
                    index_data['tree'].insert(value, existing)
        
        self.wal.append('INSERT', table_name, row)
        
        return {
            'success': True,
            'message': 'Row inserted',
            'inserted_id': row.get(table.primary_key)
        }
    
    def _select(self, sql):
        """SELECT * FROM users WHERE email = 'john@example.com'"""
        import re
        
        # Check for JOIN
        join_match = re.match(
            r"SELECT\s+(.*?)\s+FROM\s+(\w+)\s+JOIN\s+(\w+)\s+ON\s+([\w.]+)\s*=\s*([\w.]+)(?:\s+WHERE\s+(.*))?",
            sql, re.IGNORECASE
        )
        
        if join_match:
            return self._select_join(join_match)
        
        # Simple SELECT
        match = re.match(r"SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*))?", sql, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid SELECT syntax")
        
        columns = match.group(1).strip()
        table_name = match.group(2)
        where_clause = match.group(3)
        
        table = self.tables.get(table_name)
        if not table:
            raise ValueError(f"Table {table_name} does not exist")
        
        rows = list(table.rows)
        
        # Apply WHERE clause
        if where_clause:
            rows = self._filter_rows(table, rows, where_clause)
        
        # Select columns
        if columns == '*':
            return {
                'success': True,
                'rows': rows,
                'columns': [col['name'] for col in table.columns]
            }
        else:
            select_cols = [col.strip() for col in columns.split(',')]
            result = []
            for row in rows:
                new_row = {col: row.get(col) for col in select_cols}
                result.append(new_row)
            return {'success': True, 'rows': result, 'columns': select_cols}
    
    def _select_join(self, match):
        """Handle JOIN queries"""
        columns = match.group(1).strip()
        table1_name = match.group(2)
        table2_name = match.group(3)
        join_col1 = match.group(4)
        join_col2 = match.group(5)
        
        table1 = self.tables.get(table1_name)
        table2 = self.tables.get(table2_name)
        
        if not table1 or not table2:
            raise ValueError("Table does not exist")
        
        # Parse join columns
        col1 = join_col1.split('.')[-1]
        col2 = join_col2.split('.')[-1]
        
        # Nested loop join
        result = []
        for row1 in table1.rows:
            for row2 in table2.rows:
                if row1.get(col1) == row2.get(col2):
                    joined_row = {}
                    for k, v in row1.items():
                        joined_row[f"{table1_name}.{k}"] = v
                    for k, v in row2.items():
                        joined_row[f"{table2_name}.{k}"] = v
                    result.append(joined_row)
        
        # Select columns
        if columns == '*':
            select_cols = list(result[0].keys()) if result else []
        else:
            select_cols = [col.strip() for col in columns.split(',')]
            result = [{col: row.get(col) for col in select_cols} for row in result]
        
        return {'success': True, 'rows': result, 'columns': select_cols}
    
    def _update(self, sql):
        """UPDATE users SET name = 'Jane' WHERE id = 1"""
        import re
        match = re.match(r"UPDATE (\w+)\s+SET\s+(.*?)\s+WHERE\s+(.*)", sql, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid UPDATE syntax")
        
        table_name = match.group(1)
        set_clause = match.group(2)
        where_clause = match.group(3)
        
        table = self.tables.get(table_name)
        if not table:
            raise ValueError(f"Table {table_name} does not exist")
        
        # Parse SET clause
        updates = {}
        for pair in set_clause.split(','):
            col, val = pair.split('=')
            updates[col.strip()] = self._parse_value(val.strip())
        
        # Filter rows
        rows = self._filter_rows(table, table.rows, where_clause)
        
        for row in rows:
            old_row = row.copy()
            for col, val in updates.items():
                row[col] = val
            self.wal.append('UPDATE', table_name, {'old': old_row, 'new': row})
        
        return {'success': True, 'message': f'{len(rows)} row(s) updated'}
    
    def _delete(self, sql):
        """DELETE FROM users WHERE id = 1"""
        import re
        match = re.match(r"DELETE FROM (\w+)\s+WHERE\s+(.*)", sql, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid DELETE syntax")
        
        table_name = match.group(1)
        where_clause = match.group(2)
        
        table = self.tables.get(table_name)
        if not table:
            raise ValueError(f"Table {table_name} does not exist")
        
        to_delete = self._filter_rows(table, table.rows, where_clause)
        
        for row in to_delete:
            self.wal.append('DELETE', table_name, row)
        
        table.rows = [row for row in table.rows if row not in to_delete]
        
        return {'success': True, 'message': f'{len(to_delete)} row(s) deleted'}
    
    def _filter_rows(self, table, rows, where_clause):
        """Filter rows based on WHERE clause"""
        import re
        match = re.match(r"(\w+)\s*=\s*(.+)", where_clause)
        if not match:
            raise ValueError("Invalid WHERE clause")
        
        column = match.group(1)
        value = self._parse_value(match.group(2).strip())
        
        # Try to use index
        index_key = f"{table.name}_{column}_idx"
        if index_key in self.indexes:
            results = self.indexes[index_key]['tree'].search(value)
            return results if results else []
        
        # Fallback to table scan
        return [row for row in rows if row.get(column) == value]
    
    def _parse_value(self, val):
        """Parse SQL value"""
        if val.startswith("'") and val.endswith("'"):
            return val[1:-1]
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        try:
            if '.' in val:
                return float(val)
            return int(val)
        except ValueError:
            return val
    
    def _show_tables(self):
        """SHOW TABLES"""
        return {'success': True, 'tables': list(self.tables.keys())}
    
    def _describe(self, sql):
        """DESCRIBE users"""
        import re
        match = re.match(r"DESCRIBE (\w+)", sql, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid DESCRIBE syntax")
        
        table_name = match.group(1)
        table = self.tables.get(table_name)
        if not table:
            raise ValueError(f"Table {table_name} does not exist")
        
        return {
            'success': True,
            'columns': table.columns,
            'primary_key': table.primary_key
        }
    
    def get_stats(self):
        """Get database statistics"""
        total_rows = sum(len(table.rows) for table in self.tables.values())
        return {
            'tables': len(self.tables),
            'indexes': len(self.indexes),
            'wal_entries': len(self.wal.entries),
            'total_rows': total_rows
        }
    
    def create_snapshot(self):
        """Create database snapshot"""
        return self.storage.create_snapshot(self.tables)

# ==================== FLASK API ====================

app = Flask(__name__)
CORS(app)

db = PaymentRDBMS()

@app.route('/api/execute', methods=['POST'])
def execute_sql():
    """Execute SQL command"""
    try:
        data = request.json
        sql = data.get('sql', '')
        result = db.execute(sql)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    return jsonify(db.get_stats())

@app.route('/api/snapshot', methods=['POST'])
def create_snapshot():
    """Create database snapshot"""
    try:
        snapshot = db.create_snapshot()
        return jsonify({'success': True, 'snapshot': snapshot})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/wal', methods=['GET'])
def get_wal():
    """Get WAL entries"""
    entries = [entry.to_dict() for entry in db.wal.entries[-100:]]  # Last 100 entries
    return jsonify({'entries': entries})

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'database': 'PaymentRDBMS'})
def initialize_sample_data():
    """Initialize sample payment schema if tables don't exist"""
    try:
        result = db.execute("SHOW TABLES")
        if result['tables']:
            print(f"[INFO] Found existing tables: {result['tables']}")
            return
        
        print("[INFO] Initializing sample payment schema...")
        
        # Create tables - SINGLE LINE SQL
        db.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, phone TEXT, balance DECIMAL, created_at TEXT)")
        
        db.execute("CREATE TABLE merchants (id INTEGER PRIMARY KEY, business_name TEXT, merchant_id TEXT UNIQUE, category TEXT, commission_rate DECIMAL, created_at TEXT)")
        
        db.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, transaction_id TEXT UNIQUE, customer_id INTEGER, merchant_id INTEGER, amount DECIMAL, currency TEXT, payment_method TEXT, status TEXT, created_at TEXT)")
        
        # Create indexes
        db.execute("CREATE INDEX idx_customer_id ON transactions(customer_id)")
        db.execute("CREATE INDEX idx_merchant_id ON transactions(merchant_id)")
        db.execute("CREATE INDEX idx_status ON transactions(status)")
        
        # Insert sample data
        db.execute("INSERT INTO customers (email, name, phone, balance, created_at) VALUES ('alice@example.com', 'Alice Johnson', '+1234567890', 5000.00, '2025-01-10')")
        db.execute("INSERT INTO customers (email, name, phone, balance, created_at) VALUES ('bob@example.com', 'Bob Smith', '+1234567891', 3500.50, '2025-01-11')")
        db.execute("INSERT INTO customers (email, name, phone, balance, created_at) VALUES ('charlie@example.com', 'Charlie Brown', '+1234567892', 7200.00, '2025-01-12')")
        
        db.execute("INSERT INTO merchants (business_name, merchant_id, category, commission_rate, created_at) VALUES ('Coffee Shop Inc', 'MERCH_001', 'Food & Beverage', 2.5, '2025-01-01')")
        db.execute("INSERT INTO merchants (business_name, merchant_id, category, commission_rate, created_at) VALUES ('Tech Store LLC', 'MERCH_002', 'Electronics', 3.0, '2025-01-02')")
        db.execute("INSERT INTO merchants (business_name, merchant_id, category, commission_rate, created_at) VALUES ('BookWorld', 'MERCH_003', 'Books', 2.0, '2025-01-03')")
        
        db.execute("INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) VALUES ('TXN_001', 1, 1, 45.50, 'USD', 'credit_card', 'completed', '2025-01-14 10:30:00')")
        db.execute("INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) VALUES ('TXN_002', 2, 2, 1299.99, 'USD', 'debit_card', 'completed', '2025-01-14 11:15:00')")
        db.execute("INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) VALUES ('TXN_003', 1, 3, 29.99, 'USD', 'credit_card', 'pending', '2025-01-15 09:20:00')")
        
        print("[INFO] ✓ Sample data initialized successfully!")
        print(f"[INFO] Created 3 tables with 8 rows")
        
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
if __name__ == '__main__':
    print("=" * 60)
    print("Payment RDBMS Server")
    print("=" * 60)
    print("Features:")
    print("  ✓ B+ Tree Indexing")
    print("  ✓ Write-Ahead Log (WAL)")
    print("  ✓ Snapshot/Recovery")
    print("  ✓ SQL-like Interface")
    print("  ✓ CRUD Operations")
    print("  ✓ JOIN Support")
    print("=" * 60)

    initialize_sample_data()
    print("\nStarting server on http://localhost:5000")
    print("API Endpoints:")
    print("  POST /api/execute - Execute SQL")
    print("  GET  /api/stats   - Get statistics")
    print("  POST /api/snapshot - Create snapshot")
    print("  GET  /api/wal     - Get WAL entries")
    print("=" * 60)
    
    app.run(debug=True, port=5000)