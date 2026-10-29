/** Authenticated connector-owner gateway. Never run inside a coding child.
 * Adapters are existing authenticated connectors, not report-supplied commands.
 * Durable controller intent precedes each mutation; readback certifies effects.
 */
export async function advanceIntegration({controller, github, linear, observe}) {
  const snapshot = await observe();
  const decision = await controller.step(snapshot);
  const action = decision.action;
  if (!action) return decision;
  if (action.kind === 'merge-pr') {
    // Refresh immediately before GitHub's expected-head compare-and-merge.
    // GitHub has no expected-base parameter: canonical parents/tree are checked
    // afterwards. Normal repository protection remains authoritative.
    const pr = await github.getPullRequest(action.repository, action.pr_number);
    if (pr.merged || pr.head_sha !== action.expected_head_sha ||
        pr.base_sha !== action.expected_base_sha || pr.base !== 'develop' ||
        pr.head !== 'feature/langgraph-delivery-standardization' ||
        pr.draft !== false || pr.mergeable !== true) {
      await controller.outcome('merge', 'uncertain');
      return await controller.step(await observe());
    }
    let outcome;
    try {
      const response = await github.mergePullRequest({
        repository_full_name: action.repository, pr_number: action.pr_number,
        expected_head_sha: action.expected_head_sha, merge_method: 'merge'
      });
      outcome = response.merged === true ? 'succeeded' :
        response.known_refused === true ? 'refused' : 'uncertain';
    } catch (error) {
      // Only explicit known nonexecution may be called refused. A network
      // timeout has an unknown outcome and cannot safely repeat a merge.
      outcome = error.knownRefused === true ? 'refused' : 'uncertain';
    }
    await controller.outcome('merge', outcome);
    return await controller.step(await observe());
  }
  if (action.kind === 'update-linear') {
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
    return await controller.step(await observe());
  }
  // Repairs are work packets, not arbitrary executable commands.
  return decision;
}
