"""Natural-language inference (premise = retrieved chunk, hypothesis = answer sentence).

Model: cross-encoder/nli-deberta-v3-xsmall exported to ONNX (Xenova/nli-deberta-v3-xsmall,
quantized, ~87 MB), run with onnxruntime on CPU. If the model cannot be loaded the validator reports
"entailment NOT CHECKED" instead of pretending a check happened.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np

NLI_REPO = "Xenova/nli-deberta-v3-xsmall"
NLI_FILE = "onnx/model_quantized.onnx"
MAX_TOKENS = 512


@dataclass(frozen=True)
class NliResult:
    entailment: float
    neutral: float
    contradiction: float

    @property
    def label(self) -> str:
        best = max(
            ("entailment", self.entailment),
            ("neutral", self.neutral),
            ("contradiction", self.contradiction),
            key=lambda kv: kv[1],
        )
        return best[0]


class NliModel:
    def __init__(self) -> None:
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        from ignis.settings import get_settings

        cache = str(get_settings().models_dir)
        model_path = hf_hub_download(NLI_REPO, NLI_FILE, cache_dir=cache)
        tok_path = hf_hub_download(NLI_REPO, "tokenizer.json", cache_dir=cache)
        cfg_path = hf_hub_download(NLI_REPO, "config.json", cache_dir=cache)
        self.tokenizer = Tokenizer.from_file(tok_path)
        self.tokenizer.enable_truncation(max_length=MAX_TOKENS, strategy="only_first")
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}
        with open(cfg_path, encoding="utf-8") as fh:
            cfg: dict[str, Any] = json.load(fh)
        self.id2label = {int(k): v.lower() for k, v in cfg["id2label"].items()}

    def predict(self, premise: str, hypothesis: str) -> NliResult:
        enc = self.tokenizer.encode(premise, hypothesis)
        feeds: dict[str, np.ndarray] = {
            "input_ids": np.array([enc.ids], dtype=np.int64),
            "attention_mask": np.array([enc.attention_mask], dtype=np.int64),
        }
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.array([enc.type_ids], dtype=np.int64)
        logits = self.session.run(None, feeds)[0][0]
        p = np.exp(logits - logits.max())
        p /= p.sum()
        probs = {self.id2label[i]: float(p[i]) for i in range(len(p))}
        return NliResult(probs.get("entailment", 0.0), probs.get("neutral", 0.0), probs.get("contradiction", 0.0))


@lru_cache(maxsize=1)
def get_nli() -> NliModel | None:
    try:
        return NliModel()
    except Exception:
        return None
