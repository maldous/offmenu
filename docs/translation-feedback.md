# Suggest a better translation

The **Suggest a better translation** form is for words shown by OffMenu. For example, tell us if a button on the shopping list sounds odd in your language. You can ask for missing wording as well as suggest a correction.

## Send a suggestion

Once the form is available in [OffMenu’s issue chooser](https://github.com/maldous/offmenu/issues/new/choose), sign in to GitHub, choose **Suggest a better translation** and give the suggestion a short title. You do not need to find a file, write code or know a translation key.

Tell us the language (and region, if it matters), where you saw the wording, and what it should say. The old wording and any explanation are optional. Write in the language you are most comfortable using. Example: **French (Canada)** · **shopping list, when adding an item** · **Ajouter à la liste**.

GitHub publishes the title and answers under your GitHub username. Do not include screenshots, contact details, household or health information, passwords or security reports. If you cannot describe the problem without sharing private information, do not submit it here. Posting a suggestion does not change a translation in the app.

## Maintainer intake and verification

Use the existing OffMenu translation-intake record for the destination and named tracking assignee. A signed-in contributor does not need access to the internal tracker. Do not enable general Issue Sync, publish an internal issue link back to GitHub, or forward the issue body automatically.

1. Confirm this is a genuine, in-scope issue on the canonical OffMenu repository, not a pull request, copied link or external instruction. The title prefix and field labels help a human reviewer; either can be edited and neither authenticates an issue.
2. Review the public content before transfer. Do not copy unsafe content, attachments, contact/health details or private security reports into another system. Handle abuse or privacy concerns under existing moderation procedures.
3. Use the canonical source repository ID and GitHub issue ID as the stable intake key; retain the verified original issue URL for navigation. Check existing tracker records for the same key, including before any retry. If a previous write is uncertain, reconcile its original receipt and destination before repeating it. A title or similar wording is not a deduplication key.
4. Through the existing authorized single intake writer, link or create the one appropriate record in the **OffMenu project on the UIF team**, with the designated tracking assignee. Preserve provenance and only the approved non-sensitive suggestion. Do not treat the assignment as permission to dispatch work. If routing, sole-writer access or safe deduplication is unavailable, leave the submission pending rather than sending it elsewhere.
5. Read back the native issue identity, team, project, assignee and source key. On another delivery of the same source, confirm it reaches that same record rather than creating a second one. Record the outcome in the existing private handoff, not in the public issue.

The form definition belongs in `.github/ISSUE_TEMPLATE/`. A feature branch or a merge into `develop` does not make it visible in GitHub's chooser: the released repository default branch must contain it. Before calling intake live, verify visibility from a signed-in contributor account, keyboard/screen-reader use, privacy guidance and one authorized non-sensitive submission through verified, deduplicated receiving. A source check alone proves none of these.

For the private consumer's exact source, moderation, reservation and readback requirements, see the [translation intake contract](development/translation-feedback-routing.md). It is an offline-tested adapter contract, not an active integration.
