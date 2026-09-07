-- AI Agent Bank | 1_users_agents_policies.sql | Postgres/Supabase


CREATE TABLE users (
	id SERIAL NOT NULL, 
	wallet_address VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_users_id ON users (id);
CREATE UNIQUE INDEX ix_users_wallet_address ON users (wallet_address);
CREATE TYPE agentstatus AS ENUM ('active', 'suspended', 'killed', 'revoked');

CREATE TABLE agents (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	user_id INTEGER NOT NULL, 
	balance NUMERIC(20, 6), 
	total_spent NUMERIC(20, 6), 
	escrow_address VARCHAR, 
	status agentstatus, 
	violation_count INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE INDEX ix_agents_id ON agents (id);
CREATE INDEX ix_agents_name ON agents (name);

CREATE TABLE policies (
	id SERIAL NOT NULL, 
	agent_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	max_per_transaction NUMERIC(20, 6) NOT NULL, 
	max_per_day NUMERIC(20, 6) NOT NULL, 
	max_per_month NUMERIC(20, 6), 
	allowed_categories TEXT, 
	blocked_human_transfers BOOLEAN, 
	blocked_withdrawals BOOLEAN, 
	blocked_arbitrary_contracts BOOLEAN, 
	require_approval_above NUMERIC(20, 6), 
	allowed_recipient_addresses TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (agent_id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE INDEX ix_policies_id ON policies (id);
