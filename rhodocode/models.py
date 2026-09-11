"""Model catalog — mirrors the Rhododendron web app's cloud model list."""

from typing import Dict, List

TIER_RANK: Dict[str, int] = {"free": 0, "pro": 1, "max": 2}

MODELS: List[Dict] = [
    # free
    {"id": "deepseek-ai/deepseek-v4-flash-0731", "label": "DeepSeek V4 Flash", "tier": "free",
     "reasoning": True, "efforts": ["low", "high"], "blurb": "Fast reasoning chain, high effort."},
    {"id": "openai/gpt-oss-120b", "label": "GPT-OSS 120B", "tier": "free",
     "reasoning": True, "blurb": "Open-weight generalist."},
    {"id": "mistralai/mistral-nemotron", "label": "Mistral Nemotron", "tier": "free",
     "blurb": "Compact and obedient."},
    {"id": "meta/llama-3.2-90b-vision-instruct", "label": "Llama 3.2 90B Vision", "tier": "free",
     "vision": True, "blurb": "Sees images."},
    # pro
    {"id": "minimaxai/minimax-m3", "label": "MiniMax M3", "tier": "pro",
     "blurb": "Strong multilingual generalist."},
    {"id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "label": "Nemotron Nano Omni", "tier": "pro",
     "vision": True, "reasoning": True, "blurb": "Omni-modal reasoning."},
    {"id": "deepseek-ai/deepseek-v4-pro-0813", "label": "DeepSeek V4 Pro", "tier": "pro",
     "blurb": "Huge context, no fluff."},
    # max
    {"id": "nvidia/nemotron-3-ultra-550b-a55b", "label": "Nemotron 3 Ultra", "tier": "max",
     "reasoning": True, "blurb": "550B flagship reasoning."},
    {"id": "poolside/laguna-xs-2.1", "label": "Laguna XS 2.1", "tier": "max",
     "blurb": "Code-native specialist."},
    {"id": "moonshotai/kimi-k3", "label": "Kimi K3", "tier": "max",
     "vision": True, "reasoning": True, "efforts": ["low", "medium", "high", "max"],
     "blurb": "Max-effort reasoning."},
]

DEFAULT_MODEL = "deepseek-ai/deepseek-v4-flash-0731"


def find(model_id: str) -> Dict | None:
    for m in MODELS:
        if m["id"] == model_id:
            return m
    return None
