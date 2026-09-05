from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PublishRequest:
    content: str
    idempotency_key: str


@dataclass(frozen=True)
class PublishResult:
    external_post_id: str
    external_url: str | None = None


class PublisherError(RuntimeError):
    """A safe, user-facing publisher failure that contains no credentials."""


class SocialPublisher(ABC):
    @abstractmethod
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish one post or return the result of the same prior operation."""
