"""Versioned, local-only normalization contract; deliberately not an ingest hook.

Input is a staging envelope: domain, source_key, source_version, record_id,
content_sha256 and payload (the exact staged JSON object). Provenance is an
optional object. run_rules never means reviewed or gold. Every recipe/menu must
have an actual item-level second-pass review; batch transport changes neither
that requirement nor source custody. No external services are called here.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from ingest_api import DOMAINS

SCHEMA_VERSION = 'offmenu.common-normalized-record/1'
TEMPLATE_VERSION = 'offmenu.common-template/1'
RULE_VERSION = 'offmenu.normalization-rules/1'
RECORD_TYPES = {'barcodes': ('barcode',), 'ingredients': ('ingredient',),
                'recipes': ('recipe', 'menu'), 'dietary': ('dietary_assertion',),
                'user_profiles': ('profile',), 'inventory': ('inventory',),
                'suppliers': ('supplier',), 'citations': ('citation',)}
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 100000
MAX_ITEMS = 10000


@dataclass(frozen=True)
class Versions:
    rule_version: str = RULE_VERSION
    template_version: str = TEMPLATE_VERSION
    schema_version: str = SCHEMA_VERSION
    # Explicit unconfigured values prevent accidental promotion before selection.
    model_version: str = 'unconfigured'
    prompt_version: str = 'unconfigured'

    def as_dict(self):
        result = asdict(self)
        if any(not isinstance(value, str) or not value.strip() or len(value) > 256
               for value in result.values()):
            raise ValueError('invalid_version')
        return result


class NormalizationError(ValueError):
    """Input/output fails the bounded, non-executable normalization contract."""


def run_rules(record, versions=None, store=None):
    from normalization_core import run_rules as implementation
    return implementation(record, versions=versions, store=store)


def queue_review(artifact, store=None):
    from normalization_core import queue_review as implementation
    return implementation(artifact, store=store)


def validate_and_cache_actual_review(artifact, review, store=None, *, cache_result=True):
    from normalization_core import validate_and_cache_actual_review as implementation
    return implementation(artifact, review, store=store, cache_result=cache_result)
