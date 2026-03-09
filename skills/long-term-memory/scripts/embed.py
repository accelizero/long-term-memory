#!/usr/bin/env python3
"""Embedding module. Supports light (sentence-transformers) and standard (FlagEmbedding) profiles."""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import load_config

_model = None
_profile = None


def _load_model():
    global _model, _profile
    if _model is not None:
        return _model

    config = load_config()
    if not config:
        raise RuntimeError("No config found. Run setup first.")

    _profile = config.get("profile", "light")
    model_name = config.get("model_name", "BAAI/bge-small-zh-v1.5")

    if _profile == "light":
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
    elif _profile == "standard":
        from FlagEmbedding import BGEM3FlagModel
        _model = BGEM3FlagModel(model_name, use_fp16=False)
    else:
        raise ValueError(f"Unknown profile: {_profile}")

    return _model


def embed_text(text: str) -> list:
    """Embed a single text string. Returns list of floats."""
    model = _load_model()

    if _profile == "light":
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()
    elif _profile == "standard":
        result = model.encode([text])
        vec = result["dense_vecs"][0]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()
    else:
        raise ValueError(f"Unknown profile: {_profile}")


def embed_texts(texts: list) -> list:
    """Embed multiple texts. Returns list of list of floats."""
    model = _load_model()

    if _profile == "light":
        vecs = model.encode(texts, normalize_embeddings=True)
        return vecs.tolist()
    elif _profile == "standard":
        result = model.encode(texts)
        vecs = result["dense_vecs"]
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return (vecs / norms).tolist()
    else:
        raise ValueError(f"Unknown profile: {_profile}")


if __name__ == "__main__":
    import json
    text = sys.argv[1] if len(sys.argv) > 1 else "测试embedding"
    vec = embed_text(text)
    print(json.dumps({"dim": len(vec), "sample": vec[:5]}))
