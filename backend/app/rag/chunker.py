"""Splits raw document text into overlapping chunks for embedding. The
knowledge-base UI's own copy says "chunk ~500 tok · overlap 50" — this
approximates tokens as ~4 characters (a common rule of thumb for English
prose), so the defaults below are chosen to land near that target without
pulling in a real tokenizer dependency for something that's inherently an
approximation anyway."""

_CHARS_PER_CHUNK = 2000  # ~500 tokens
_CHARS_OVERLAP = 200  # ~50 tokens


def chunk_text(
    text: str, *, chunk_size: int = _CHARS_PER_CHUNK, overlap: int = _CHARS_OVERLAP
) -> list[str]:
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]
