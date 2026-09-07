-- AI Agent Bank | 2_transactions_transaction_logs.sql | Postgres/Supabase

CREATE TYPE transactiontype AS ENUM ('payment', 'withdrawal', 'approval');
CREATE TYPE transactionstatus AS ENUM ('pending', 'approved', 'rejected', 'executed', 'failed');
CREATE TYPE policycategory AS ENUM ('api', 'compute', 'data', 'agent');

CREATE TABLE transactions (
	id SERIAL NOT NULL, 
	agent_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	amount NUMERIC(20, 6) NOT NULL, 
	currency VARCHAR, 
	transaction_type transactiontype, 
	status transactionstatus, 
	recipient_address VARCHAR NOT NULL, 
	recipient_name VARCHAR, 
	category policycategory, 
	description TEXT, 
	idempotency_key VARCHAR, 
	tx_hash VARCHAR, 
	rejection_reason TEXT, 
	risk_score INTEGER, 
	risk_level VARCHAR(16), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	executed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE UNIQUE INDEX ix_transactions_idempotency_key ON transactions (idempotency_key);
CREATE INDEX ix_transactions_id ON transactions (id);

CREATE TABLE transaction_logs (
	id SERIAL NOT NULL, 
	transaction_id INTEGER NOT NULL, 
	log_level VARCHAR, 
	message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(transaction_id) REFERENCES transactions (id)
)

;
CREATE INDEX ix_transaction_logs_id ON transaction_logs (id);
