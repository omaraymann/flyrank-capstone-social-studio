from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformProfile:
    max_characters: int
    max_hashtags: int
    tone: str
    forbidden_tone_terms: tuple[str, ...]


PROFILES = {
    "x": PlatformProfile(max_characters=280, max_hashtags=3, tone="concise", forbidden_tone_terms=()),
    "linkedin": PlatformProfile(
        max_characters=3000,
        max_hashtags=5,
        tone="professional",
        forbidden_tone_terms=(" lol ", " omg ", " lmao "),
    ),
}


def validate_variant(platform: str, content: str):
    profile = PROFILES[platform]
    errors = []
    if len(content) > profile.max_characters:
        errors.append(f"content exceeds {profile.max_characters} characters")
    hashtag_count = sum(1 for word in content.split() if word.startswith("#") and len(word) > 1)
    if hashtag_count > profile.max_hashtags:
        errors.append(f"content exceeds {profile.max_hashtags} hashtags")
    if not content.strip():
        errors.append("content cannot be empty")
    padded_content = f" {content.lower()} "
    if any(term in padded_content for term in profile.forbidden_tone_terms):
        errors.append(f"content breaks the {profile.tone} tone rule")
    if errors:
        raise ValueError("; ".join(errors))


def generate_variant(platform: str, title: str, source: str, source_url: str | None) -> str:
    summary = " ".join(source.split())[:170]
    link = f"\n\nRead more: {source_url}" if source_url else ""
    if platform == "x":
        suffix = f" {source_url}" if source_url else ""
        available = 280 - len(suffix) - len(" — ")
        content = f"{title} — {summary[:max(20, available - len(title))]}{suffix}"
        return content[:280]
    return f"{title}\n\n{summary}{link}\n\n#Insights #SocialMedia"
