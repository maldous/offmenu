# Scan a barcode and inspect its source information

This guide follows OffMenu source
`59496c6cf006c16b6ac4859580d0e91374682756`, checked by reading source rather than
using a running installation. Camera/device performance, assistive-technology
behavior, deployed lookup availability and offline operation remain unverified.
The scanner described here uses English labels and has no language chooser;
the main app's language preference does not initialize this scanner page.

## Open the scanner and present one item

1. Open **/shelf-scanner.html** on your OffMenu installation. The camera attempts
   to connect automatically. Allow camera access when the browser asks. Camera
   use requires a secure context; use the installation's HTTPS address.
2. The initial setup is **Handheld · rear camera**. Keep the whole barcode,
   including its blank edges, inside the aiming guide. Start around 15–30 cm
   away, hold still briefly and move farther away if the bars look blurred.
   Tilt shiny packaging away from glare. This distance is a starting suggestion,
   not a measured limit for your device.
3. Present one barcode at a time. Live reading requires agreeing frames; an
   **Accepted** camera message means a code was captured. Review the separate
   product lookup status before treating any displayed information as a match.
4. Move the barcode fully out of view before the next identical pack. If you
   deliberately want another capture of the same code, open **⋯ → Session** and
   choose **Next identical pack**. Session entries count capture events, not
   verified products or inventory quantities.

For another lens or placement, use **⋯ → Session → Choose mode**, then expand
**Camera & sound settings**. Choose **Scanning setup** and **Camera**. Bench
uses the front camera; a stand uses the rear camera. Keep the rear lens exposed
when using a stand: laying the phone screen-up blocks it. Bench guidance starts
around 30–50 cm, with more distance if needed for focus. These setup choices
are kept in this tab's memory.

**Mirror** and **Rotate** adjust the preview. **Contrast** enables a decoding
fallback; it cannot restore a badly blurred barcode. Focus, zoom, exposure and
light controls appear only when the camera/browser exposes them. A failed
control change leaves the scanner using its current settings. **Sound off**
can enable a short read tone if browser audio works; a tone confirms capture,
not product qualification. Choose **Enter Explore** (or the selected mode's
Enter button) to return to scanning.

## Type the printed code or use a photo

Choose **Type code** when the camera cannot read the label.

1. Enter **Original identifier**, preserving its characters and leading zeros.
   The form accepts 1–128 printable characters.
2. Leave **Source namespace** at **Barcode · printed code** for a package
   barcode. Choose **USDA-FDC** only for a known FoodData Central source
   identifier; it is not a printed barcode.
3. Leave **Barcode representation hint** at **No hint · exact lexical lookup**
   unless you know the format. In particular, eight digits alone do not establish
   UPC-E. The hint is disabled for USDA-FDC identifiers.
4. Choose **Confirm identifier**, then review the lookup result. **Cancel**
   closes the form without confirming it. A scanner that types into the focused
   field and submits with Enter can use this form, but USB/Bluetooth pairing
   and hardware compatibility have not been established here.

Camera and photo decoding target EAN-13, EAN-8, UPC-A and UPC-E retail codes.
A representation that needs manual confirmation should be entered from the
printed label; do not guess missing digits or a format from the decoder's text.

For a photo, expand **Read a barcode image locally** in Type code and select a
**Barcode image** smaller than 20 MB. Use a sharp JPEG/PNG showing the entire
barcode and its blank edges. If several codes are found, crop to one product
and choose the image again. A photo is one deliberate submission, without the
live camera's repeated-frame check. The camera stops while the photo is read
and attempts to resume afterward when scanning is allowed.

Camera frames and selected photos are passed to local browser decoding in this
source. Captured identifiers then enter the installation's retained-data lookup;
local image decoding does not mean product lookup works offline. The visible
connection is **Real · loaded retained barcode identifiers**. Availability
depends on the installation having the selected retained release and lookup
service; this guide does not establish a functioning installation or provider.

## Read a result without filling in the unknowns

Open **Product details** to expand the sheet. On a narrow screen, the fully
expanded sheet suspends new camera reads until you lower it. Choose **Overview**,
**Ingredients**, **Nutrition** or **Source**; use **Previous**, **Next** and
**Expand** to inspect longer readouts.

The Product group shows source information and the captured identifier. The
OffMenu group shows separately qualified category/ingredient interpretations
when supplied; **Not yet identified**, **—** and unavailable values must stay
unknown. A captured code, a source match and eligibility for an inventory action
are separate facts. Where the decoder normalized its text, the readout warns
that the printed original is unverified.

| Lookup condition | What to do |
| --- | --- |
| Source identifier found | Inspect the retained details and source release. A source assertion does not establish a physical-product winner or canonical ingredient mapping. |
| Multiple source observations | Choose **Inspect source records**, then **Load selected source details** or **Inspect source projection** for the record you want to examine. Selection does not merge identities. |
| Selected search continuing or incomplete | In the source-record choices, use **Continue bounded source search** or **Retry incomplete source lane** when offered. Loaded observations remain available; the search has not established absence. |
| No matching source-asserted identifier | Check the original code and namespace. This is a miss in the selected retained generation, not global absence. |
| Lookup or details unavailable | Read the displayed reason. An identifier may remain known while its product details are unavailable; missing details do not erase the source assertion. |

Source allergens, traces and dietary labels are source claims, not independent
certification. Markets are not origin; serving quantities are not necessarily
package quantities. Missing supplier, recall or recipe relations mean unknown,
not that none exist. Review the **Source** tab's attribution and use notice.
Open Food Facts notices retain ODbL/DbCL attribution; USDA records retain their
source declaration. Display here grants no additional image, trademark or
redistribution rights. An OffMenu fallback logo is not a product photograph.

If **Review selected source in kitchen ↗** appears, it carries the selected
source reference to kitchen review. It does not establish ingredient use or
perform an inventory change.

## Pause, finish or recover

**Pause** suspends capture; **Resume** allows it again. Pause does not explicitly
release the camera stream. **Finish scanning** stops the camera and opens
**Current session**. Hiding or leaving the page also stops the camera; returning
to the visible page can attempt to reconnect while the session is active.
Use **Session → Choose mode** and its Enter button to start again after Finish.

Use **Inspect** on a session entry to revisit it. **Undo last** removes the last
capture event from this temporary session; it is not a pantry rollback. The
session is held in tab memory and is not a saved receipt or durable history.
Copy any information you need before reloading or leaving.

**Explore**, **Buy**, **Stock**, **Audit** and **Discard** describe intended
workflows. This visible retained-data connection records **0 real inventory
actions**: changing mode does not buy food, add stock, reconcile a lot or discard
anything. Inventory changes require separately verified eligibility and an
existing pantry action binding.

| Camera message or problem | Next step |
| --- | --- |
| Permission blocked | Allow camera access in this site's browser settings, then reopen the scanner. Type code remains available. |
| No camera / camera busy | Connect a camera or close other camera apps; use manual entry or a photo if needed. |
| Camera cannot use those settings | Choose another camera or setup. |
| No readable code / more than one barcode | Hold one complete code steady, adjust distance and glare, or use Type code/photo. |
| Decoder unavailable | Reconnect and reopen the camera, or type the printed code. |
| Camera disconnected | Reconnect it and reopen the scanner. |

**Check camera support** in Camera & sound settings reports browser/context and
stream facts. It does not test successful decoding, device reliability or
accessibility. For help reporting an issue or choosing main-app preferences,
see [support and optional-service preferences](support-preferences-guide.md).

## Source and maintenance

The OffMenu documentation owner should update this guide when scanner controls,
lookup states or action eligibility change. The [engineering decision](scanner-engineering.md)
contains historical implementation/testing context; this guide follows the wired
entrypoint at the revision above.

- [Visible controls and labels](../apps/web/assets/shelf-scanner.html).
- [Sessions, modes, manual entry and result readouts](../apps/web/src/shelf-scanner.js).
- [Camera lifecycle, photo handling and supported controls](../apps/web/src/scanner-ui.js).
- [Read agreement and camera errors](../apps/web/src/scanner-model.js).
- [Retail decoding](../apps/web/src/scanner-decode.js).
- [Capture representation checks](../apps/web/src/scanner-capture-envelope.js).
- [Retained source lookup and detail selection](../apps/web/src/scanner-identifiers.js),
  [selected-release requests](../apps/web/src/scanner-identity-v2.js).
- [Product visual captions and fallback](../apps/web/src/scanner-product-visuals.js).
- [Language initialization](../apps/web/src/i18n.js) and
  [scanner build entrypoint](../scripts/build.mjs).
