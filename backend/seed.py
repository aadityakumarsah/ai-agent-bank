#!/usr/bin/env python3
"""
Seed script to create demo data for AI Agent Bank.
Run this script to create a demo user, agent, and policy.
"""

import sys
import os

# Add the backend directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_db, engine
from app.db.models import User, Agent, Policy, AgentStatus, Base
from sqlalchemy.orm import Session


def seed_demo_data():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db: Session = next(get_db())

    # Create a demo user if not exists
    demo_user_wallet = "demo_user_wallet_address_placeholder"
    user = db.query(User).filter(User.wallet_address == demo_user_wallet).first()
    if not user:
        user = User(wallet_address=demo_user_wallet)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created demo user: {user.id}")
    else:
        print(f"Demo user already exists: {user.id}")

    # Create a demo agent if not exists
    demo_agent_name = "DemoAgent"
    agent = (
        db.query(Agent)
        .filter(Agent.name == demo_agent_name, Agent.user_id == user.id)
        .first()
    )
    if not agent:
        agent = Agent(
            name=demo_agent_name,
            description="A demo agent for testing",
            user_id=user.id,
            status=AgentStatus.active,
            wallet_address="demo_agent_wallet_address_placeholder",
            balance=1000.0,  # 1000 USDC
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        print(f"Created demo agent: {agent.id}")
    else:
        print(f"Demo agent already exists: {agent.id}")

    # Create a default policy for the agent if not exists
    policy = db.query(Policy).filter(Policy.agent_id == agent.id).first()
    if not policy:
        policy = Policy(
            agent_id=agent.id,
            user_id=user.id,
            max_per_transaction=20.0,  # $20 per transaction
            max_per_day=100.0,  # $100 per day
            allowed_categories='["api", "compute", "data", "agent"]',
            blocked_human_transfers=True,
            blocked_withdrawals=True,
            blocked_arbitrary_contracts=True,
            require_approval_above=20.0,  # Require approval for transactions above $20
            allowed_recipient_addresses="[]",  # Empty allowlist for now
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        print(f"Created demo policy: {policy.id}")
    else:
        print(f"Demo policy already exists: {policy.id}")

    print("Seeding completed.")


if __name__ == "__main__":
    seed_demo_data()
