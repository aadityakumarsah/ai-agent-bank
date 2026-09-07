"""
Deterministic, rule-based transaction risk scoring.

This is NOT a machine-learning model and we do not pretend it is. It is a
transparent, additive scoring function over a small set of explicit,
human-readable rules. Every point a transaction receives can be explained by a
factor line in the response, so users can audit exactly why a risk score came out
the way it did.

Scoring inputs (all deterministic and derivable server-side):
    amount                transaction size relative to the policy budget
    recipient_known       recipient is whitelisted / a known provider
    merchant_known        recipient_address resolves to a known merchant
    category_allowed      the requested category is in the policy allow-list
    contract_allowed      the agent may interact with arbitrary contracts
    agent_age_hours       how long the agent has existed
    recent_spending       daily budget utilization (0-100%)
    velocity              active transactions in the last hour
    policy_violation_count  how many times the agent was blocked recently

Output: a score from 0-100 with a band:
    0-30   LOW
    31-70  MEDIUM
    71-100 HIGH
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class RiskFactor:
    name: str
    points: int
    detail: str = ""


@dataclass
class RiskResult:
    score: int
    level: str
    factors: List[RiskFactor] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "factors": [
                {"name": f.name, "points": f.points, "detail": f.detail}
                for f in self.factors
            ],
        }


class RiskEngine:
    """Deterministic rule-based transaction risk scoring (see module docstring)."""

    @staticmethod
    def _level(score: int) -> str:
        if score <= 30:
            return "low"
        if score <= 70:
            return "medium"
        return "high"

    def compute(
        self,
        *,
        amount: float,
        recipient_known: bool,
        merchant_known: bool,
        category_allowed: bool,
        contract_allowed: bool,
        agent_age_hours: float,
        daily_limit: float,
        spent_today: float,
        velocity: int,
        policy_violation_count: int,
    ) -> RiskResult:
        factors: List[RiskFactor] = []

        # --- Amount (max 35 pts) ---
        if amount <= 2:
            pts, detail = 0, "small amount (<= $2)"
        elif amount <= 20:
            pts, detail = 10, "moderate amount (<= $20)"
        elif amount <= 100:
            pts, detail = 25, "large amount (<= $100)"
        else:
            pts, detail = 35, "very large amount (> $100)"
        factors.append(RiskFactor("Amount", pts, detail))

        # --- Recipient trust (max 30 pts) ---
        if not recipient_known:
            factors.append(RiskFactor("Recipient trusted", 25, "recipient not whitelisted / unknown"))
        else:
            factors.append(RiskFactor("Recipient trusted", 0, "recipient is whitelisted"))
        if not merchant_known:
            factors.append(RiskFactor("Merchant known", 5, "no known merchant record"))
        else:
            factors.append(RiskFactor("Merchant known", 0, "known merchant"))

        # --- Category (max 15 pts) ---
        if not category_allowed:
            factors.append(RiskFactor("Category allowed", 15, "category is not in the policy allow-list"))
        else:
            factors.append(RiskFactor("Category allowed", 0, "category is allowed"))

        # --- Contract interaction (max 10 pts) ---
        if contract_allowed:
            factors.append(RiskFactor("Contract interaction", 0, "arbitrary contracts permitted"))
        else:
            factors.append(RiskFactor("Contract interaction", 10, "arbitrary contracts blocked"))

        # --- Agent age (max 15 pts) ---
        if agent_age_hours < 1:
            pts, detail = 15, "agent is younger than 1 hour"
        elif agent_age_hours < 24:
            pts, detail = 10, "agent is younger than 24 hours"
        elif agent_age_hours < 24 * 7:
            pts, detail = 5, "agent is younger than 7 days"
        else:
            pts, detail = 0, "agent is established"
        factors.append(RiskFactor("Agent age", pts, detail))

        # --- Recent spending / daily budget utilization (max 20 pts) ---
        if daily_limit > 0:
            utilization = min(100.0, (spent_today / daily_limit) * 100.0)
            if utilization < 50:
                pts, detail = 0, "daily budget utilization < 50%"
            elif utilization < 90:
                pts, detail = 10, "daily budget utilization < 90%"
            else:
                pts, detail = 20, "daily budget utilization >= 90%"
        else:
            pts, detail = 10, "no daily limit configured"
        factors.append(RiskFactor("Recent spending", pts, detail))

        # --- Velocity (max 15 pts) ---
        if velocity <= 2:
            pts, detail = 0, "low transaction velocity"
        elif velocity <= 5:
            pts, detail = 5, "moderate velocity"
        elif velocity <= 10:
            pts, detail = 10, "elevated velocity"
        else:
            pts, detail = 15, "very high velocity"
        factors.append(RiskFactor("Velocity", pts, detail))

        # --- Policy violation history (max 20 pts) ---
        if policy_violation_count <= 0:
            pts, detail = 0, "no policy violations"
        elif policy_violation_count == 1:
            pts, detail = 8, "1 prior policy violation"
        elif policy_violation_count <= 3:
            pts, detail = 14, "repeated policy violations"
        else:
            pts, detail = 20, "persistent policy violations"
        factors.append(RiskFactor("Violation history", pts, detail))

        score = max(0, min(100, sum(f.points for f in factors)))
        return RiskResult(score=score, level=self._level(score), factors=factors)


risk_engine = RiskEngine()