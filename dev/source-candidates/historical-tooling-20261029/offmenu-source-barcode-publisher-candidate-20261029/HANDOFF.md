# Source-barcode index publisher — source-only candidate

Pending independent review. Baseline exact source SHA-256 0bf9f679b4b6dd3643456c31387e9396073d3e97ebc7058e2ff735dd6bc70bbb. Only ROOT, DESCRIPTOR, PREFIX, new exact EXPECTED_PATHS, allowed_delta and validate_descriptor differ. Generic deployment title and complete main remain byte-identical. Transport helpers/definitions and all other top-level nodes remain source/AST identical; per-definition hashes are in the receipt.

Exactly manifest.json and all256 lowercase shards/00.json.gz through shards/ff.json.gz are required in the fixed namespace. Entries retain lowercase SHA-1/SHA-256 and strict nonnegative integer bytes validation. No producer-manifest interpretation or data projector added. Existing main owns baseDeployId/servedBaseManifestSha256 checking; unchanged pin/semantic checks remain.

17 focused methods pass; test source includes257 individual missing-entry subcases and forbidden-network/private-helper guards. Only validator and source-preservation checks execute; no live publisher main/provider/private operation. Earlier transport tests were unavailable and not rerun or claimed.

Do not deploy on this author receipt. Native independent reviewer approves exact candidate/diff; existing sole publication owner controls any subsequent reviewed adoption. No current deployment changed. Rollback before adoption is to leave this unused candidate inactive.
