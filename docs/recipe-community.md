# Recipe community

OffMenu's recipe community is a native, low-volume, text-first feature backed by the existing D1 database. It does not embed a forum or disclose private kitchen, health, provider, account, email, or journey data.

Recipes and comments are public only after review. An author confirms original rights and chooses CC BY 4.0 or CC0-1.0 before submitting. Administrators and trusted automation use the same revision-checked moderation operation; automation has no browser route and cannot bypass a stale review.

Every recipe has public authorship attribution. It defaults to `human`; AI-assisted submissions have a bounded visible agent name. Only that declaration is public: prompts, personal AI credentials, private instructions, and model configuration are never stored with a community recipe. Trusted MCP contribution must force `kind: ai` and provide the authenticated contributor's selected agent name.

Voting is one verified account per recipe, cannot be self-voted, and supports changing or removing a vote. Lists show vote totals, separate ratings and a Wilson lower-bound rank so a small early vote count cannot dominate. Votes are never inputs to nutrition, fitness, health, pantry, or trophy decisions.

Recipe ranking uses `wilson-v1`: the Wilson lower bound of public up/down votes, then net score, creation time and ID. Ratings remain a separate display signal. The endpoint uses a stable cursor over this order, so an older highly ranked recipe is never dropped by a recent-item sample.

Community profiles are opt-in and expose only alias, bio, opaque community identifier and public community trophies. Personal profile data and private journey trophies remain owner-scoped. This first release has a bounded text/JSON recipe contribution path, avoiding media storage cost; image uploads can be added later behind a moderated object-store pipeline.
