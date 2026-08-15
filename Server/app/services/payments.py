import uuid
from typing import Protocol


class PaymentError(Exception):
    """Charge declined or failed. Router maps to 402; the checkout transaction
    rolls back, so no order row survives a failed payment."""


class PaymentProvider(Protocol):
    def charge(self, *, user_id: int, order_id: int, amount_cents: int) -> str: ...


class MockProvider:
    def charge(self, *, user_id: int, order_id: int, amount_cents: int) -> str:
        return f"mock_{uuid.uuid4().hex}"


def get_provider() -> PaymentProvider:
    # Stripe lands here as a new class behind the same Protocol (DESIGN §8).
    return MockProvider()
