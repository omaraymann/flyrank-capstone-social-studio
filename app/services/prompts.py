from app.services.variants import PROFILES

PROMPT_VERSION = "social-v1"
EXAMPLES_VERSION = "few-shot-v1"

EXAMPLES = {
    "x": "Quick take: Reliable pipelines recover safely instead of silently losing work. #DataEngineering",
    "linkedin": (
        "Reliable data pipelines are designed for recovery.\n\n"
        "Three useful practices:\n- Persist work before execution\n- Make retries safe\n- Keep an audit trail\n\n"
        "How does your team handle failed jobs? #DataEngineering"
    ),
    "discord": (
        "**New engineering guide**\n\nWe broke down how durable workers prevent lost and duplicate jobs. "
        "Take a look and tell us how your team handles retries."
    ),
}


def system_prompt(platforms: list[str]) -> str:
    rules = "\n".join(
        f"- {platform}: maximum {PROFILES[platform].max_characters} characters and "
        f"{PROFILES[platform].max_hashtags} hashtags; use a {PROFILES[platform].tone} style."
        for platform in platforms
    )
    examples = "\n\n".join(f"Good {platform} example:\n{EXAMPLES[platform]}" for platform in platforms)
    return (
        "You create accurate social posts from supplied source content. Never invent facts. "
        "Every draft must include the user's call to action verbatim. "
        "Return only the requested JSON fields. Make each platform draft meaningfully different.\n\n"
        f"Platform rules:\n{rules}\n\nFew-shot examples ({EXAMPLES_VERSION}):\n{examples}"
    )


def generation_prompt(*, title, content, source_url, audience, goal, tone, call_to_action, platforms) -> str:
    return (
        f"Create drafts for: {', '.join(platforms)}\n"
        f"Audience: {audience}\nGoal: {goal}\nTone: {tone}\nCall to action: {call_to_action}\n"
        f"Source URL: {source_url or 'none'}\nTitle: {title}\nSource content:\n{content}"
    )


def repair_prompt(*, platform: str, content: str, errors: str) -> str:
    return (
        f"Repair this {platform} draft. Preserve its facts and call to action. Fix only the listed "
        f"validation errors and return the single requested JSON field.\nErrors: {errors}\nDraft:\n{content}"
    )
