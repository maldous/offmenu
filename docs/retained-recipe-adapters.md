# Selected retained HTML recipe adapters

Parser 1.3.3 adds `parse_html_recipes(...) -> list[recipe]`. The keyword
arguments match `parse_html_recipe`. The trusted custody caller explicitly sets
`source['adapter']`; these adapters do not fetch or automatically retry sources.

| Selected adapter | Retained source ID | Representation |
| --- | --- | --- |
| `montserrat-paragraph-recipe-v1` | `source-24bb0dd0155f406f19d1` | One recipe with paragraph/line-break ingredient and method labels |
| `martinique-paragraph-recipes-v1` | `source-f1200d43cb166403d088` | Every marked recipe in the explicit Christmas recipe section |
| `wprm-visible-recipe-v1` | `source-61c40ee9464c96d109fe` | One visible WPRM card, with its actual ingredient, instruction and yield text |

The selected operation must bind each adapter to its exact retained asset hash.
An unsupported structure fails the entire call. The singular API rejects a
selected multi-recipe collection rather than returning only its first recipe.
The generic JSON-LD parser still rejects fields absent from extracted page text.
The WPRM adapter deliberately selects the visible representation; it does not
remove punctuation from JSON-LD until it resembles visible text.

Locations index the exact UTF-8 bytes of
`BeautifulSoup(raw, 'html.parser').get_text('\n', strip=False)`. DOM positions
distinguish repeated titles and instructions. All recipe records retain the
selected asset's `sourceRecordId`; the existing writer's asset ordinal gives
each variant a distinct identity. Ingredient IDs also include that ordinal.

Paragraph steps remain source blocks, including a whole unsplit procedure when
the source gives one paragraph. Explicit underlined labels, duration/context
and attribution remain source notes. Unmarked lines remain intact in their
explicit ingredient or method section; their semantic role and component
membership are not inferred. No units, identities, regional claims or
translations are normalized. Missing values stay unknown.

The writer change only rebinds parser version/hash; its schema and import logic
are unchanged. The old pinned custody caller and existing stores remain on
their original code. A reviewed successor caller must bind these adapters,
call the plural API, retain the complete list/count and preserve existing
held-descriptor, whole-input hash, identity and EOF checks. This source change
does not authorize loading or replacing retained records.

Validation uses generated markup and generated in-memory stores. Private
bounded cached-fragment diagnostics found MS 1 recipe (11 ingredient lines,
1 procedure block), MQ 2 recipes (4/20 ingredient lines, 4/10 step blocks), and
MR 1 recipe (7 ingredient lines, 8 steps). Those fragments lack full-original
EOF evidence. They establish neither accepted source records nor complete
country coverage, semantic mapping or gold admission. Independent source/API
review, normal integration and Worker13's separately selected full-original
replay remain required before a separately selected load. Worker13 retains
recipe execution and MT PDF assessment ownership.
