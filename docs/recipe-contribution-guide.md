# Share an original recipe with the community

This guide follows OffMenu source
`59496c6cf006c16b6ac4859580d0e91374682756`, checked by reading source rather than
using a running account. Live submission, review, account access and device or
accessibility behavior remain unverified. The labels below are the English labels.

## Open community recipes

Choose **Me → Help & community**, then find **Community recipes** in the panel.
This section is separate from public discussions and private support requests.
Sign in with your own account to contribute, comment, vote or save a community
profile. Demo mode does not supply a signed-in contributor.

Choose **Top recipes** or **Recent recipes**, then open a recipe to read its
description, ingredients, steps, license and human or AI-assisted attribution.
The list entry displays a vote score and a separate average rating; **—** means
no average rating is supplied. Top order uses vote confidence, not the rating.
The current page shows a limited list and has no next-page control. An empty list
does not prove there are no recipes: loading failures can also leave it empty.

## Choose what your public profile shares

After signing in, find **Public community profile** in the same panel.

1. Enter a **Public alias** of 2–40 characters and an optional **Bio** up to
   500 characters. Keep private contact, health and account details out of them.
2. Check **Publish this profile** to opt into a public profile, or leave it
   unchecked to keep that profile unpublished.
3. Choose **Save community profile**. Reopen Help & community to check the saved
   fields: this form has no success or error message. If another session changed
   the profile, reopen and review the current values before saving again.

A public profile exposes the alias, bio, community identifier and public community
trophies. It does not publish your personal profile or private journey trophies.
Unchecking the profile option does not withdraw recipes or comments. Each recipe
and comment has its own public-alias field; check that field for every submission.

## Prepare the recipe JSON

The contribution form accepts recipe text as **Recipe JSON**, or a JSON file;
it is not a free-form recipe editor or an image uploader. Keep your own copy.
Start with this structure and replace it with a recipe you have rights to publish:

```json
{
  "title": "My original toast",
  "description": "A simple recipe written in my own words.",
  "servings": 1,
  "ingredients": [
    {"name": "Bread", "quantity": 2, "unit": "slices"}
  ],
  "steps": ["Toast the bread and serve."],
  "language": "en",
  "license": "CC BY 4.0"
}
```

Use a title of 2–160 characters, description up to 4,000 characters and a serving
count greater than zero and at most 100. Supply 1–100 ingredients with a name,
numeric quantity and unit, and 1–50 nonempty steps. Ingredient names allow up to
160 characters, quantities 0–100,000 and units up to 40 characters; each step
allows up to 2,000 characters. Use separate step strings instead of line breaks
inside a step. Set `language` to a 2–20-character value such as `en`.

Set `license` to exactly `CC BY 4.0` or `CC0-1.0`. This is your publication choice;
the form does not establish that you own someone else's recipe text. The browser
form passes the fields shown above; extra fields, including nutrition, are not
included in its cleaned submission. Do not assume an imported file's extra data
will be published.

## Preview and submit for review

1. Enter the recipe's **Public alias** (2–40 characters).
2. Paste the JSON into **Recipe JSON**, or choose **Recipe JSON file**. Keep the
   file under 20 KB and the entire contribution small; the server also limits
   the complete submission body, including alias and attribution, to 20,000 bytes.
3. Choose **Recipe attribution**: **Human recipe** or **AI-assisted recipe**.
   For AI assistance, enter an **AI agent name** of 1–80 characters. That name is
   public attribution; do not put credentials, private prompts or instructions in it.
4. Choose **Preview recipe** and inspect the cleaned JSON. An invalid recipe can
   leave the preview blank without an explanation. Preview does not save or send
   anything, and it does not establish server acceptance.
5. Check **I confirm this is an original recipe and I have rights to publish it
   under the recipe license.** Then choose **Submit recipe for review**.
6. Read the message: **Recipe submitted for review.** means pending review;
   **Recipe already submitted.** means the same delivery was recognized.

Recipes are listed publicly only after approval. Submission is not a promise of
publication, rights clearance or nutritional validation. The member form has no
pending-submission inbox, edit, withdrawal or moderation control. Copy text you
need before changing views, reloading or signing out.

## Vote, rate or comment on a published recipe

Open a listed recipe. Choose a value from **Rate recipe** (1–5), then **Up vote**
or **Down vote** to send both your vote and that rating. Selecting a rating alone
does not send it. A later vote replaces your account's previous vote and rating;
**Clear vote** removes both. Authors cannot vote on their own recipes.
The current vote controls do not display request errors, so a click alone does
not confirm a change. Reopen the recipe to review its current totals.

Under **Comments**, enter a **Public alias** and **Comment** (1–5,000 characters),
then choose **Post comment**. **Comment submitted for review.** is pending,
not immediate publication; **Comment already submitted.** recognizes a duplicate
delivery. Only approved comments are displayed. Keep private support details out
of public comments. A displayed protein value, if present, is self-reported;
it is not a validated health claim.

## Handle a refusal or an uncertain result

Recipe and comment errors appear beside their submission form. **Sign in required.**
means you need an account session. A temporary posting restriction also prevents
voting; do not try another identity to bypass it. Monthly contribution-limit
messages mean the server refused this submission; repeated sending will not
remove the limit. Invalid-submission messages require reviewing the JSON, alias,
rights confirmation, license and attribution.

For a delivery error, preserve your text and check any confirmation already shown.
Retrying an unchanged recipe in the same open form reuses its delivery identity;
changing the payload, reopening or reloading can create a different request.
An error or missing message does not establish whether a write succeeded. If an
idempotency conflict appears, ask support rather than sending more copies.
Loading, profile-saving and voting failures can be silent; no visible update
does not prove success. Reopen the panel and review what actually loaded.

To report a problem with a community recipe, use **My requests → New request**
in Help & community and select the recipe category. Include its title, public
alias and the issue in your message, then review and send the request. Community
recipe details have no dedicated report button or automatic source-context report.
See [support and preferences](support-preferences-guide.md) for that workflow and
[the recipe-community contract](recipe-community.md) for technical scope and limits.
