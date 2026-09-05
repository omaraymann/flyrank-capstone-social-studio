from app.config import settings
from app.publishers.base import SocialPublisher
from app.publishers.discord import DiscordPublisher
from app.publishers.mock import MockLinkedInPublisher, MockXPublisher


class PublisherRegistry:
    def __init__(self, publishers: dict[str, SocialPublisher]):
        self._publishers = publishers

    def get(self, platform: str) -> SocialPublisher:
        publisher = self._publishers.get(platform)
        if not publisher:
            raise LookupError(f"No publisher configured for {platform}")
        return publisher


publisher_registry = PublisherRegistry(
    {
        "x": MockXPublisher(),
        "linkedin": MockLinkedInPublisher(),
        "discord": DiscordPublisher(settings.discord_webhook_url),
    }
)


def get_publisher_registry() -> PublisherRegistry:
    return publisher_registry
