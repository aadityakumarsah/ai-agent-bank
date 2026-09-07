import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TrustRegistry:
    """
    Registry of known trusted recipients (merchants, service providers, agents).

    In a production system this maps a recipient's Solana address to metadata about
    what category they belong to and whether their public key has been verified.
    For the demo, we ship a small set of built-in demo providers so the policy
    engine can demonstrate whitelisted vs. blocked recipients.
    """

    BUILTIN = {
        "rpcProvider": {
            "name": "RPC Compute Provider",
            "category": "compute",
            "trusted": True,
            "description": "Rent Solana RPC compute from a known provider",
        },
        "apiProvider": {
            "name": "API Provider",
            "category": "api",
            "trusted": True,
            "description": "Pay for approved API access",
        },
        "dataProvider": {
            "name": "Data Provider",
            "category": "data",
            "trusted": True,
            "description": "Purchase market/pricing data",
        },
        "agentPeer": {
            "name": "Peer Agent",
            "category": "agent",
            "trusted": True,
            "description": "Pay another approved AI agent",
        },
        "unknownWallet": {
            "name": "Unknown Human Wallet",
            "category": "human",
            "trusted": False,
            "description": "An arbitrary, unverified wallet address",
        },
    }

    def __init__(self):
        self.providers: Dict[str, Dict[str, Any]] = dict(self.BUILTIN)

    def register(self, address: str, name: str, category: str) -> None:
        self.providers[address] = {
            "name": name,
            "category": category,
            "trusted": True,
        }

    def lookup(self, address: str) -> Dict[str, Any]:
        """Return metadata for a recipient, or a default 'unknown' entry."""
        if address in self.providers:
            return self.providers[address]
        return {
            "name": address,
            "category": "human",
            "trusted": False,
            "description": "Unknown / unregistered recipient",
        }

    def is_trusted(self, address: str) -> bool:
        entry = self.lookup(address)
        return bool(entry.get("trusted"))


trust_registry = TrustRegistry()
