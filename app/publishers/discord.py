import httpx

from app.publishers.base import PublisherError, PublishRequest, PublishResult, SocialPublisher


class DiscordPublisher(SocialPublisher):
    def __init__(self, webhook_url: str | None, timeout: float = 10):
        self.webhook_url = webhook_url
        self.timeout = timeout

    async def publish(self, request: PublishRequest) -> PublishResult:
        if not self.webhook_url:
            raise PublisherError("Discord publisher is not configured")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.webhook_url, params={"wait": "true"}, json={"content": request.content})
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PublisherError(f"Discord returned HTTP {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise PublisherError("Discord request failed") from exc
        payload = response.json()
        if "id" not in payload:
            raise PublisherError("Discord response did not contain a message ID")
        return PublishResult(external_post_id=str(payload["id"]))
