# Scan a barcode and inspect its source information

This guide describes the standalone scanner in OffMenu source
`56026538d15d29f6f5afd427294a82be69557908`. Camera performance,
assistive-technology behavior and the installed experience are not verified.

The scanner uses the shared **Interface language** choice for English or
Arabic. The control names below are English source wording; some labels or
statuses may fall back to English. The interface language does not change
the printed code.

## Open the scanner and present one item

1. Open the standalone scanner at **/shelf-scanner.html**. It may ask for
   camera access. Allow it only if you want to scan with your camera. Use
   **Type code** if the camera is unavailable or you prefer not to grant access.
   **Retry camera** makes a separate attempt; it cannot override a denial.
   Camera use requires a secure context such as the installation's HTTPS address.
2. The initial setup is **Handheld · rear camera**. Keep the whole barcode,
   including its blank edges, inside the aiming guide. Start around 15–30 cm
   away, hold still briefly and move farther away if the bars look blurred.
   Tilt shiny packaging away from glare. This distance is a starting suggestion,
   not a measured limit for your device.
3. Present one barcode at a time. Live reading requires agreeing frames; an
   camera read means a code was captured, not that a product was identified.
   Read the separate lookup status before relying on product information.
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

If you cannot use the camera or do not want to give it permission, choose
**Type code**. You can also open **Scanner options** and choose **Type code**
there.

1. In **Original identifier**, enter the printed code exactly, including any
   leading zeros. The field accepts up to 128 printable characters.
2. Use **Barcode · printed code**. Leave **Barcode representation hint** at
   **No hint · exact lexical lookup** unless you know the format. Eight digits
   alone do not establish UPC-E.
3. Choose **Search for this code**. If the scanner shows **Lookup unavailable**,
   OffMenu could not check the code. That is not a no-match result and it does
   not add anything to your pantry.
4. To leave the form without submitting, choose **Cancel**.

You can also expand **Scan a barcode photo on this device** and choose a
**Barcode image** up to 20,000,000 bytes. Use a clear photo of one complete
barcode, including blank edges. A decoder notice may ask you to confirm the
printed code. Do not guess missing digits or a format.

The current scanner decodes preview frames and chosen images locally. An image
read or captured code does not qualify a product, and the public catalogue is
unavailable in this source. Do not treat being online as a fix for that status.
USB/Bluetooth keyboard input and phone/device compatibility were not verified
by this guide.

## Read a result without filling in the unknowns

Open **Product details** to expand the sheet and read the reported status.
On a narrow screen the fully expanded sheet can pause new camera reads until
you lower it. The readout includes **Overview**, **Ingredients**, **Nutrition**
and **Source**. Available data depends on what has actually been established.

The current public scanner reports **Lookup unavailable**. Capturing or
typing a barcode does not establish product identity, ingredients, package or
serving size, stock or an inventory change. A blank or unavailable detail is
unknown, not evidence that a nutrient, allergen or record is absent.

When you have separately eligible source information, check its edition,
attribution and licence. Do not treat the absence of a displayed claim as
certification, or assume that a label or image comes with reuse rights.
A separately authorized retained-source workflow is not a public fallback
from this page.

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

**Explore**, **Buy**, **Stock**, **Audit** and **Discard** are scanner modes.
Changing mode does not buy food, add stock, reconcile a lot or discard anything.
A session item is not a pantry entry. For the separate checkout flow, see
[Type a barcode in Guest checkout](support/type-a-barcode-in-guest-checkout.md).

| Camera message or problem | Next step |
| --- | --- |
| Permission blocked | Choose **Type code** without granting access. If you decide to use the camera, check this site's browser permission, then choose **Retry camera**. |
| No camera / camera busy | Use **Type code** or choose a barcode photo. If you free a camera, **Retry camera** tries to start it again. |
| Camera cannot use those settings | Choose another camera or setup. |
| No readable code / more than one barcode | Hold one complete code steady, adjust distance and glare, or use Type code/photo. |
| Decoder unavailable | Reconnect and reopen the camera, or type the printed code. |
| Camera disconnected | Reconnect it and reopen the scanner. |

**Check camera support** in Camera & sound settings reports browser/context and
stream facts. It does not test successful decoding, device reliability or
accessibility. For help reporting an issue or choosing main-app preferences,
see [support and optional-service preferences](support-preferences-guide.md).

## Return to scanning or change its appearance

These additional control notes are checked separately at source
`0e0ceeec889251ab2c4ed01a5b5688ca9f736780`; they do not establish rendered,
camera or assistive-technology behavior on your device.

Open **Scanner tools** with the **⋯** button. Its light/dark button has the
accessible label **Switch light and dark mode**. It changes this scanner's theme
and attempts to save that choice on the device. This is separate from the
**Interface language** choice; neither is a product or inventory action.

**Back to scanner** closes the tools, expanded readout or current-session view.
It is a return action, not **Finish scanning**. Do not rely on closing one of
those views to stop capture; use **Pause** or **Finish scanning** for the
different behaviors described above.

In **Choose mode**, **Cancel** closes the options and attempts to start capture
in the current mode/connection. It is not a stop command or a rollback of every
setting: camera placement/lens and preview controls can already have applied
their changes. Use the selected **Enter** button when deliberately applying a
mode selection. If you intend to keep capture stopped, do not use Cancel as a
substitute for Finish.

The public catalogue is unavailable in this source; there is no public
provider selector or automatic fallback. Any retained, reviewed-file control
in source is not general import, backup or private-data access for visitors.

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
- [Public catalogue availability boundary](../apps/web/src/public-catalogue-boundary.js).
- [Product visual captions and fallback](../apps/web/src/scanner-product-visuals.js).
- [Language initialization](../apps/web/src/i18n.js) and
  [scanner build entrypoint](../scripts/build.mjs).
