# Python source and installed-package boundary

The product packages live under `src/`: `offmenu`, `offmenu_ciqual` and
`offmenu_norway`. Preserve their public import names and the `offmenu` console
entry point. Installation must not require a root package copy, symlink, another
project checkout or host-specific service.

Setuptools selects product packages and declared resources. Wheels contain the
ordinary import paths; repository tests, source-control metadata, private data
and operational history are not package resources merely because development
commands can access them.

From the intended checkout:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pip wheel --no-deps --wheel-dir dist/python .
```

Select the intended interpreter and verify `offmenu.__file__`. An editable
installation belongs to its selected checkout; it must not silently import a
sibling checkout. Verify the wheel again in a separate environment and working
directory, including its HTML, schema and source-adapter JSON resources. A
checkout import cannot establish that a wheel includes those resources.

Run materially affected package tests with the declared test extra. Collection
extras are separate and never select or qualify a live source. Tests with
explicit frozen-input prerequisites must report actual skips rather than
inventing data or rewriting their source pins.

Source-specific adapters retain their input identities, parser/layout pins,
unknown-value semantics and source-use rights. A changed parser or source path
requires its affected qualification; relocation does not transfer an older
acceptance to new code. Package resources resolve from the installed package,
while repository-only tools may require the explicit source checkout.

Virtual environments, wheels, build output, caches, private databases and source
payloads remain untracked. Their cleanup must preserve existing consumers and
necessary source provenance.
