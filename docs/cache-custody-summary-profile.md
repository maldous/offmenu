# Retained-cache metadata evidence

A retained-cache inventory describes candidate assets; it does not establish
current file availability, source rights or dataset acceptance. Historical
execution receipts are preserved separately from the product documentation.
This document describes a metadata-only review contract, not an installed tool,
job, access grant or a request to inspect a private data root.

## Metadata review contract

1. Select exact source/release identities and permitted small metadata files.
   Reuse existing verified evidence before requesting another input read. Do not
   infer missing asset paths or traverse arbitrary payload directories.
2. Preserve exact declared file sizes and hashes. Distinguish a verified byte
   digest from a source-declared payload digest. An uninspected asset remains
   `declared-only`; a metadata reference is not evidence of its body contents.
3. If metadata reading is selected, use bounded read-only file handling, anchored
   paths and no symlink following. Reject unsafe or oversized files, duplicate
   JSON keys and nonfinite values. Keep missing, unreadable, altered, over-limit
   and unknown inputs distinct; do not silently truncate a report.
4. Bind acquisition time to the original download event and the same artifact
   hash. A normalizer timestamp, filename date, publisher release date or file
   modification time is not a substitute. Missing or conflicting evidence stays
   unknown. Age is a review input, not permission for replacement or download.
5. Retain operation-specific source-use conditions and existing holds. A manifest
   claim or metadata hash does not authorize source-body reads, acquisition,
   native replay, public serving or redistribution.
6. Keep private reports local. A compact exported summary can include selected
   source/release IDs, accessibility, digest/size match, provenance, acquisition
   date or null, rights-claim state, holds and missing-evidence reasons. Exclude
   raw records, credentials, arbitrary exception text and payload copies.

The former proposed review profile used a 64 KiB per-file and 2 MiB aggregate
metadata budget, with explicit file-count and runtime bounds. Those are recorded
proposal limits, not evidence that every retained manifest fits or that a reader
has been deployed. Larger or unavailable inputs require a separately selected
bounded operation; no automatic access or execution fallback is defined here.

## Interpreting retained observations

Historical inventories declared 22 releases and 21 handler-bound release entries,
not necessarily 21 distinct parser files. A prior selected read reported nine
Norway/France assets totaling 30,623,126 bytes, while original acquisition dates
were unknown. Other manifest paths, declared counts and rights links remained
unverified or missing. These are dated receipt claims, not a new inspection or
present custody/rights qualification. Use current exact input evidence for any
new product operation; no dataset completion follows from these observations.
