# Completed-observation query adapter

This inactive, read-only local tool queries one pinned, completed 225-observation
application and its reviewed registry. It preserves source references, language,
duplicate occurrences and unresolved relationships. It does not rerun the
application, modify its inputs, create a service or admit canonical mappings.

Run the generated checks from the repository root:

```sh
python3 -B -m unittest discover -s dev/completed225-query -p 'test_query_normalization.py'
```

These checks open only disposable generated fixtures. They do not open retained
source bodies. No completed application, registry, query output or source data is
included in this repository package.

The CLI's local input locations and hashes identify the already selected source
cut. Running a real query additionally requires the current source-use permission
for those inputs; copying this tool does not grant access. The barcode mode can
dereference only its one explicitly selected retained product line, with an exact
line hash. Other records retain completed decisions and references. The historical
whole-file hash does not claim a fresh whole-file read.

Product labels are not normalized ingredients. An opaque declaration placeholder
does not establish source absence, and a label's language does not qualify a
declaration's language. Projected unit notation does not qualify the original unit
or nutrient basis. Missing ingredient, recipe, profile, quantity and nutrient
relationships remain explicit; the tool does not fabricate positive edges or
replace unknown values with zero.

This source package has no application, MCP or runtime registration. Production,
data processing, canonical admission and serving remain separate operations.
