"""Shared argparse helpers for the evaluation scripts."""
import argparse

import _bootstrap  # noqa: F401
from car_rental_sql.config import CACHE_DIR
from car_rental_sql.llm import PROVIDER_PRESETS, CachedLLM, LLMError, create_llm


def add_llm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default="anthropic", choices=list(PROVIDER_PRESETS))
    parser.add_argument("--model", default=None, help="Model name (defaults to the provider preset).")
    parser.add_argument("--base-url", default=None, help="Override the API base URL (OpenAI-compatible providers).")
    parser.add_argument("--no-cache", action="store_true", help="Disable the on-disk LLM response cache.")


def build_llm(args, model=None):
    try:
        llm = create_llm(args.provider, model or args.model, base_url=args.base_url)
    except LLMError as exc:
        raise SystemExit(f"Error: {exc}")
    if args.no_cache:
        return llm
    safe = llm.name.replace(":", "_").replace("/", "_")
    return CachedLLM(llm, CACHE_DIR / f"{safe}.json")
