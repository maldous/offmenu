/** Finite authenticated connector-owner gateway; never a coding-child tool.
 * Existing authenticated adapters supply observations. Persisted controller
 * intent precedes mutations; canonical readback alone certifies their effects.
 */
export async function advanceIntegration({controller, github, linear, observe, unitReviewWriter}) {
  let snapshot = await observe();
  let decision = await controller.step(snapshot);
  // Optional same-owner transport, installed only by the authenticated sole
  // integration owner. Neither this callback nor an owner/authenticated string
  // authenticates a coding child. No transport/credential is configured here.
  // Only the fresh controller qualification may cross this seam; repair and
  // reconciliation decisions never become unit verdicts. Normal flow is unchanged.
  if (unitReviewWriter && decision.status === 'merge-intent' &&
      decision.action?.kind === 'merge-pr' && decision.merge_effect === 'pending' &&
      decision.qualification_sha256 && !snapshot.cancel_requested &&
      !snapshot.unresolved_findings?.length && snapshot.review?.verdict === 'accept' &&
      !snapshot.review?.findings?.length) {
    try {
      await unitReviewWriter(structuredClone({snapshot, decision}));
    } catch (error) {
      // Publication can fail, but no GitHub mutation has been attempted.
      await controller.outcome('merge', 'not-issued');
      throw error;
    }
  }
  let mergeIssued = false;
  // At most one merge and the controller's three metadata attempts. Every
  // returned metadata action is consumed here, including slow-readback retries.
  for (let used = 0; used < 4 && decision.action; used++) {
    const action = decision.action;
    if (action.kind === 'merge-pr') {
      if (mergeIssued) return await controller.outcome('merge', 'not-issued');
      let pr;
      try {
        pr = await github.getPullRequest(action.repository, action.pr_number);
      } catch (error) {
        // No mutation has been invoked. A failed read cannot create an unknown
        // merge effect. Explicit permission refusals still stop for authority.
        return await controller.outcome('merge', error.knownRefused === true ? 'refused' : 'not-issued');
      }
      if (!pr || pr.merged || pr.head_sha !== action.expected_head_sha ||
          pr.base_sha !== action.expected_base_sha || pr.base !== 'develop' ||
          pr.head !== action.expected_head_branch ||
          pr.draft !== false || pr.mergeable !== true) {
        return await controller.outcome('merge', 'not-issued');
      }
      let outcome;
      mergeIssued = true;
      try {
        const response = await github.mergePullRequest({
          repository_full_name: action.repository, pr_number: action.pr_number,
          expected_head_sha: action.expected_head_sha, merge_method: 'merge'
        });
        outcome = response.merged === true ? 'succeeded' :
          response.known_refused === true ? 'refused' : 'uncertain';
      } catch (error) {
        outcome = error.knownRefused === true ? 'refused' : 'uncertain';
      }
      await controller.outcome('merge', outcome);
    } else if (action.kind === 'update-linear') {
      let outcome;
      try {
        await linear.completeIssue(action.issue_id, {
          merge_commit_sha: action.merge_commit_sha,
          validation_operation_key: action.validation_operation_key
        });
        outcome = 'succeeded';
      } catch (error) {
        outcome = error.knownRefused === true ? 'refused' : 'uncertain';
      }
      await controller.outcome('linear', outcome);
    } else {
      // Repairs are work packets, never report-supplied executable commands.
      return decision;
    }
    decision = await controller.step(await observe());
  }
  if (decision.action?.kind === 'update-linear') {
    // Defensive bound: do not strand a newly persisted but unconsumed intent.
    return await controller.outcome('linear', 'not-issued');
  }
  return decision;
}
