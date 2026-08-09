from app.rag.chunker import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_one_chunk():
    text = "A short paragraph."
    assert chunk_text(text) == [text]


def test_long_text_is_split_into_multiple_overlapping_chunks():
    text = "a" * 5000
    chunks = chunk_text(text, chunk_size=2000, overlap=200)
    assert len(chunks) == 3
    for chunk in chunks[:-1]:
        assert len(chunk) == 2000
    # consecutive chunks share the overlap region
    assert chunks[0][-200:] == chunks[1][:200]


def test_chunking_covers_the_entire_text_with_no_gaps():
    text = "".join(str(i % 10) for i in range(3000))
    chunk_size, overlap = 1000, 100
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    expected = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        expected.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    assert chunks == expected
