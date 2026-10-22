# Multilingual reusable recipe sources: practical acquisition review
**Retrieved:** 22 October 2026. **Scope:** public primary-source research and small representative content/schema inspection, not a production fetch.

## Executive findings

1. **Koch-Wiki is the strongest newly identified large German recipe corpus:** the publisher distinguishes **11,434 recipes**, **2,504 ingredient entries**, and **435 techniques**. Actual recipes have quantities, directions, yield, time and equipment. Content is **CC BY-SA 3.0**, permitting commercial reuse with attribution and ShareAlike. These are publisher counts, not an audited net-new ingest total. [Count](https://www.kochwiki.org/wiki/Hauptseite), [sample](https://www.kochwiki.org/wiki/Arabischer_Bulgursalat), [content policy](https://www.kochwiki.org/wiki/Koch-Wiki:Lizenzbestimmungen).

2. **Multilingual Wikibooks is a real reusable corpus, but much is already represented in the retained snapshot.** Ingredient-and-preparation samples were verified in **11 non-English editions**: German, French, Bengali, Tamil, Persian, Arabic, Chinese, Japanese, Indonesian, Portuguese and Polish. The English cookbook links **54 other language editions**, but that is a discovery frontier, **not 54 verified recipe collections**. German's all-recipes category reports 640 pages; Bengali's cookbook category reports 364 direct pages plus 11 subcategories, with nonrecipe material mixed in. The pinned 14 October catalog snapshot already reports 17,379 Wikibooks records across 32 editions (3,309 English), so these observations are quality/delta leads rather than an assumed net-new multilingual corpus. [Language navigation](https://en.wikibooks.org/wiki/Cookbook:Table_of_Contents), [German category](https://de.wikibooks.org/wiki/Kategorie:Kochbuch/_Alle_Rezepte), [Bengali category](https://bn.wikibooks.org/wiki/বিষয়শ্রেণী:রন্ধনপ্রণালী).

3. **Korean MFDS COOKRCP01 is an unusually well-structured non-English government source.** Official documentation contains actual ingredient quantities and up to 20 preparation steps, nutrition and stable IDs. The official dataset's reuse field says **no restrictions**, rather than merely “free download.” **Operational access is separate:** a key/service application is required, development approval is automatic and operating-stage approval requires review. The total recipe count is **not verified**. [Dataset and reuse scope](https://www.data.go.kr/data/15060073/openapi.do), [schema and actual sample rows](https://www.foodsafetykorea.go.kr/api/newDatasetDetail.do?svc_no=COOKRCP01).

4. **Cuisine-libre provides useful French recipes with explicit per-recipe licenses:** CC BY-SA 3.0, CC0, CC BY and GFDL examples were observed. This is a **license-partitioned corpus**, not one blanket-licensed dataset. A New Caledonian recipe is explicitly CC0; a curry recipe is CC BY-SA 3.0. Catalog/RSS paths returned 404 through this research tool, so scale and bulk-discovery access remain unresolved. [CC0 example](https://www.cuisine-libre.org/tartiflette-caledonienne?lang=fr), [CC BY-SA example](https://www.cuisine-libre.org/curry-de-blettes).

5. **Japan MAFF's regional-food database advertises 1,365 local-dish records**, with rich HTML recipes and regional context. It is promising, but the sampled recipe credits an external recipe provider. MAFF's default Public Data License allows commercial reuse of covered content but excludes uncleared third-party rights. Treat the ministry-owned subset as potentially usable and the identified third-party material as conditional—not the whole source as forbidden. [Count](https://www.maff.go.jp/j/keikaku/syokubunka/expotenji/index.html), [database](https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/index.html), [sample](https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/search_menu/menu/ishikarinabe_hokkaido.html).

6. **Non-PDF historical sources genuinely contain recipes:** Chinese Wikisource's *隨園食單*, Aozora's Japanese *食道楽 春の巻*, Italian Artusi and Spanish Calleja on Gutenberg. Their access is HTML/TXT/XML, not scan-only. They need recipe segmentation, original-work/edition rights checks and deduplication against the pinned 25,135-record cross-source catalog snapshot, including 6,192 historical-archive records—not another indiscriminate book download.

**Acquisition remains disabled.** Production acquisition belongs on **Foo only after all eight databases are provisioned and relationally fit for the existing data**, and after source-specific rights/access tests. No bulk mirror, active fetch-config modification, account registration, production run or source-dataset publication was performed. This source-only research bundle may be published separately. The JSON contains disabled proposals only.

### Classification
- **A:** a practical reusable-content route is established for the specified scope; quality, normal attribution and operational gates still apply.
- **B:** conditional, with the precise missing evidence stated; not a finding that reuse is prohibited.
- **C:** an explicitly restricted subset, not a blanket ban on the host.

The manifest contains **23 source/scope rows: 18 A, 4 B and 1 restricted-subset C**. These are review rows, **not 23 independent datasets**; eleven rows are Wikibooks language editions. No combined recipe total is defensible yet.

## 1. Contemporary community sources

### Koch-Wiki — A, German
The sampled **Arabischer Bulgursalat** has six-person yield, 30-minute time, quantified ingredients, equipment, preparation bullets, variants and categories. Its revision is available through the page's permanent-link/history mechanism. This is substantially better normalized-recipe coverage than title-only cuisine catalogs. [Recipe](https://www.kochwiki.org/wiki/Arabischer_Bulgursalat).

Use recipe/category discovery, not all MediaWiki pages. Preserve page URL, revision ID, history attribution, credited authors, source headings and original ingredient strings. Normalize amounts/units but retain ambiguous German abbreviations. The site-specific license permits adaptation and redistribution with attribution and ShareAlike; the linked version is 3.0. Adapted recipe text must retain the applicable license; this is not an NC license, and the policy distinguishes collections from derivative works. Images still need separate handling. [Policy](https://www.kochwiki.org/wiki/Koch-Wiki:Lizenzbestimmungen), [CC deed](https://creativecommons.org/licenses/by-sa/3.0/).

**Access:** HTML works. A small `/api.php?action=query&meta=siteinfo...` probe was inaccessible through the web tool, so MediaWiki API availability is not yet verified. This was not an authentication refusal or permission denial. Proposed handler: `mediawiki_cookbook_localized`; first perform ordinary endpoint discovery and a single public API smoke test when acquisition resumes. Do not infer that the site is unavailable from this tool limitation.

### Cuisine-libre — A for identified licensed recipe records, French
The curry sample has author, publication month, servings, ingredients, instructions, preparation/cooking times and diet tags. Its recipe-specific link resolves to **CC BY-SA 3.0**. The New Caledonian tartiflette sample has six-person ingredients, directions and times and explicitly dedicates the recipe under **CC0**. These demonstrate real regional recipe text, not only geography tags. [Curry](https://www.cuisine-libre.org/curry-de-blettes), [license version](https://creativecommons.org/licenses/by-sa/3.0/deed.fr), [New Caledonia](https://www.cuisine-libre.org/tartiflette-caledonienne?lang=fr).

Partition by actual license link and retain original author/source:
- [Foodista-derived lovage syrup](https://www.cuisine-libre.org/lovage-spritzers) is labeled CC BY, creating known overlap with Foodista.
- [Wikimanche-derived razor clams](https://www.cuisine-libre.org/couteaux-a-l-echalote) are GFDL, while their photograph has a separate CC BY-SA credit.
- [Bakwan](https://www.cuisine-libre.org/bakwan) credits Ramekin and links the original, with recipe/photo licensing shown separately.
- External “related recipe” links must not be mistaken for recipe text licensed by Cuisine-libre.

**Handler:** `cuisine_libre_html_license_partitioned`. Extract the main recipe only; discard comment forms, ratings widgets and visible template debris. No API, JSON-LD or whole-site total was verified. Discovered `/recettes`, `/exporter`, `/licences` and `/mentions-legales` returned 404 via the tool; individual recipe pages work. Resolve canonical catalog/RSS paths before a production plan, not by assuming every linked page is fetchable.

### GNOME Recipes — B, structured base plus translation catalogs
Official upstream confirms bundled recipes and chefs live in `data/recipes.db` and `data/chefs.db`; `po-data` carries recipe translations. The file is **GLib keyfile text, not SQLite**. Observed data include rice/maize/apple cake, tzatziki and soy chicken, with actual quantities and directions. [Architecture/data documentation](https://wiki.gnome.org/Apps/Recipes/Contributing/Intro), [recipe data](https://raw.githubusercontent.com/GNOME/recipes/master/data/recipes.db).

Fields include `Name, Author, Description, Cuisine, Season, Category, PrepTime, CookTime, Ingredients, Instructions, Serves, Yield, Diets, Images, Created, Modified`. Ingredient strings encode quantity/unit/name/group with tabs and escaped newlines; directions include timer and temperature markup. Use a keyfile-aware parser, not line-based splitting or a SQLite connector.

The current public tree metadata showed a 97,528-byte recipe file; this is **file size, not recipe count**. Seventeen recipe translation catalogs are listed: ar, cs, de, el, es, eu, fr, fur, hu, id, nl, pt_BR, sl, sr, sv, uk, zh_CN. They are not seventeen complete independent recipe corpora. Base submission guidance requests English originals for localization. [Languages](https://raw.githubusercontent.com/GNOME/recipes/master/po-data/LINGUAS), [contribution guidance](https://wiki.gnome.org/Apps%282f%29Recipes%282f%29Contributing.html).

**Unclosed rights point:** repository `COPYING` is GPL-3.0; inspected contribution guidance requests original recipes but did not explicitly establish the grant for contributed recipe text/photos. GNOME's CC BY-SA documentation policy applies to help documentation, not automatically to recipe data. Do not promote this to “CC BY-SA recipes” based on help/legal.xml. Obtain a data-specific licensing statement or establish repository-license scope for contributed content, then retain chef/recipe authorship and translation provenance. [COPYING](https://github.com/GNOME/recipes/blob/master/COPYING), [recipe help](https://raw.githubusercontent.com/GNOME/recipes/master/help/C/contribute.page), [documentation licensing scope](https://wiki.gnome.org/DocumentationProject/Guide/Licensing).

## 2. Multilingual Wikibooks — verified recipe breadth

Current Wikimedia terms establish CC BY-SA 4.0 for covered contributed text and permit commercial reuse. Preserve attribution via article/history links, license notice and any imported attribution; indicate changes and observe ShareAlike for adaptations. Some content has exceptions and media has its own licensing. This is a content license, distinct from MediaWiki software licensing. [Terms, section 7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use).

| Edition | Verified actual recipe and useful fields | Important gaps / parsing treatment |
|---|---|---|
| German | [Afrikanisches Huhn](https://de.wikibooks.org/wiki/Kochbuch/_Afrikanisches_Huhn): quantified ingredients, preparation, six servings, 30–45 minutes, difficulty and diet flags. | “African” is the page's generic label, not proof of a national cuisine. [640 all-recipe-category pages](https://de.wikibooks.org/wiki/Kategorie:Kochbuch/_Alle_Rezepte) is not a quality-audited total. |
| French | [Couscous](https://fr.wikibooks.org/wiki/Livre_de_cuisine/Couscous): six-person ingredient list and grouped numbered preparation stages. | Some ingredients appear only in directions; flag incompleteness. French-language North African food is not an African-language corpus. Root category has subcategories, not a usable total. |
| Bengali | [মোরগ পোলাও](https://bn.wikibooks.org/wiki/রন্ধনপ্রণালী:মোরগ_পোলাও): ingredient table, 3–4-person yield, 1–2-hour time and preparation. | Bengali numerals and quantities; stock/rice subcomponents partly embedded in prose. The 364-page category includes nonrecipes. |
| Tamil | [இட்லி](https://ta.wikibooks.org/wiki/சமையல்_நூல்/இட்லி): ingredient table with rice/black-gram quantities and fermentation/steaming instructions. | History, varieties and equipment are not separate recipes; no standard yield/time guaranteed. |
| Persian | [کته](https://fa.wikibooks.org/wiki/کتاب_آشپزی/کته): quantified ingredients and preparation, multiple variants. | Preserve RTL, Persian numerals, variant boundaries and original units; do not combine variants into one ingredient list. |
| Arabic | [منسف](https://ar.wikibooks.org/wiki/كتاب_الطبخ/منسف): ingredient names and preparation section. | Quantities and standardized yield largely absent; admit as partial recipe rather than invent amounts. |
| Chinese | [蛋炒饭](https://zh.wikibooks.org/zh-hans/食谱/蛋炒饭): ingredients, equipment and preparation. | Ingredient amounts missing. Simplified/traditional display conversions are not distinct source recipes. |
| Japanese | [味噌汁](https://ja.wikibooks.org/wiki/料理本/味噌汁): three-person yield, quantities, preparation and main cooking steps. | The [simple index](https://ja.wikibooks.org/wiki/料理本/簡易版) is better than blindly following main-root red links; captions can contain mismatched dish descriptions. |
| Indonesian | [Nasi goreng](https://id.wikibooks.org/wiki/Resep:Nasi_goreng): ingredient amounts and numbered directions. | List omits seasonings used in directions. Credits *Mustikarasa*, Indonesian agriculture 1967: retain and inspect imported-text provenance. |
| Portuguese | [Brazilian feijoada](https://pt.wikibooks.org/wiki/Livro_de_receitas/Feijoada_brasileira_completa): ingredients, steps and sauce subrecipe. [Ibo-style feijoada](https://pt.wikibooks.org/wiki/Livro_de_receitas/Feijoada_à_moda_do_Ibo): Mozambique-specific procedure with ingredients in prose. | Mozambique sample lacks full quantities. Book inventory includes household bleach—exclude nonfood material. Pending versus published revisions require a policy. |
| Polish | [Pierogi dough](https://pl.wikibooks.org/wiki/Książka_kucharska/Ciasto_na_pierogi): five ingredients, fractional cups, optional egg and eight steps. | Yield absent; optional ingredients and timing inside steps need separate fields. |

Spanish [Artes culinarias](https://es.wikibooks.org/wiki/Artes_culinarias) and Russian [Кулинарная книга](https://ru.wikibooks.org/wiki/Кулинарная_книга) roots were inspected, but are **not promoted here to fully sample-verified rows**. Other linked editions remain discovery candidates. We did not verify comparable reusable native-language collections for every African, South Asian, indigenous American or other language; regional dish coverage is not language completeness.

### Access and export design
- Enumerate relevant categories and cookbook namespaces using [Categorymembers](https://www.mediawiki.org/wiki/API:Categorymembers); recurse subcategories with continuation and page-ID deduplication. Category membership alone cannot distinguish recipes from techniques or ingredient articles.
- Fetch chosen revision text and IDs/timestamps/hashes through [Revisions](https://www.mediawiki.org/wiki/API:Revisions). Store language, source wiki DB, page ID, revision ID, title, recipe-section ID, canonical URL, original content hash and license/attribution snapshot.
- **Important current change:** Wikimedia's [legacy dump index](https://dumps.wikimedia.org/backup-index.html) says the legacy XML dump service is deprecated and will sunset in **January 2027**. Do not design a new pipeline around indefinitely available legacy per-wiki dump URLs.
- The replacement [MediaWiki Content File Exports](https://dumps.wikimedia.org/other/mediawiki_content_history/readme.html) supplies per-wiki **compressed XML** compatible with Special:Export and legacy XML, with current-content and history choices. **The service changes; XML has not disappeared.** Prefer current content for snapshot extraction, retaining revision metadata and a migration-aware manifest. [Operational documentation](https://wikitech.wikimedia.org/wiki/MediaWiki_Content_File_Exports).
- No dump was downloaded. A French API probe was inaccessible through the research tool, so a production adapter still needs a normal live API smoke test. Follow Wikimedia's current User-Agent/access/rate guidance; the legacy index states at most three connections per IP, not an invitation to distribute requests across addresses.

## 3. Public regional government sources

### Korean MFDS — A content route, gated operational access
The official HTML preview includes real rows, e.g. rice/tofu/egg porridge with grouped quantities and five sequential cooking instructions. Fields: `RCP_SEQ` ID, `RCP_NM` title, `RCP_WAY2` cooking method, `RCP_PAT2` dish type, `INFO_*` nutrition/weight, `RCP_PARTS_DTLS` ingredient prose, `MANUAL01..20`, optional step images and sodium-reduction tips. Some portion weights are empty. No verified cook-time/yield fields should be invented. [Primary schema/sample](https://www.foodsafetykorea.go.kr/api/newDatasetDetail.do?svc_no=COOKRCP01).

Proposed disabled handler `mfds_cookrcp01`: JSON/XML endpoint pattern `https://openapi.foodsafetykorea.go.kr/api/{key}/COOKRCP01/json/{start}/{end}`; stable-ID upsert, preserve all ordered nonempty steps, parse ingredient subgroups, track change dates. Documentation states maximum 1,000 rows/request and additional incremental/per-hour/file limits. The key/service enrollment and operating review must be completed through the approved credential process; no registration was attempted. A two-row public sample URL was inaccessible via the tool, but this is not evidence that authenticated API requests fail. Do not use third-party 1,176/1,600 counts as the official total.

### Korean MAFRA/EPIS relational recipes — B, highly relevant database shape
Three official endpoints describe **base recipes**, **ingredients**, and **preparation steps**, joined by `RECIPE_ID`. Embedded examples show Korean bibimbap base information, ingredient rows and numbered cooking instructions; thus this is not just a nutrition catalog. Formats are XML/JSON with XLS documented. Base fields include cuisine, dish type, time, calories, yield and difficulty; procedure fields include step order, text and tips. [Base](https://data.mafra.go.kr/opendata/data/indexOpenDataDetail.do?data_id=20150827000000000464), [ingredients](https://data.mafra.go.kr/opendata/data/indexOpenDataDetail.do?data_id=20150827000000000465&filter_ty=), [steps](https://data.mafra.go.kr/opendata/data/indexOpenDataDetail.do?data_id=20150827000000000466).

The rendered reuse-scope field is blank, so **free API access is not yet a verified content grant**. Exact rights scope needs clarification. The published raw-IP endpoint was not called. The five-row example is a sample, not corpus total. This is a useful relational-fit fixture for the eight-database design: ingest all three relations, validate foreign keys, and reject orphan steps/ingredients. Do not count the ingredient and step rows as recipes.

### MAFF Japan — B for credited third-party content, potential A subset
The Ishikarinabe page contains Hokkaido/local-area context, season/history, four-person ingredient quantities and four steps, while naming an external recipe provider. Japanese and English pages should be linked as language variants, not added as distinct culinary recipes. [Sample](https://www.maff.go.jp/j/keikaku/syokubunka/k_ryouri/search_menu/menu/ishikarinabe_hokkaido.html).

[MAFF's policy](https://www.maff.go.jp/j/use/link.html) adopts [Public Data License 1.0](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0): covered material can be copied/adapted commercially with source attribution and modification notices; third-party rights are excluded unless cleared, and images frequently need separate checking. The license permits use under its specified CC BY 4.0-compatible terms; it is **not a blanket public-domain declaration**. Record provider credits and clear/narrow the subset before enabling. Handler `maff_regional_html`; no API or bulk dump verified, no image ZIPs downloaded.

## 4. Historical text without PDF dependency

| Source and status | Actual content / accessible formats | Rights, segmentation and overlap |
|---|---|---|
| **A: Aozora, Japanese *食道楽 春の巻*** | [1903 work card](https://www.aozora.gr.jp/cards/000810/card49947.html); [XHTML text](https://www.aozora.gr.jp/cards/000810/files/49947_40166.html) contains pork preparations inside dialogue and notes. Card offers TXT ZIP as well. | Author died 1927; original historical text is the target, not modern edition additions. One verified volume is not a recipe count. Segment prose, cooking notes and story; preserve historical measures and mark unvalidated historical health/storage claims. |
| **A: Chinese Wikisource *隨園食單*** | [1792 work](https://zh.wikisource.org/wiki/隨園食單), five transcribed sections; [section four](https://zh.wikisource.org/wiki/隨園食單/第四節) contains fish/tofu and other preparation passages. HTML/wikitext/XML available. | Original work carries old-public-domain notice; modern editorial contributions and translations are separate. Preserve attribution and moral-rights notices. Many passages have no quantified list; culinary opinions/techniques are not full recipes. No unsupported “300 recipes” count adopted. |
| **A in applicable jurisdictions: Artusi, Italian** | [Gutenberg 59047](https://www.gutenberg.org/ebooks/59047), [full HTML](https://www.gutenberg.org/cache/epub/59047/pg59047-images.html), plain text/EPUB. The book has 790 numbered recipes; risotto sample includes quantities, yield and cross-referenced peas preparation. | Gutenberg labels public domain in USA; author 1820–1911. Confirm edition/jurisdiction; resolve cross-references and avoid TOC duplication. Wikisource versions are the same underlying work, not another 790 new recipes. |
| **A in applicable jurisdictions: Calleja, Spanish** | [Gutenberg 8870](https://www.gutenberg.org/ebooks/8870), [full HTML](https://www.gutenberg.org/cache/epub/8870/pg8870-images.html), TXT/EPUB. Basic stock sample contains quantities and cooking instructions. | USA PD label, not worldwide guarantee. Heading-based recipe segmentation; variants can refer to prior recipes. Exclude nonfood household instructions. Do not treat the site's automatically generated summary as authoritative publication dating. |
| **B: Bengali *আমিষ ও নিরামিষ আহার*** | [Work page](https://bn.wikisource.org/wiki/রচনা:আমিষ_ও_নিরামিষ_আহার) confirms multiple historical edition records. | This review did not establish a usable full recipe transcription. Scan indexes/metadata alone do not meet admission; no PDF-only dependency and no unsupported “2,500” count. |

[Aozora's policy](https://www.aozora.gr.jp/guide/kijyunn.html) explicitly permits paid/free reuse and adaptation of copyright-expired works, while copyright-active permission-based works have separate restrictions. Catalog metadata licensing is distinct from book-text licensing; its guide's NC license is also not the books' license. Preserve bibliography and input/proofreading credits. **C applies only to the protected/private-use-limited subset**, not all Aozora.

For example, [Rosanjin's 1933 stock-making essay](https://www.aozora.gr.jp/cards/001403/card49986.html) has [actual HTML technique text](https://www.aozora.gr.jp/cards/001403/files/49986_37674.html), but later publication requires separate international rights analysis and does not furnish another fully quantified recipe corpus. Do not infer US public domain solely from Japan's expiry status. Historical sources require jurisdiction-specific review; this report is a sourcing assessment, not a blanket legal determination.

Gutenberg's item notices explicitly warn users outside the USA to check local law. If distributing Gutenberg-branded editions rather than the unbranded original public-domain text, retain/comply with the applicable Project Gutenberg trademark/license terms.

## 5. Cooklang and already-retained overlap

Public Cooklang collections are technically attractive because `.cook` files carry ingredients, quantities, equipment/timers and instructions. However, the federation's software/specification license does **not** license publishers' recipes. The [federation specification](https://github.com/cooklang/federation/blob/main/spec.md) uses RSS/Atom discovery with separate full-recipe enclosure files; retain feed URL, recipe URL, author, updated timestamp and actual upstream content license. General federation coverage is in the structured-sources peer report, not a second count here.

French [Net-Mist/remy](https://github.com/Net-Mist/remy), German [leMaik/rezepte](https://github.com/leMaik/rezepte) and [ggalmazor/recipes](https://github.com/ggalmazor/recipes) were inspected as discovery candidates, but no sufficiently clear recipe-specific reusable grant was established. They are not included as usable corpus rows merely because they are public repositories. Request/narrow rights at source; do not infer a language from a contributor's name or license scraped third-party content from a code LICENSE.

Peer reconciliation confirms:
- **AdamBouhmad/open-recipe-archive:** same retained revision `ae3bd2c`; its advertised 54,843 recipes are **not additional** here.
- **Anduin2017/HowToCook:** retained 362 at `3dfa950f6daf0a5b311fc46619f1b559bac980c4`; no new delta established by this review.
- **UniTools:** retained 501; not new.
- **Wikibooks:** the [pinned 14 October catalog snapshot](https://github.com/maldous/offmenu/blob/52b6a50a59b458bdb49fe7ea090b72c63a4b1a30/docs/world-recipe-research-20261014.json) reports 17,379 records across 32 editions, including 3,309 English. Compare source wiki/page/revision IDs before claiming any new delta. These are historical catalog counts, not current staged, normalized or loaded counts.
- **Cross-source catalog snapshot 25,135:** comprises 24,879 full records plus 256 OCR candidates; historical-archive is a 6,192-record subset. Canonicalize author/work/edition, Gutenberg ID, Wikisource title and Aozora card ID before claiming new content; do not call the whole catalog historical recipes.
- **Cuisine-libre imports:** Foodista and Wikimanche provenance create known cross-source overlap.

No advertised totals are summed. A recipe source may have an additional translation without being an additional underlying dish; keep both `recipe_work_id` and `recipe_text_variant_id`.

## 6. Normalized recipe contract and readiness tests

**Required for admission:** original title, language/script, source URL/stable ID, source revision/date/hash, content rights + evidence URL, attribution, ingredient text (even unquantified), and actual preparation text. Keep a completeness grade rather than hallucinating missing quantities.

**Preserve where available:** ingredient groups and source order; amount/unit/raw strings; optionality; step groups/order; timers/temperatures; equipment; yield and serving basis; prep/cook/rest times; cuisine and region as separately sourced labels; season; nutrition with units/basis; contributor/translator; original work/edition; image license and source separately.

**Do not infer:** nutrition from an unverified calculation, ingredients omitted from the source, safe storage from historical prose, language from cuisine, or exact recipe count from total documents/category pages.

**Relational checks before Foo acquisition:**
1. Source/license/attribution records exist before recipe variants; every variant has a provenance parent.
2. Ingredients, units, steps, equipment, regions and nutrition attach by valid IDs; MAFRA's three relation sets test this especially well.
3. Text variant language and source edition survive normalization; original Unicode/RTL/numerals retained.
4. Rights partitioning is enforceable at record and media level; ShareAlike exports cannot lose notices.
5. Dedup handles redirects, same work across platforms, translations, recipe variants, script renderers, repeated TOCs and imported sources.
6. Parser tests use small permitted fixtures; snapshot/row counts distinguish discovered, fetched, parsed, valid, duplicate and admitted records.
7. All eight databases are provisioned and relationally compatible with existing data; only then consider enabling production acquisition on Foo.

**Suggested order after readiness:** Koch-Wiki → source-ID-reconciled Wikibooks deltas and quality gaps with localized parsers → Korean MFDS after service approval → licensed Cuisine-libre subsets after catalog resolution → carefully segmented PD originals. Resolve MAFF provider scope, GNOME data licensing and MAFRA content grant in parallel.

## 7. Exact outstanding gates and research actions

| Action/target | Status and reason | Completed / next legitimate step |
|---|---|---|
| Koch-Wiki and French Wikibooks API probes | **Uncertain:** web tool said inaccessible, not permission denied. | Recipe HTML and API documentation inspected. Later ordinary public endpoint smoke test; no bypass. |
| MFDS two-record public sample API | **Uncertain:** tool inaccessible. | Official HTML rows and schema verified; no bulk/API credential use. Later one approved-key sample. |
| MFDS operating access | **Pending:** official service application/review. | No registration attempted. Use approved project credential process only after readiness gate. |
| Cuisine-libre catalog/export/license-index paths | **Uncertain:** 404 in tool, recipe pages work. | Per-record rights verified. Resolve canonical discovery paths; do not mistake a failed catalog URL for absent recipes. |
| MAFF external recipe-provider text | **Pending:** default license excludes uncleared third-party rights. | Provider credit captured; narrow to ministry-owned/cleared records or clarify specific supplied text rights. |
| GNOME recipe data, MAFRA recipe relations | **Pending:** exact content-specific grant not established. | Actual schemas/content verified; code/help/metadata licensing explicitly separated. Seek precise source statement. |
| Bengali historical cookbook | **Pending:** actual usable transcription not verified. | Work editions identified; do not ingest metadata/scan links as recipes. |
| Production acquisition | **Held by user:** eight databases must be provisioned and relationally fit, acquisition on Foo. | Manifest entries are disabled. No active acquisition configuration or production data changed. |

No permission-policy denial was encountered in this research. Technical URL failures above remain unresolved where stated; no login/paywall/authentication barrier was bypassed.

### Artifacts
- `multilingual-recipes.md` — this evidence and implementation review.
- `multilingual-recipes.json` — 23 source/scope rows, source-specific rights, samples, schemas, overlap notes, disabled handler proposals and exact blockers.

