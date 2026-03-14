"""Conftest for indexing service tests."""

import sys
from unittest.mock import MagicMock

# Mock heavy dependencies that aren't needed for unit tests
for mod_name in [
    "torch",
    "torch.nn",
    "torch.nn.functional",
    "sentence_transformers",
    "elasticsearch",
    "elasticsearch.helpers",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()
