"""Starting settings for our local embedding experiments."""

# Pretrained model to load when we implement embeddings.py.
EMBEDDING_MODEL = "intfloat/e5-small-v2"

# This model produces 384 numbers for each text input.
EMBEDDING_DIMENSIONS = 384

# Process up to 16 texts together; lower this if memory usage is too high.
EMBEDDING_BATCH_SIZE = 16

# Keep each vector's length at one for cosine-similarity comparisons.
NORMALIZE_EMBEDDINGS = True

# Start on CPU so the experiment works without GPU configuration.
EMBEDDING_DEVICE = "cpu"

# E5 expects these prefixes to distinguish queries from document passages.
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "

# Pin the downloaded model revision for reproducible embeddings.
EMBEDDING_REVISION = "ffb93f3bd4047442299a41ebb6fa998a38507c52"
CHUNKING_VERSION = "sentence-overlap-v1"
