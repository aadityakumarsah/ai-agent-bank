-- AI Agent Bank | 5_user_api_keys.sql | Postgres/Supabase


CREATE TABLE user_api_keys (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	provider VARCHAR(16) NOT NULL, 
	encrypted_key TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE INDEX ix_user_api_keys_id ON user_api_keys (id);
