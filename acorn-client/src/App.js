import React, { useState, useEffect } from 'react';
import { Play, Database, Terminal, DollarSign, CreditCard, Users, Store, TrendingUp, Download, RefreshCw, Activity } from 'lucide-react';

const API_BASE = 'http://localhost:5000/api';

export default function PaymentRDBMSApp() {
  const [activeTab, setActiveTab] = useState('transactions');
  const [stats, setStats] = useState({ tables: 0, indexes: 0, wal_entries: 0, total_rows: 0 });
  const [replInput, setReplInput] = useState('');
  const [replHistory, setReplHistory] = useState([]);
  
  // Data state
  const [transactions, setTransactions] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [merchants, setMerchants] = useState([]);
  
  // Form state
  const [newTransaction, setNewTransaction] = useState({
    customer_id: '',
    merchant_id: '',
    amount: '',
    currency: 'USD',
    payment_method: 'credit_card',
    status: 'pending'
  });

  useEffect(() => {
    initializeDatabase();
  }, []);

  const executeSQL = async (sql) => {
    try {
      const response = await fetch(`${API_BASE}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql })
      });
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Query failed');
      }
      
      return data;
    } catch (error) {
      console.error('SQL Error:', error);
      throw error;
    }
  };

  const initializeDatabase = async () => {
    try {
      // Create schema
      await executeSQL(`CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE,
        name TEXT,
        phone TEXT,
        balance DECIMAL,
        created_at TEXT
      )`);

      await executeSQL(`CREATE TABLE merchants (
        id INTEGER PRIMARY KEY,
        business_name TEXT,
        merchant_id TEXT UNIQUE,
        category TEXT,
        commission_rate DECIMAL,
        created_at TEXT
      )`);

      await executeSQL(`CREATE TABLE transactions (
        id INTEGER PRIMARY KEY,
        transaction_id TEXT UNIQUE,
        customer_id INTEGER,
        merchant_id INTEGER,
        amount DECIMAL,
        currency TEXT,
        payment_method TEXT,
        status TEXT,
        created_at TEXT
      )`);

      // Create indexes
      await executeSQL('CREATE INDEX idx_customer_id ON transactions(customer_id)');
      await executeSQL('CREATE INDEX idx_merchant_id ON transactions(merchant_id)');
      await executeSQL('CREATE INDEX idx_status ON transactions(status)');

      // Insert sample data
      await executeSQL("INSERT INTO customers (email, name, phone, balance, created_at) VALUES ('alice@example.com', 'Alice Johnson', '+1234567890', 5000.00, '2025-01-10')");
      await executeSQL("INSERT INTO customers (email, name, phone, balance, created_at) VALUES ('bob@example.com', 'Bob Smith', '+1234567891', 3500.50, '2025-01-11')");
      await executeSQL("INSERT INTO customers (email, name, phone, balance, created_at) VALUES ('charlie@example.com', 'Charlie Brown', '+1234567892', 7200.00, '2025-01-12')");

      await executeSQL("INSERT INTO merchants (business_name, merchant_id, category, commission_rate, created_at) VALUES ('Coffee Shop Inc', 'MERCH_001', 'Food & Beverage', 2.5, '2025-01-01')");
      await executeSQL("INSERT INTO merchants (business_name, merchant_id, category, commission_rate, created_at) VALUES ('Tech Store LLC', 'MERCH_002', 'Electronics', 3.0, '2025-01-02')");
      await executeSQL("INSERT INTO merchants (business_name, merchant_id, category, commission_rate, created_at) VALUES ('BookWorld', 'MERCH_003', 'Books', 2.0, '2025-01-03')");

      await executeSQL("INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) VALUES ('TXN_001', 1, 1, 45.50, 'USD', 'credit_card', 'completed', '2025-01-14 10:30:00')");
      await executeSQL("INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) VALUES ('TXN_002', 2, 2, 1299.99, 'USD', 'debit_card', 'completed', '2025-01-14 11:15:00')");
      await executeSQL("INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) VALUES ('TXN_003', 1, 3, 29.99, 'USD', 'credit_card', 'pending', '2025-01-15 09:20:00')");

      await refreshData();
    } catch (error) {
      console.error('Initialization error:', error);
    }
  };

  const refreshData = async () => {
    try {
      // Fetch transactions with JOIN
      const txResult = await executeSQL(`
        SELECT 
          transactions.id,
          transactions.transaction_id,
          transactions.amount,
          transactions.currency,
          transactions.payment_method,
          transactions.status,
          transactions.created_at,
          customers.name,
          merchants.business_name
        FROM transactions
        JOIN customers ON transactions.customer_id = customers.id
        JOIN merchants ON transactions.merchant_id = merchants.id
      `);
      setTransactions(txResult.rows || []);

      // Fetch customers
      const custResult = await executeSQL('SELECT * FROM customers');
      setCustomers(custResult.rows || []);

      // Fetch merchants
      const merchResult = await executeSQL('SELECT * FROM merchants');
      setMerchants(merchResult.rows || []);

      // Fetch stats
      const statsResponse = await fetch(`${API_BASE}/stats`);
      const statsData = await statsResponse.json();
      setStats(statsData);
    } catch (error) {
      console.error('Refresh error:', error);
    }
  };

  const executeREPL = async () => {
    if (!replInput.trim()) return;

    try {
      const result = await executeSQL(replInput);
      setReplHistory(prev => [...prev, { input: replInput, output: result, error: false }]);
      setReplInput('');
      
      if (replInput.toUpperCase().includes('INSERT') || 
          replInput.toUpperCase().includes('UPDATE') || 
          replInput.toUpperCase().includes('DELETE')) {
       setTimeout(async () => {
        await refreshData();
      }, 100);
      }
    } catch (error) {
      setReplHistory(prev => [...prev, { input: replInput, output: error.message, error: true }]);
    }
  };

  const addTransaction = async () => {
    try {
      const txnId = `TXN_${Date.now()}`;
      const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
      
      await executeSQL(`
        INSERT INTO transactions (transaction_id, customer_id, merchant_id, amount, currency, payment_method, status, created_at) 
        VALUES ('${txnId}', ${newTransaction.customer_id}, ${newTransaction.merchant_id}, ${newTransaction.amount}, '${newTransaction.currency}', '${newTransaction.payment_method}', '${newTransaction.status}', '${now}')
      `);
      
      setNewTransaction({
        customer_id: '',
        merchant_id: '',
        amount: '',
        currency: 'USD',
        payment_method: 'credit_card',
        status: 'pending'
      });
      
      await refreshData();
    } catch (error) {
      alert('Error adding transaction: ' + error.message);
    }
  };

  const updateTransactionStatus = async (id, newStatus) => {
    try {
      await executeSQL(`UPDATE transactions SET status = '${newStatus}' WHERE id = ${id}`);
      await refreshData();
    } catch (error) {
      alert('Error updating transaction: ' + error.message);
    }
  };

  const createSnapshot = async () => {
    try {
      const response = await fetch(`${API_BASE}/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      
      if (data.success) {
        alert('Snapshot created successfully!');
      }
    } catch (error) {
      alert('Error creating snapshot: ' + error.message);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-900 text-green-300';
      case 'pending': return 'bg-yellow-900 text-yellow-300';
      case 'failed': return 'bg-red-900 text-red-300';
      default: return 'bg-gray-900 text-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-5xl font-bold mb-2 flex items-center gap-3">
                <Database className="w-12 h-12 text-pink-400" />
                Payment RDBMS
              </h1>
              <p className="text-purple-200">Custom Database with B+ Trees, WAL & Snapshots</p>
            </div>
            
            {/* Stats Dashboard */}
            <div className="bg-black/30 backdrop-blur rounded-lg p-4 border border-purple-400/30">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-purple-300 text-xs">Tables</div>
                  <div className="text-2xl font-bold text-pink-400">{stats.tables}</div>
                </div>
                <div className="text-center">
                  <div className="text-purple-300 text-xs">B+ Indexes</div>
                  <div className="text-2xl font-bold text-blue-400">{stats.indexes}</div>
                </div>
                <div className="text-center">
                  <div className="text-purple-300 text-xs">WAL Entries</div>
                  <div className="text-2xl font-bold text-green-400">{stats.wal_entries}</div>
                </div>
                <div className="text-center">
                  <div className="text-purple-300 text-xs">Total Rows</div>
                  <div className="text-2xl font-bold text-yellow-400">{stats.total_rows}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={createSnapshot}
              className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded flex items-center gap-2 transition-colors text-sm font-medium"
            >
              <Download className="w-4 h-4" />
              Create Snapshot
            </button>
            <button
              onClick={refreshData}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded flex items-center gap-2 transition-colors text-sm font-medium"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh Data
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-purple-400/30">
          <button
            onClick={() => setActiveTab('transactions')}
            className={`px-6 py-3 font-medium transition-colors flex items-center gap-2 ${
              activeTab === 'transactions'
                ? 'border-b-2 border-pink-400 text-pink-400'
                : 'text-purple-300 hover:text-purple-100'
            }`}
          >
            <DollarSign className="w-4 h-4" />
            Transactions
          </button>
          <button
            onClick={() => setActiveTab('customers')}
            className={`px-6 py-3 font-medium transition-colors flex items-center gap-2 ${
              activeTab === 'customers'
                ? 'border-b-2 border-pink-400 text-pink-400'
                : 'text-purple-300 hover:text-purple-100'
            }`}
          >
            <Users className="w-4 h-4" />
            Customers
          </button>
          <button
            onClick={() => setActiveTab('merchants')}
            className={`px-6 py-3 font-medium transition-colors flex items-center gap-2 ${
              activeTab === 'merchants'
                ? 'border-b-2 border-pink-400 text-pink-400'
                : 'text-purple-300 hover:text-purple-100'
            }`}
          >
            <Store className="w-4 h-4" />
            Merchants
          </button>
          <button
            onClick={() => setActiveTab('repl')}
            className={`px-6 py-3 font-medium transition-colors flex items-center gap-2 ${
              activeTab === 'repl'
                ? 'border-b-2 border-pink-400 text-pink-400'
                : 'text-purple-300 hover:text-purple-100'
            }`}
          >
            <Terminal className="w-4 h-4" />
            SQL REPL
          </button>
        </div>

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="space-y-6">
            {/* Add Transaction Form */}
            <div className="bg-black/20 backdrop-blur rounded-lg p-6 border border-purple-400/30">
              <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
                <CreditCard className="w-6 h-6 text-pink-400" />
                New Transaction
              </h2>
              <div className="grid grid-cols-3 gap-4">
                <select
                  value={newTransaction.customer_id}
                  onChange={(e) => setNewTransaction({...newTransaction, customer_id: e.target.value})}
                  className="bg-purple-900/50 border border-purple-400/30 rounded px-4 py-2 focus:outline-none focus:border-pink-400"
                >
                  <option value="">Select Customer</option>
                  {customers.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <select
                  value={newTransaction.merchant_id}
                  onChange={(e) => setNewTransaction({...newTransaction, merchant_id: e.target.value})}
                  className="bg-purple-900/50 border border-purple-400/30 rounded px-4 py-2 focus:outline-none focus:border-pink-400"
                >
                  <option value="">Select Merchant</option>
                  {merchants.map(m => (
                    <option key={m.id} value={m.id}>{m.business_name}</option>
                  ))}
                </select>
                <input
                  type="number"
                  step="0.01"
                  placeholder="Amount"
                  value={newTransaction.amount}
                  onChange={(e) => setNewTransaction({...newTransaction, amount: e.target.value})}
                  className="bg-purple-900/50 border border-purple-400/30 rounded px-4 py-2 focus:outline-none focus:border-pink-400"
                />
                <select
                  value={newTransaction.payment_method}
                  onChange={(e) => setNewTransaction({...newTransaction, payment_method: e.target.value})}
                  className="bg-purple-900/50 border border-purple-400/30 rounded px-4 py-2 focus:outline-none focus:border-pink-400"
                >
                  <option value="credit_card">Credit Card</option>
                  <option value="debit_card">Debit Card</option>
                  <option value="bank_transfer">Bank Transfer</option>
                  <option value="digital_wallet">Digital Wallet</option>
                </select>
                <select
                  value={newTransaction.status}
                  onChange={(e) => setNewTransaction({...newTransaction, status: e.target.value})}
                  className="bg-purple-900/50 border border-purple-400/30 rounded px-4 py-2 focus:outline-none focus:border-pink-400"
                >
                  <option value="pending">Pending</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                </select>
                <button
                  onClick={addTransaction}
                  disabled={!newTransaction.customer_id || !newTransaction.merchant_id || !newTransaction.amount}
                  className="bg-pink-600 hover:bg-pink-700 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-2 rounded transition-colors font-medium"
                >
                  Add Transaction
                </button>
              </div>
            </div>

            {/* Transactions List */}
            <div className="bg-black/20 backdrop-blur rounded-lg p-6 border border-purple-400/30">
              <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
                <Activity className="w-6 h-6 text-blue-400" />
                Recent Transactions
              </h2>
              <div className="space-y-3">
                {transactions.map(tx => (
                  <div key={tx.id} className="bg-purple-900/30 rounded-lg p-4 border border-purple-400/20">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="font-mono text-sm text-purple-300">{tx.transaction_id}</span>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(tx.status)}`}>
                            {tx.status}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <span className="text-purple-400">Customer:</span> {tx.name}
                          </div>
                          <div>
                            <span className="text-purple-400">Merchant:</span> {tx.business_name}
                          </div>
                          <div>
                            <span className="text-purple-400">Amount:</span> <span className="text-green-400 font-bold">{formatCurrency(tx.amount)}</span>
                          </div>
                          <div>
                            <span className="text-purple-400">Method:</span> {tx.payment_method}
                          </div>
                          <div className="col-span-2">
                            <span className="text-purple-400">Date:</span> {tx.created_at}
                          </div>
                        </div>
                      </div>
                      {tx.status === 'pending' && (
                        <button
                          onClick={() => updateTransactionStatus(tx.id, 'completed')}
                          className="ml-4 bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm transition-colors"
                        >
                          Complete
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Customers Tab */}
        {activeTab === 'customers' && (
          <div className="bg-black/20 backdrop-blur rounded-lg p-6 border border-purple-400/30">
            <h2 className="text-2xl font-semibold mb-4">Customers</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {customers.map(customer => (
                <div key={customer.id} className="bg-purple-900/30 rounded-lg p-4 border border-purple-400/20">
                  <h3 className="font-bold text-lg mb-2">{customer.name}</h3>
                  <div className="space-y-1 text-sm">
                    <div><span className="text-purple-400">Email:</span> {customer.email}</div>
                    <div><span className="text-purple-400">Phone:</span> {customer.phone}</div>
                    <div><span className="text-purple-400">Balance:</span> <span className="text-green-400 font-bold">{formatCurrency(customer.balance)}</span></div>
                    <div><span className="text-purple-400">Member since:</span> {customer.created_at}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Merchants Tab */}
        {activeTab === 'merchants' && (
          <div className="bg-black/20 backdrop-blur rounded-lg p-6 border border-purple-400/30">
            <h2 className="text-2xl font-semibold mb-4">Merchants</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {merchants.map(merchant => (
                <div key={merchant.id} className="bg-purple-900/30 rounded-lg p-4 border border-purple-400/20">
                  <h3 className="font-bold text-lg mb-2">{merchant.business_name}</h3>
                  <div className="space-y-1 text-sm">
                    <div><span className="text-purple-400">ID:</span> {merchant.merchant_id}</div>
                    <div><span className="text-purple-400">Category:</span> {merchant.category}</div>
                    <div><span className="text-purple-400">Commission:</span> {merchant.commission_rate}%</div>
                    <div><span className="text-purple-400">Registered:</span> {merchant.created_at}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* REPL Tab */}
        {activeTab === 'repl' && (
          <div className="bg-black/20 backdrop-blur rounded-lg p-6 border border-purple-400/30">
            <h2 className="text-2xl font-semibold mb-4">SQL REPL</h2>
            
            <div className="mb-4 bg-black/50 rounded p-4 font-mono text-sm max-h-96 overflow-y-auto border border-purple-400/20">
              {replHistory.length === 0 ? (
                <div className="text-purple-400">
                  Try commands like:<br/>
                  • SELECT * FROM transactions WHERE status = 'completed'<br/>
                  • UPDATE transactions SET status = 'completed' WHERE id = 1<br/>
                  • SELECT customers.name, transactions.amount FROM customers JOIN transactions ON customers.id = transactions.customer_id<br/>
                  • SHOW TABLES<br/>
                  • DESCRIBE transactions
                </div>
              ) : (
                replHistory.map((entry, idx) => (
                  <div key={idx} className="mb-4">
                    <div className="text-green-400">sql&gt; {entry.input}</div>
                    <div className={entry.error ? 'text-red-400' : 'text-purple-200'}>
                      {entry.error ? (
                        `Error: ${entry.output}`
                      ) : (
                        <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(entry.output, null, 2)}</pre>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={replInput}
                onChange={(e) => setReplInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && executeREPL()}
                placeholder="Enter SQL command..."
                className="flex-1 bg-purple-900/50 border border-purple-400/30 rounded px-4 py-2 focus:outline-none focus:border-pink-400"
              />
              <button
                onClick={executeREPL}
                className="bg-pink-600 hover:bg-pink-700 px-6 py-2 rounded flex items-center gap-2 transition-colors"
              >
                <Play className="w-4 h-4" />
                Execute
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
    
  );
}