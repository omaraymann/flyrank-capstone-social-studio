from rag.config import PASSAGE_PREFIX
import re

def prepare_passage(text: str, title: str | None = None) -> str:
    """Combine an optional title with passage text."""
    text = text.strip()
    title = title.strip() if title else ""

    if title:
        return f"{title}\n{text}"

    return text

def count_passage_tokens(text: str, tokenizer) -> int:
    """Count tokens without truncating the input."""
    tokens = tokenizer(
        PASSAGE_PREFIX + text,
        truncation=False,
        add_special_tokens=True,
        verbose=False,
    )["input_ids"]

    return len(tokens)

def split_into_sentences(text: str) -> list[str]:
    """Split text at basic sentence boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]

def split_oversized_sentence(sentence: str, tokenizer, max_tokens: int, title: str | None = None,) -> list[str]:
    """Split a long sentence at whitespace within the token budget."""
    if max_tokens < 1:
        raise ValueError("max_tokens must be positive")

    words = sentence.split()
    if not words:
        return []

    fragments = []
    current_words = []

    for word in words:
        candidate = " ".join(current_words + [word])
        passage = prepare_passage(candidate, title)

        if count_passage_tokens(passage, tokenizer) <= max_tokens:
            current_words.append(word)
            continue

        if current_words:
            fragments.append(" ".join(current_words))
            current_words = []

        # Check that this word fits by itself.
        passage = prepare_passage(word, title)
        if count_passage_tokens(passage, tokenizer) > max_tokens:
            raise ValueError(
                "A single word cannot fit with the title, prefix, "
                "and special tokens. Shorten the title or add "
                "a token-level fallback."
            )

        current_words = [word]

    if current_words:
        fragments.append(" ".join(current_words))

    return fragments

def chunk_document(text: str, tokenizer, max_tokens: int, title: str | None = None,) -> list[str]:
    """Create passages that fit within the embedding token limit."""
    if max_tokens < 1:
        raise ValueError("max_tokens must be positive")

    if not text.strip():
        return []

    passage = prepare_passage(text, title)

    if count_passage_tokens(passage, tokenizer) <= max_tokens:
        return [passage]

    sentences = []

    for sentence in split_into_sentences(text):
        single_passage = prepare_passage(sentence, title)

        if count_passage_tokens(single_passage, tokenizer) <= max_tokens:
            sentences.append(sentence)
        else:
            sentences.extend(
                split_oversized_sentence(
                    sentence=sentence,
                    tokenizer=tokenizer,
                    max_tokens=max_tokens,
                    title=title,
                )
            )

    chunks = []
    current_sentences = []

    for sentence in sentences:
        # A single sentence must fit with the title and prefix.
        single_passage = prepare_passage(sentence, title)
        if count_passage_tokens(single_passage, tokenizer) > max_tokens:
            raise ValueError(
                "A single sentence exceeds the token limit; "
                "we need a smaller-text fallback."
            )

        candidate_sentences = current_sentences + [sentence]
        candidate_passage = prepare_passage(" ".join(candidate_sentences), title)

        if count_passage_tokens(candidate_passage, tokenizer) <= max_tokens:
            current_sentences = candidate_sentences
            continue

        # The candidate is too large: save the existing group.
        chunks.append(prepare_passage(" ".join(current_sentences), title))

        # Carry the previous sentence over when both sentences fit.
        overlap_sentences = [current_sentences[-1], sentence]
        overlap_passage = prepare_passage(" ".join(overlap_sentences), title)

        if count_passage_tokens(overlap_passage, tokenizer) <= max_tokens:
            current_sentences = overlap_sentences
        else:
            current_sentences = [sentence]

    # Save the final group.
    if current_sentences:
        chunks.append(
            prepare_passage(" ".join(current_sentences), title)
        )

    return chunks