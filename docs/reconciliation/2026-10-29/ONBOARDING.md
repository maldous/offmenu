# Developer source pickup

This is the private repository source baseline, not a claim that historical production209 source has been integrated or that its scanner UI passed. Main remains verified-release policy; develop is the agreed integration baseline. Use your own authorized GitHub access; no shared credentials, raw corpus, private runtime records or local archives are required for source pickup.

## Fresh checkout

```sh
git clone git@github.com:maldous/offmenu.git
cd offmenu
git fetch origin
git switch -c develop --track origin/develop
git switch -c feature/<work-name> develop
```

The pinned integration baseline for this handoff is dc39d0d7f29f0b0650be374f0e7e2111ec45c4b7. Resume an existing assigned bugfix branch instead of duplicating its owner. API deadline WIP and scanner209 have separate owner handoffs; both remain inactive. Source-custody branches contain frozen historical packets, not a replacement current application tree.

## Source prerequisites and checks

Existing reconciliation workflow evidence uses Node24 and Python3.12. pyproject.toml declares Python>=3.10 and jsonschema>=4.10.3,<5; package.json has no engines declaration. The documented setup is:

```sh
npm ci
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
```

For an already prepared checkout, documented build steps are `npm run check:generated` then `npm run build`. Existing package test scripts remain the source of truth. No setup, build or tests were executed during this source custody/cleanup handoff. See [maintainer instructions](../../maintainer.md) and the root README for exact project-specific prerequisites.

There is no npm start or npm run dev script. The full browser/Worker preview requires its owner's current instructions; docs/maintainer.md explicitly rejects substituting the Python server or directly running dist/worker.mjs. The separately documented Python demo command is:

```sh
python3 -m offmenu.server --db "$OFFMENU_DEMO_DB" --host 127.0.0.1 --port 8765
```

OFFMENU_DEMO_DB is a user-selected demonstration database path in that command, not evidence of a provisioned application database. No server was launched.

## Configuration contract

[ONBOARDING.env.example](ONBOARDING.env.example) is fully commented documentation. It does not configure a runnable environment or activate authentication. docs/maintainer.md:124-134 is its authority. DB is a deployment-owned D1 binding; PROVIDER_VAULT_KEY and optional BETTER_AUTH_SECRET belong in the existing secret store. CURATED_CORPUS_ORIGIN is an accepted static publication origin; OFFMENU_CURATED_RELEASE is a publication-tool input. OFFMENU_AUTH_MODE and BETTER_AUTH_URL retain their documented conditional authentication requirements. No secret values or live account configuration are supplied.

Full Worker preview/run instructions and deployment-owned bindings remain prerequisites for that interface. This example closes the documented names/classification handoff, not a claim of complete runtime provisioning.

## Git and custody boundaries

Use develop for checked integration and main for verified releases. Keep feature/* and bugfix/* changes based on the agreed integration baseline. Preserve owner WIP before merging. Avoid wholesale merges of historical custody snapshots or known-failing209 into a release. Existing protection access remains unknown after the earlier403; this handoff does not bypass it. The safe pinned workflow set has no ordinary feature push trigger, but old branch tips may differ; verify workflows before publishing historical tips.
