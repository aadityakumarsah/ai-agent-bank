-- AI Agent Bank | 3_task_runs_audit_logs.sql | Postgres/Supabase


CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	agent_id INTEGER, 
	event VARCHAR(64) NOT NULL, 
	actor VARCHAR(32), 
	detail TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
)

;
CREATE INDEX ix_audit_logs_id ON audit_logs (id);
CREATE INDEX ix_audit_logs_event ON audit_logs (event);

CREATE TABLE task_runs (
	id SERIAL NOT NULL, 
	agent_id INTEGER NOT NULL, 
	task_prompt TEXT NOT NULL, 
	status VARCHAR, 
	result TEXT, 
	error TEXT, 
	steps TEXT, 
	memory TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(agent_id) REFERENCES agents (id)
)

;
CREATE INDEX ix_task_runs_id ON task_runs (id);
