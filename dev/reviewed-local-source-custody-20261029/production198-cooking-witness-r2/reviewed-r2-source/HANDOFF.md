NS196-G2 privacy correction R2 — SUPERSEDES R1; independent acceptance pending

The R1 frozen packet must not deploy: its public classification ignored private/unknown child citations, and shared projection trusted the public flag. Original packet remains preserved.
R2 recursively incorporates ALL retained visibility in recipe citations/provenance, selected nutrient provenance and per-nutrient evidence context, and source-reference evidence. Any private wins; missing/unknown source/citation visibility prevents public classification. Nested retained citations/provenance are preserved, not dropped to obtain public status. Existing source labels are not promoted to rights.
copyCookingWitness conservatively combines declared and retained evidence visibility; sharedCookingBatch calls that codec BEFORE projection, so a misleading public root flag cannot expose a private child. All other batch fields are passed through unchanged for existing projection logic. No unrelated sharing/auth rewrite.

Exports for the existing Foo parity bundle:
  export {copyCookingWitness,preserveCookingWitnesses,sharedCookingBatch} from '../public/cooking-witness.js';
The complete cloud/cooking-witness-parity.mjs includes those exports plus finishCookingWitnessState.
SA shared-batch projection: replace only its direct spread of each batch with a spread of __offmenuCookingWitness198.sharedCookingBatch(theSameBatch). Keep the existing event projection and all other fields. Calling the SAME helper is mandatory; do not reproduce the R1 top-level flag check. Full SA source/preimage belongs to the sole integrator and is not guessed here.
lg history: retain the existing R1 exact tail hook in evidence/server-history-helper.patch.
CA validated state: retain finishCookingWitnessState(rawInput, existingValidatedOutput) after all existing validation, for both batches and history. Original current-source cloud/state.mjs hook is included unchanged. Authentication/revision logic stays with the existing integrator.

Applying sources: app-source.patch is the complete superseding patch from exact v196 preimages, including all original additive hooks and the corrected codec/parity/test files. r1-to-r2.patch changes ONLY the three new files and can update a builder that already applied R1. Verify MANIFEST preimages and candidate hashes; do not stack the complete patch twice. Original function-local replacements remain valid for unchanged hook files; no frozen shopping/lot-nutrition changes are included.

Executed evidence on Foo: R1 with expanded 18-case suite passes 13 and fails 5; R2 passes all 18, plus all seven legacy server-history cases. The five new groups cover recipe citation privacy/unknown/all-public, selected nutrient provenance, nested source reference citations, server shared-batch rechecking of misleading public flags, and per-nutrient retained source context. Original zero/unknown/version/local/cloud/backup/retry/binding tests remain. Test fixtures are synthetic only.
Test run 01a18440-a760-2bae-c638-56d5fd212f67 succeeded; child_tree_gone=true. No production write. Full worker SA/lg/CA integration, independent re-review and authenticated served readback remain with existing owners. New candidate is not described accepted.
Scanner work paused without source edits; resume only after this correction handoff.
