---
name: OffMenu
description: Cinematic Glass for the OffMenu kitchen, scanner and food-data workspace.
colors:
  canvas: "#d9efda"
  paper: "#f7fbf8"
  surface: "#f9fcf9"
  raised: "#e3ede5"
  home-ink: "#214638"
  forest: "#183f35"
  muted: "#4b6256"
  line: "#b9cabd"
  coral: "#f3b09a"
  action: "#2865b5"
  accent: "#81552b"
  signboard: "#02050a"
  neon-blue: "#5da2ff"
  neon-white: "#f2f5f0"
  camera-frame: "#081719"
  camera-raised: "#091322"
  camera-panel: "#071c22"
  camera-guide: "#0a2732"
  camera-line: "#c0d6e39c"
  camera-copy: "#e8f4ee"
  camera-copy-strong: "#f5fff9"
  register-case: "#54715c"
  register-display: "#203e32"
  register-phosphor: "#e0edbb"
  scanner-confirmation: "#6affb7"
  danger: "#9c351f"
  warning-surface: "#efe4ca"
  error-surface: "#f4dfd1"
  print-paper: "#fffdf5"
  print-ink: "#000000"
  dark-canvas: "#081413"
  dark-paper: "#112321"
  dark-mint: "#1b332d"
  dark-ink: "#e1f4e9"
  dark-muted: "#b1c9bb"
  dark-line: "#45665b"
  dark-coral: "#ffc2a8"
  dark-on-ink: "#0b2018"
  dark-selected: "#a5dfc4"
  dark-focus: "#ffc2a8"
  dark-danger: "#ffc2af"
typography:
  landing-display:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "8.5rem"
    fontWeight: 800
    lineHeight: 0.97
    letterSpacing: "-0.04em"
  body:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.4
  compact:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: 1.4
  control:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  title:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.2
  section:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "24px"
    fontWeight: 800
    lineHeight: 1.15
  heading:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "30px"
    fontWeight: 800
    lineHeight: 1.15
  page-heading:
    fontFamily: "Avenir Next, Segoe UI, sans-serif"
    fontSize: "36px"
    fontWeight: 800
    lineHeight: 1.15
  scanner:
    fontFamily: "OffMenuRoboto, Avenir Next, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  emphasis:
    fontFamily: "Georgia, serif"
    fontWeight: 400
rounded:
  xs: "4px"
  tight: "8px"
  sm: "10px"
  compact: "12px"
  md: "16px"
  lg: "18px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  compact: "12px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  2xl: "48px"
  3xl: "64px"
components:
  button-primary:
    backgroundColor: "{colors.coral}"
    textColor: "{colors.home-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "12px 22px"
    height: "46px"
  button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.home-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "12px 22px"
    height: "46px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.home-ink}"
    rounded: "{rounded.lg}"
    padding: "clamp(20px, 3vw, 32px)"
  input:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.home-ink}"
    rounded: "{rounded.sm}"
    padding: "12px"
    height: "56px"
---

## Overview

**Creative North Star: "The bright pantry, lit by a real scanner sign."** OffMenu opens with the original animated blue-bracket, white-glass barcode-bowl sign centred on an almost-black signboard. The sign and the motto “From product to pantry to plate” share the full opening viewport. The kitchen fills the viewport in daylight green or dark evergreen. The identity feels like a practical kitchen tool that happens to have a luminous after-hours window, never a generic grocery template.

**Key Characteristics:**

- Full-width household panes in daylight green and dark evergreen.
- Home-green type, warm paper layers and a pale-coral landing action.
- The original animated blue-bracket, white-glass barcode-bowl sign is the product mark everywhere a logo appears.
- Motion is purposeful: the sign energises once, its steam only moves while visible, and every reduced-motion path is still and complete.

## Colors

The palette pairs an unmistakably green work surface with quiet paper layers and a cool electric brand signature.

### Primary

- **Pale Coral:** the landing's committed first action is warm and direct against the dark signboard.
- **Scanner Blue:** the sign's blue scanner brackets and selected operational actions use blue sparingly, legibly and functionally.

### Secondary

- **Pantry Brown:** the warm accent is reserved for highlighted food moments and supporting emphasis, never a competing call to action.

### Neutral

- **Visible Green Canvas:** the app's base field must read as light green at a glance, not as cream or white.
- **Paper Surface:** clean, almost-white panels separate detailed tasks from the canvas.
- **Forest Ink and Soft Green Ink:** dark readable type and quieter supporting copy preserve the calm, practical tone.
- **Neon White:** use on the glowing barcode bowl and on dark sign surfaces, not as a replacement for the light workspace canvas.
- **Camera and register darks:** camera-frame, raised, panel and guide colors are named scanner roles; register case, display and phosphor colors are named checkout roles. They are operational exceptions, not a second general page palette.
- **Status and print:** scanner confirmation, warning, error, danger and print-paper/print-ink each have explicit roles so receipts and state messages stay clear without arbitrary one-off colors.

**The Green-First Rule.** The default light surface is the visible green canvas; a neutral cream or near-white page background is not an OffMenu substitute.

Dark mode uses evergreen canvas, lighter evergreen panels and pale ink. The appearance choice carries across the kitchen, scanner, data workspace and Help. The retailer popup follows the operating system.

The shared palette, control radius and fast easing live in the reusable stylesheet `@apps/web/assets/offmenu-tokens.css`. Load it before the surface stylesheet. The household app, data workspace, Help, scanner and retailer popup consume it. Surface palettes still decide which brand token to use for each role, including the scanner’s operational blues.

## Typography

**Display Font:** Avenir Next / Segoe UI sans stack, with heavy sans for the motto.

**Body Font:** Avenir Next / Segoe UI sans stack.

**Scanner Font:** OffMenuRoboto / Avenir Next / Segoe UI sans stack for the scanner's operational surface.

**Character:** compact, humanist system type makes dense household decisions easy to scan. The brand's expression lives in the neon illustration, not in a novelty display face.

### Hierarchy

- **Landing Display:** The motto uses weight 800, 0.97 line height and −0.04em tracking. Its responsive size ranges from 2.55rem on phones to 8.5rem on wide screens.
- **Headline:** clear section labels keep meal, inventory and shop content scannable.
- **Body:** comfortable 1rem copy at a 1.5 line height explains choices without becoming editorial prose.
- **Label:** small, high-weight labels identify controls, quantities and current state.

The supported reading scale is 12, 14, 15, 16, 18, 24, 30 and 36 pixels. Use compact text for labels and supporting state only; body-sized UI remains at least 15 pixels, and editable controls stay at 16 pixels.

**The Work-First Type Rule.** Let application language remain direct and readable; the sign carries the theatre.

## Layout

The landing, kitchen, data workspace and Help use the full browser width with shared gutters that scale from 16 to 64 pixels. Kitchen tabs stay reachable while scrolling. The scanner uses the dynamic viewport and reserves device safe areas. Cards group a decision or a short result; they do not become ornamental tiles. On narrow screens the tab row scrolls horizontally rather than compressing labels; panels lose gratuitous floating treatment and each task keeps one clear next step.

The landing pairs the motto and actions with the neon sign on desktop and stacks the sign above them on phones. The feature showcase opens working app views and reduces its columns to fit. The same sign remains recognisable at small sizes through the blue brackets and white bowl silhouette.

## Elevation & Depth

Working surfaces use borders and neutral elevation. The shared shadow uses a 14-pixel offset in light mode and an 18-pixel offset in dark mode. The dark neon stage earns a brighter glow; ordinary app cards do not. Focus is always a high-contrast outline, never shadow alone.

**The Sign Owns the Glow Rule.** The full animated sign belongs only to the landing stage. Kitchen, account and navigation surfaces use the compact static SVG mark; work surfaces communicate hierarchy with tone, border and quiet elevation.

## Shapes

The operating interface uses an intentional 4, 8, 10, 12, 16 and 18-pixel radius scale, with full pills reserved for compact status badges. Compact controls are 42 pixels tall, the landing action is 46 pixels and standard task controls are 56 pixels. Borders are calm green-grey hairlines. The logo is not redrawn as a boxed glyph, emoji, barcode tile or arbitrary icon: use the original blue-bracket and white-glass barcode-bowl asset.

## Motion & Micro-interaction

The neon sign ignites once. Steam runs while the sign is visible and the page is active. The pause button keeps a stable accessible label and exposes its pressed state. Reduced motion keeps the sign fully lit and still.

Kitchen tabs use a 250 ms native view transition where supported. Navigation applies immediately with reduced motion or when the API is unavailable. The completed receipt uses a 380 ms title settle and a 440 ms confirmation ring. Both cues are disabled in reduced motion.

## Voice & Content Strategy

Keep **From product to pantry to plate** as the exact landing motto. Name actions and their outcomes directly. Keep product identity, measured amounts, estimates and unknown values distinct. Localise complete messages and leave room for Arabic and right-to-left layouts.

## Components

### Buttons

- **Shape:** compactly rounded controls with a reliable 56-pixel touch height.
- **Primary:** Pale Coral carries the landing's committed action; it has home-green text and a light press scale.
- **Secondary:** a raised paper treatment supports choice without competing with the action.
- **Focus:** use the high-contrast focus outline with a visible offset.

### Cards / Containers

- **Corner Style:** gently rounded working surfaces.
- **Background:** paper surface on the green canvas, with a calm green-grey border.
- **Shadow Strategy:** shallow layered depth for interactive or elevated groups; omit unnecessary card shadows on mobile.
- **Internal Padding:** start at 20 pixels and expand with available space.

### Inputs / Fields

- **Style:** raised surface, green-grey stroke, 10-pixel corners and a 56-pixel minimum height.
- **Focus:** preserve the explicit focus outline; never rely only on a color shift.

### Navigation

- **Style:** direct, text-led navigation with a clear current-page fill and large tap targets.
- **Brand:** use the compact static SVG mark beside the OffMenu wordmark in kitchen, account and navigation contexts; do not fall back to old tile marks or unrelated icons.

### Appearance Toggle and Feature Showcase

Use a 44-pixel theme toggle with a stable label and pressed state. The app follows the system until the visitor chooses a theme. Use live, theme-aware content in the showcase. When a screenshot is needed, capture light and dark variants and match the image to the active theme.

### Dynamic Text and Controls

Use localizedElement from `@apps/web/src/ui-dom.js` for localized labels, headings and controls created in JavaScript. It assigns text safely, preserves the rendered language and lets the browser determine text direction. Pass a class only when the caller needs one. For example, create a button, then assign its type and click handler where the workflow is defined.

### OffMenu Neon Sign

The blue scanner brackets framing the white-glass barcode bowl are the signature component. The landing uses the full sign on a dark display field, with one shallow ignition sequence and steam only while visible. Pause it offscreen or when the document is hidden; respect reduced-motion preference with a complete static sign and preserve the SVG fallback if material loading fails. Elsewhere, use the compact static SVG counterpart.

## Do's and Don'ts

### Do:

- **Do** use the visible green canvas as the default light environment.
- **Do** use the original neon barcode-bowl sign anywhere a logo or branded identity is needed.
- **Do** keep controls explicit, high-contrast and comfortably tappable.
- **Do** give the neon sign a dark stage when it needs to glow, while keeping routine product work calm in both themes.

### Don't:

- **Don't** let the light background drift into cream, off-white or ambiguous near-white.
- **Don't** replace the logo with the former boxed mark, a barcode tile, emoji or generic food icon.
- **Don't** spread neon glow or continuous animation across ordinary task UI.
- **Don't** remove the reduced-motion, offscreen-pause or material-fallback behavior from the sign.
