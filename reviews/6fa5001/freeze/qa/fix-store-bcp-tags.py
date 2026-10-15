#!/usr/bin/env python3
"""
NON-AUTHORITATIVE HISTORICAL REFERENCE — DO NOT EXECUTE AGAINST THE CANDIDATE LANE.

This script CANNOT reproduce the candidate extraction byte-semantics (it drops region
tokens like 'Australia'/'Canada' from parenthesized captions and emits rows lacking
canonicalBcp47/evidenceKind/rowsCount fields the candidate carries). Running it with
its default DEST would destructively overwrite the authoritative candidate file
qa/store-locale-bcp47-extraction.json with a lossy incompatible variant.

The authoritative parsed output is store-locale-bcp47-extraction.json (and its qa/
copy), rebuilt from store-language-locale-inventory.json. This script is retained
only as provenance for the historical parsing bug it documents.

D5 guard (2026-10-15): main() refuses to run unless FIX_STORE_BCP_TAGS_ALLOW=1 is
set in the environment, and refuses any DEST inside the candidate lane unless
FIX_STORE_BCP_TAGS_ALLOW_LANE_OVERWRITE=1 is also set. See qa/test_terminology_qa.py
regressions (guard defaults declared below are asserted by QA).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SNAP_PATH = Path(
    "/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/language-terminology"
    "/app-store-locale-snapshot.json"
)
DEST = Path(__file__).resolve().parent / "store-locale-bcp47-extraction.json"

# D5 guard defaults — asserted by qa/test_terminology_qa.py. QA never sets these.
ALLOW_ENV = "FIX_STORE_BCP_TAGS_ALLOW"
LANE_OVERWRITE_ENV = "FIX_STORE_BCP_TAGS_ALLOW_LANE_OVERWRITE"
CANDIDATE_LANE_ROOT = Path(
    "/home/user/src/offmenu-data/freebuff-parallel-20261015/country-coverage/language-terminology"
)

BASE_LANGUAGE_FROM_CAPTION: dict[str, str] = {
    "Afrikaans": "af",
    "Albanian": "sq",
    "Amharic": "am",
    "Arabic": "ar",
    "Armenian": "hy",
    "Azerbaijani": "az",
    "Bangla": "bn",
    "Basque": "eu",
    "Belarusian": "be",
    "Bulgarian": "bg",
    "Burmese": "my",
    "Catalan": "ca",
    "Chinese": "zh",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "English": "en",
    "Estonian": "et",
    "Filipino": "fil",
    "Finnish": "fi",
    "French": "fr",
    "Galician": "gl",
    "Georgian": "ka",
    "German": "de",
    "Greek": "el",
    "Gujarati": "gu",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Icelandic": "is",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Kannada": "kn",
    "Kazakh": "kk",
    "Khmer": "km",
    "Korean": "ko",
    "Kyrgyz": "ky",
    "Lao": "lo",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Macedonian": "mk",
    "Malay": "ms",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Mongolian": "mn",
    "Nepali": "ne",
    "Norwegian": "no",
    "Persian": "fa",
    "Polish": "pl",
    "Portuguese": "pt",
    "Punjabi": "pa",
    "Romanian": "ro",
    "Romansh": "rm",
    "Russian": "ru",
    "Serbian": "sr",
    "Sinhala": "si",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swahili": "sw",
    "Swedish": "sv",
    "Tamil": "ta",
    "Telugu": "te",
    "Thai": "th",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Urdu": "ur",
    "Vietnamese": "vi",
    "Odia": "or",
}

DASH = "\u2013"  # en dash
DASH2 = "\u2014"  # em dash
def is_bcp47_base(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]{2,3}", value))

def is_bcp47_tag(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]{2,3}-[A-Za-z0-9]{1,8}", value))

def normalize_region_token(token: str) -> str | None:
    t = token.strip()
    if not t:
        return None
    if re.fullmatch(r"[A-Za-z]{2,8}", t):
        return t
    t2 = t.rstrip(".")
    if re.fullmatch(r"[A-Za-z]{2,8}", t2):
        return t2
    return None

def guess_base_language_caption(name: str) -> str | None:
    nl = name.strip().lower()
    for caption, tag in BASE_LANGUAGE_FROM_CAPTION.items():
        cl = caption.lower()
        if nl == cl or nl.startswith(cl + " ") or nl.startswith(cl + "-") or nl.startswith(cl + "_"):
            return tag
    return None

def drop_parens_caption(chunk: str):
    """If chunk ends with a parenthesized region like 'English (Australia) - en-AU',
    split into caption and region. Otherwise return caption.
    """
    # Look for last '- ' preceded by a parenthesized region
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*-\s*([A-Za-z0-9\-]+)\s*$", chunk)
    if m:
        return m.group(1).strip(), normalize_region_token(m.group(2)) or m.group(2).strip(), m.group(3).strip()
    return chunk.strip(), None, None

def google_parse_one(chunk: str):
    caption, region, explicit = drop_parens_caption(chunk)
    if not caption:
        return None
    # Explicit BCP tag
    if explicit and is_bcp47_tag(explicit):
        tag = explicit
        return {
            "caption": caption,
            "regionToken": region,
            "sourceCaption": chunk.strip(),
            "explicitTag": explicit,
            "inferredTag": tag,
            "tagInferenceNote": "explicit tag from source excerpt",
        }
    # Standalone base-like caption
    if is_bcp47_base(caption) and not region:
        tag = caption.lower()
        return {
            "caption": caption,
            "regionToken": region,
            "sourceCaption": chunk.strip(),
            "explicitTag": None,
            "inferredTag": tag,
            "tagInferenceNote": "best-effort caption token used as tag",
        }
    base = guess_base_language_caption(caption)
    if not base:
        return None
    if region and is_bcp47_base(region):
        tag = f"{base}-{region.lower()}"
        return {
            "caption": caption,
            "regionToken": region,
            "sourceCaption": chunk.strip(),
            "explicitTag": None,
            "inferredTag": tag,
            "tagInferenceNote": "inferred base+region from caption",
        }
    return {
        "caption": caption,
        "regionToken": region,
        "sourceCaption": chunk.strip(),
        "explicitTag": None,
        "inferredTag": base,
        "tagInferenceNote": "inferred base language from caption",
    }

def apple_parse_one(chunk: str):
    chunk = chunk.strip()
    if not chunk:
        return None
    caption = chunk
    region = None
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", chunk)
    if m:
        caption = m.group(1).strip()
        region = normalize_region_token(m.group(2)) or m.group(2).strip()
    if not caption:
        return None
    base = guess_base_language_caption(caption)
    if not base:
        return None
    if region and is_bcp47_base(region):
        tag = f"{base}-{region.lower()}"
        return {
            "caption": caption,
            "regionToken": region,
            "sourceCaption": chunk.strip(),
            "explicitTag": None,
            "inferredTag": tag,
            "tagInferenceNote": "inferred base+region from caption",
        }
    return {
        "caption": caption,
        "regionToken": region,
        "sourceCaption": chunk.strip(),
        "explicitTag": None,
        "inferredTag": base,
        "tagInferenceNote": "inferred base language from caption",
    }

def guard(dest: Path) -> int | None:
    """D5 guard. Returns an exit code to abort with, or None to proceed.
    Non-authoritative: refuses to run at all unless ALLOW_ENV is set, and refuses
    to write inside the candidate lane unless LANE_OVERWRITE_ENV is also set."""
    if os.environ.get(ALLOW_ENV) != "1":
        print(
            f"REFUSED: fix-store-bcp-tags.py is NON-AUTHORITATIVE (cannot reproduce "
            f"candidate byte-semantics). Set {ALLOW_ENV}=1 only for deliberate "
            f"historical-reference experiments into a scratch destination.",
            file=sys.stderr,
        )
        return 64
    try:
        dest.resolve().relative_to(CANDIDATE_LANE_ROOT.resolve())
        in_lane = True
    except ValueError:
        in_lane = False
    if in_lane and os.environ.get(LANE_OVERWRITE_ENV) != "1":
        print(
            f"REFUSED: DEST {dest} is inside the candidate lane "
            f"({CANDIDATE_LANE_ROOT}); this would destructively overwrite the "
            f"authoritative candidate extraction. Set {LANE_OVERWRITE_ENV}=1 "
            f"only if you intend to destroy the candidate artifact.",
            file=sys.stderr,
        )
        return 65
    return None

def main(dest: Path | None = None) -> int:
    dest = dest if dest is not None else DEST
    rc = guard(dest)
    if rc is not None:
        return rc
    if not SNAP_PATH.is_file():
        print(f"Missing snapshot: {SNAP_PATH}", file=sys.stderr)
        return 2
    snap = json.loads(SNAP_PATH.read_text(encoding="utf-8"))
    stores = snap.get("stores", {})
    google_block = stores.get("googlePlay")
    apple_block = stores.get("appleAppStore")
    if not google_block or not apple_block:
        print("Missing store block(s)", file=sys.stderr)
        return 3
    google_full = " ".join(google_block.get("visibleExcerptFirst120", []))
    apple_full = " ".join(apple_block.get("visibleExcerptFirst120", []))

    google_start = "you can do so in the following languages: "
    google_end = "Purchase and apply human translations"
    apple_start = "you can localize it in the following languages and locales: "
    apple_end = "When adding more than one language"

    gs = google_full.find(google_start)
    ge = google_full.find(google_end, gs if gs >= 0 else 0)
    if gs < 0 or ge < 0:
        print("Cannot locate Google store-listing list in snapshot excerpt", file=sys.stderr)
        return 4
    google_list = google_full[gs + len(google_start):ge].strip()

    as_ = apple_full.find(apple_start)
    ae = apple_full.find(apple_end, as_ if as_ >= 0 else 0)
    if as_ < 0 or ae < 0:
        print("Cannot locate Apple store-localization list in snapshot excerpt", file=sys.stderr)
        return 5
    apple_list = apple_full[as_ + len(apple_start):ae].strip()

    google_rows: list[dict] = []
    seen_google: set[str] = set()
    for chunk in re.split(r"\s+[" + DASH + DASH2 + r"]\s+", google_list):
        row = google_parse_one(chunk)
        if not row:
            continue
        key = row["sourceCaption"]
        if key in seen_google:
            continue
        seen_google.add(key)
        google_rows.append(row)

    apple_rows: list[dict] = []
    seen_apple: set[str] = set()
    for chunk in re.split(r",(?![^()]*\))", apple_list):
        row = apple_parse_one(chunk)
        if not row:
            continue
        key = row["sourceCaption"]
        if key in seen_apple:
            continue
        seen_apple.add(key)
        apple_rows.append(row)

    out = {
        "schemaVersion": "store-locale-bcp47-extraction/1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceSnapshot": {
            "path": str(SNAP_PATH),
            "googlePlay": {
                "canonicalUrl": google_block["canonicalUrl"],
                "fetchedUtc": google_block["fetchedUtc"],
                "sha256": google_block["sha256"],
                "bytesFetched": google_block["bytesFetched"],
            },
            "appleAppStore": {
                "canonicalUrl": apple_block["canonicalUrl"],
                "fetchedUtc": apple_block["fetchedUtc"],
                "sha256": apple_block["sha256"],
                "bytesFetched": apple_block["bytesFetched"],
            },
        },
        "googlePlay": {
            "sourceListTextExcerpt": google_list,
            "rows": google_rows,
        },
        "appleAppStore": {
            "sourceListTextExcerpt": apple_list,
            "rows": apple_rows,
        },
    }

    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {dest}")
    print(f"googlePlay rows: {len(google_rows)}; distinct inferred tags: {len({r['inferredTag'] for r in google_rows})}")
    print(f"appleAppStore rows: {len(apple_rows)}; distinct inferred tags: {len({r['inferredTag'] for r in apple_rows})}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
