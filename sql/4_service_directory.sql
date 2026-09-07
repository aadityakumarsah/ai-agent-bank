-- AI Agent Bank | 4_service_directory.sql | Postgres/Supabase

CREATE TYPE servicecategory AS ENUM ('api', 'compute', 'data', 'ai_model', 'storage', 'other_agent');
CREATE TYPE servicerisklevel AS ENUM ('low', 'medium', 'high');

CREATE TABLE service_directory (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	category servicecategory NOT NULL, 
	endpoint VARCHAR NOT NULL, 
	wallet_address VARCHAR NOT NULL, 
	price NUMERIC(20, 6) NOT NULL, 
	currency VARCHAR, 
	requires_payment BOOLEAN, 
	active BOOLEAN, 
	risk_level servicerisklevel, 
	is_demo BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_service_directory_id ON service_directory (id);
