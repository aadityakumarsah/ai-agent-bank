from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    @abstractmethod
    def generate(
        self, prompt: str, tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        Returns a dictionary with:
          - text: the generated text
          - tool_calls: list of tool calls (if any)
        """
        pass

    @abstractmethod
    def stream(self, prompt: str, tools: List[Dict[str, Any]] = None):
        """
        Stream the response from the LLM.
        Yields chunks of text.
        """
        pass


class DemoAIProvider(AIProvider):
    """
    A demo AI provider that simulates predictable responses for hackathon demo.
    It does not require an API key and returns hardcoded responses based on the prompt.
    """

    def __init__(self):
        self.call_count = 0

    def generate(
        self, prompt: str, tools: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        logger.info(f"DemoAIProvider generating for prompt: {prompt}")
        self.call_count += 1

        # Simulate a simple agent that can search, request payment, and complete task.
        if "research" in prompt.lower() or "best solana rpc" in prompt.lower():
            # First, we simulate a search for RPC providers.
            if self.call_count == 1:
                return {
                    "text": "I will search for Solana RPC providers.",
                    "tool_calls": [
                        {
                            "name": "search",
                            "arguments": {"query": "best Solana RPC provider"},
                        }
                    ],
                }
            # After search, we simulate getting results and then choosing one.
            elif self.call_count == 2:
                return {
                    "text": "I found a promising RPC provider: 'FastRPC'. I will now request payment to access their API.",
                    "tool_calls": [
                        {
                            "name": "request_payment",
                            "arguments": {
                                "amount": 0.02,
                                "currency": "USDC",
                                "recipient": "FastRPC_wallet_address_placeholder",
                                "category": "API",
                                "reason": "Paid for API access to FastRPC",
                                "metadata": {"provider": "FastRPC"},
                            },
                        }
                    ],
                }
            # After payment, we simulate fetching the API and then completing the task.
            elif self.call_count == 3:
                return {
                    "text": "I have accessed the FastRPC API and gathered the necessary information. The task is complete.",
                    "tool_calls": [
                        {
                            "name": "complete_task",
                            "arguments": {
                                "result": "The best Solana RPC provider is FastRPC due to its low latency and high uptime."
                            },
                        }
                    ],
                }
            else:
                # Fallback
                return {
                    "text": "I am not sure how to proceed. I will complete the task.",
                    "tool_calls": [
                        {
                            "name": "complete_task",
                            "arguments": {"result": "Task completed via demo agent."},
                        }
                    ],
                }

        elif "send $300" in prompt.lower() or "transfer 300" in prompt.lower():
            # This should trigger a payment request that will be denied by the policy engine.
            return {
                "text": "I will attempt to send $300 USDC to the specified wallet.",
                "tool_calls": [
                    {
                        "name": "request_payment",
                        "arguments": {
                            "amount": 300,
                            "currency": "USDC",
                            "recipient": "unknown_wallet_address",
                            "category": "human_transfer",
                            "reason": "Transfer to unknown wallet",
                            "metadata": {},
                        },
                    }
                ],
            }

        else:
            # Default response for any other prompt: we'll just complete the task with a generic result.
            return {
                "text": "I will complete the task as requested.",
                "tool_calls": [
                    {
                        "name": "complete_task",
                        "arguments": {"result": "Task completed via demo agent."},
                    }
                ],
            }

    def stream(self, prompt: str, tools: List[Dict[str, Any]] = None):
        # For demo, we just yield the entire response as one chunk.
        # In a real implementation, we would yield chunks.
        response = self.generate(prompt, tools)
        yield json.dumps(response)


# Factory to get the AI provider
def get_ai_provider() -> AIProvider:
    # Check if we have API keys for real providers; if not, use demo.
    # We'll check for OpenAI API key as an example.
    import os

    if os.getenv("OPENAI_API_KEY"):
        # TODO: Implement OpenAIProvider
        # For now, fall back to demo if not implemented.
        logger.warning(
            "OPENAI_API_KEY is set but OpenAIProvider not implemented. Falling back to demo."
        )
        return DemoAIProvider()
    elif os.getenv("ANTHROPIC_API_KEY"):
        # TODO: Implement AnthropicProvider
        logger.warning(
            "ANTHROPIC_API_KEY is set but AnthropicProvider not implemented. Falling back to demo."
        )
        return DemoAIProvider()
    elif os.getenv("GOOGLE_AI_API_KEY"):
        # TODO: Implement GoogleProvider
        logger.warning(
            "GOOGLE_AI_API_KEY is set but GoogleProvider not implemented. Falling back to demo."
        )
        return DemoAIProvider()
    else:
        logger.info("No AI API keys found. Using DemoAIProvider.")
        return DemoAIProvider()


# Singleton instance
ai_provider = get_ai_provider()
