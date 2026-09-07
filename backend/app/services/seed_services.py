"""
Seeds the service directory with demo marketplace listings.

These are clearly labelled as DEMO SERVICE — they represent a conceptual
marketplace and never return real payable endpoint responses.
"""

from decimal import Decimal

from app.db.models import (
    ServiceDirectory,
    ServiceCategory,
    ServiceRiskLevel,
)

# (name, description, category, endpoint, wallet, price, risk)
DEMO_SERVICES = [
    (
        "Solana RPC API",
        "High-throughput Solana RPC provider. Query accounts, blocks and transactions for agent workloads.",
        ServiceCategory.compute,
        "/v1/rpc",
        "rpcProvider",
        "0.02",
        ServiceRiskLevel.low,
    ),
    (
        "Web Search API",
        "General web search and knowledge retrieval for autonomous research tasks.",
        ServiceCategory.api,
        "/v1/search",
        "apiProvider",
        "0.05",
        ServiceRiskLevel.low,
    ),
    (
        "Premium Data API",
        "Aggregated market data, on-chain analytics and token pricing feeds.",
        ServiceCategory.data,
        "/v1/market-data",
        "dataProvider",
        "50.00",
        ServiceRiskLevel.high,
    ),
    (
        "Image Generation API",
        "Request image generation and multimodal asset rendering.",
        ServiceCategory.ai_model,
        "/v1/generate",
        "apiProvider",
        "0.10",
        ServiceRiskLevel.medium,
    ),
    (
        "Compute Provider",
        "Rent ephemeral compute for heavy batch processing and parallel jobs.",
        ServiceCategory.compute,
        "/v1/compute",
        "computeProvider",
        "0.40",
        ServiceRiskLevel.medium,
    ),
    (
        "Vector Storage",
        "Pay-per-use vector database for embeddings and long-term agent memory.",
        ServiceCategory.storage,
        "/v1/vector",
        "storageProvider",
        "0.03",
        ServiceRiskLevel.low,
    ),
    (
        "Peer Agent Service",
        "Pay another AI agent to run a subtask on your behalf.",
        ServiceCategory.other_agent,
        "/v1/agent-run",
        "agentPeer",
        "0.25",
        ServiceRiskLevel.medium,
    ),
]


def seed_service_directory(db) -> int:
    """Insert the demo services if the directory is empty. Returns count created."""
    if db.query(ServiceDirectory).count() > 0:
        return 0

    count = 0
    for name, description, category, endpoint, wallet, price, risk in DEMO_SERVICES:
        db.add(
            ServiceDirectory(
                name=name,
                description=description,
                category=category,
                endpoint=endpoint,
                wallet_address=wallet,
                price=Decimal(price),
                currency="USDC",
                requires_payment=True,
                active=True,
                risk_level=risk,
                is_demo=True,
            )
        )
        count += 1
    db.commit()
    return count
