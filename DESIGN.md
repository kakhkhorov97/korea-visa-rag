---
name: Korea Visa Assistant
description: A bilingual question workspace with official evidence beside the answer.
colors:
  ink: "#152238"
  muted: "#5a6572"
  line: "#dfe3e5"
  ground: "#f7f7f4"
  surface: "#fff"
  rail: "#12283d"
  rail-text: "#f4f7fc"
  rail-muted: "#b5c5d7"
  rail-selected: "#284970"
  accent: "#0759df"
  accent-hover: "#0645ab"
  accent-soft: "#e8f0fd"
  sage: "#eaf0e7"
  sage-ink: "#344b3c"
  ok: "#24733c"
typography:
  display:
    fontFamily: "Newsreader, Georgia, serif"
    fontSize: "clamp(27px, 2.5vw, 38px)"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-.025em"
  headline:
    fontFamily: "Newsreader, Georgia, serif"
    fontSize: "clamp(23px, 2.1vw, 32px)"
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: "-.025em"
  title:
    fontFamily: "IBM Plex Sans KR, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.6
  body:
    fontFamily: "IBM Plex Sans KR, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.6
  answer:
    fontFamily: "IBM Plex Sans KR, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.8
  label:
    fontFamily: "IBM Plex Sans KR, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  citation: "3px"
  small: "6px"
  control: "7px"
  action: "8px"
  source: "9px"
  panel: "12px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  xxl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.action}"
    width: "48px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-topic:
    backgroundColor: "transparent"
    textColor: "{colors.rail-text}"
    rounded: "{rounded.small}"
    padding: "12px 8px"
  navigation:
    backgroundColor: "{colors.rail-selected}"
    textColor: "{colors.surface}"
    rounded: "{rounded.action}"
    padding: "14px"
  mode-selected:
    backgroundColor: "{colors.rail-selected}"
    textColor: "{colors.rail-text}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  citation:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.citation}"
    padding: "2px 5px"
  answer-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "24px"
  source-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.source}"
    padding: "16px"
  composer:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "12px"
  status:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
---

# Design System: Korea Visa Assistant

## Overview

**Creative North Star: "The bilingual evidence workspace"**

The approved workspace uses an ink-blue navigation rail, warm stone ground, white answer cards and a sage evidence panel. Blue identifies actions and citations. Original passages remain visually distinct from generated answers.

Humanist sans-serif text supports English and Korean reading. Modest serif headings mark the question workspace and its evidence area. Borders and background changes separate content without floating cards.

**Key Characteristics:**

- Ink-blue navigation and blue actions.
- White answers beside sage evidence.
- Serif headings with bilingual sans-serif reading text.

## Colors

The primary blue marks interaction; ink, stone and sage organize the reading workspace. Frontmatter contains the normative values, extracted from `web/styles.css`.

### Primary

- Action blue (`accent`) colors send controls, links, citations and focus outlines. `accent-hover` deepens interactive states; `accent-soft` supports citations and user messages.

### Secondary

- Evidence sage (`sage`) distinguishes the evidence panel; `sage-ink` supports its text.
- Status green (`ok`) appears in the availability dot with an explicit status label.

### Neutral

- Reading ink (`ink`) and muted slate (`muted`) separate main text from metadata.
- Stone ground (`ground`), white (`surface`) and the divider (`line`) separate the workspace and its cards.
- Navigation ink (`rail`) carries pale text (`rail-text`), muted labels (`rail-muted`) and selected rows (`rail-selected`).

**The Evidence Separation Rule.** Use the sage panel for original sources and white cards for answers.

## Typography

Newsreader with Georgia fallback is the display family. IBM Plex Sans KR with system sans-serif fallback is the reading family. Newsreader is bundled locally; IBM Plex Sans KR loads through Google Fonts.

The display and headline roles belong to the introduction and evidence headings. The title role marks answer headings. Body text uses the body role; answers use the larger answer role with a maximum width of 72ch. Metadata and source links use the label scale. Original passages use the reading family, preserve line breaks and use a line height of 1.8.

At the mobile breakpoint, the introductory heading becomes 31px, the evidence heading 27px and answer text 14px. Composer text remains 16px. Sidebar section labels use uppercase text with .09em tracking; this treatment is limited to navigation settings.

## Layout

Desktop uses a full-height shell with a rail sized by `clamp(250px, 20vw, 308px)`. The top bar is 74px high. The workspace uses a flexible answer column and an evidence column of `minmax(280px, 35%)`, with 24px gaps. The evidence panel spans the introduction and conversation rows; the composer spans both columns. Conversations and evidence scroll independently.

At 1100px and below, workspace gaps and answer padding become 20px and the evidence column becomes 280px. Language text in the status bar hides. At 1800px and above, horizontal workspace padding becomes 48px and evidence width becomes 380px.

At 900px and below, the page becomes a single scrolling column. A 64px sticky bar replaces the desktop header; the rail becomes a fixed disclosure below it, at most 300px or 88vw wide. Evidence follows the conversation. The composer sticks to the bottom with safe-area padding. Opening settings makes the content inert; Escape closes settings and returns focus to its toggle. Replies scroll into view only while the visitor remains at the current reply.

## Elevation & Depth

Background changes and thin borders provide ordinary depth. Answer cards have a divider-colored border; source cards sit on the sage panel without shadows. The only structural shadow belongs to the mobile settings drawer, `10px 20px 40px #12283d33`.

Transitions use 160ms ease-out for color and background changes. The loading ring rotates over 900ms. Reduced-motion preferences disable animation, transitions and smooth scrolling.

## Shapes

Rounded rectangles distinguish panels, source cards and controls. Small citations use the tightest radius. User messages use an asymmetric lower-right corner of 3px; their other corners use the panel radius. Document icons use thin outline SVG paths. Status dots are circles. Avoid adding decorative framing to passages or answers.

## Components

### Buttons

The square send button uses the primary action token and a centered outline SVG. Hover uses the darker action blue. Disabled controls retain their shape with .55 opacity and a not-allowed cursor. Text topic buttons fill their row on hover. Keyboard focus uses a visible 3px outline with a 4px offset; rail controls use a pale-blue outline.

### Chips

Numbered citations are compact buttons in the answer text. Their pale-blue fill darkens on hover. Activation opens the corresponding source and moves focus to its summary. Only valid retrieved source numbers become interactive citations.

### Cards / Containers

Answer cards use the answer-card token with a thin border. Their heading, answer, source links and search metadata form a reading sequence. Paragraphs and lists retain separate blocks. Source cards use native disclosures with a numbered badge, title, citation status and plus/minus indicator. Expanded passages have a pale sage inset, preserved line breaks and a scroll limit of 260px.

### Inputs / Fields

The composer wraps a borderless growing textarea and the send button in a bordered white container. It gains a blue border and pale-blue outer outline on focus within. The textarea grows to 112px. Enter submits; Shift+Enter inserts a line break. Selected search methods use a filled rail row and a radio indicator. Unavailable methods remain visible and disabled.

### Navigation

The rail pairs the bilingual brand with an active question button, radio search methods and topic shortcuts. Its mobile disclosure preserves the same controls. The status bar uses a colored dot plus text; availability does not rely on color alone.

## Do's and Don'ts

### Do:

- Do use blue for actions, citations and focus indicators.
- Do keep original passages visually separate from answer prose.
- Do preserve visible keyboard focus and reduced-motion behavior.
- Do stack evidence after the conversation on small screens.

### Don't:

- Don't apply shadows to ordinary answer or source cards.
- Don't replace the reading font with the display serif.
- Don't use status color without its accompanying text.
