# Style Guide

The web app follows the visual language of [tryalma.com](https://www.tryalma.com), sampled from the home, get-started, pricing, lawyers, visa (O-1A) and blog pages at desktop and phone widths, with values read from the site's own CSS variables and computed styles. It borrows the palette, type scale, shapes and component patterns, not Alma's logo or wordmark.

All tokens live in [`frontend/src/app/globals.css`](../frontend/src/app/globals.css) (Tailwind v4 `@theme`), so components use names like `bg-accent` or `text-muted`, never raw hex values.

## 1. Principles

- **Warm, calm, confident.** Cream pages, soft green panels, generous whitespace. Nothing shouts except the one primary action.
- **Green means brand and progress.** Deep pine for brand text, sage for the primary action, moss for quieter actions.
- **Cards on cream.** Content sits on white cards with a soft, green-tinted shadow; grouped items sit in light-grey panels inside a card.
- **Small bold labels, large calm headings.** Uppercase eyebrow labels (bold, tracked) introduce medium-weight, tightly tracked headings.

## 2. Color

### Brand

| Token | Hex | Use |
|---|---|---|
| `brand` (pine) | `#054D2A` | Brand wordmark, heading highlights, eyebrow text, the "done" status pill |
| `accent` (sage) | `#207460` | Primary buttons, links, focus rings, check icons |
| `accent-hover` (pine deep) | `#1A4731` | Hover/pressed state of `accent` |
| `moss` | `#2F5B50` | Secondary buttons (outline), nav links, compact buttons |

### Surfaces

| Token | Hex | Use |
|---|---|---|
| `paper` (cream) | `#FFF7EE` | Page background, header |
| `surface` | `#FFFFFF` | Cards, inputs |
| `apple` | `#E0F0BC` | Hero / intro panels (the big light-green blocks) |
| `apple-soft` | `#F3F9E4` | Hover tint, selected rows |
| `panel` | `#F3F3F3` | Grey panels nested inside a card, segmented-control track, upload button |

### Text and lines

| Token | Hex | Use |
|---|---|---|
| `ink` | `#000000` | Headings and body text |
| `ink-soft` | `#3A3B3B` | Secondary body text |
| `muted` | `#6B6B72` | Hints, placeholders, metadata, table headers (5:1 on cream) |
| `line` | `#E7E8E3` | Borders, dividers, input outlines |

### Status

| Token | Background / text | Use |
|---|---|---|
| `honey` | `#FBE5C2` / `#8C5A12` | Waiting on us: **Pending** |
| `brand` | `#054D2A` / white | Done: **Reached out** |
| `danger` | `#FEF3F2` / `#B42318` | Errors |

## 3. Typography

**Typeface:** [Figtree](https://fonts.google.com/specimen/Figtree) (400, 500, 600, 700), a free geometric sans standing in for Alma's licensed Gellix. Loaded with `next/font`, so it's self-hosted and doesn't shift layout. Fallback: Arial, sans-serif.

| Style | Size | Weight | Tracking | Line height | Use |
|---|---|---|---|---|---|
| Display | 40–56px | 500 | −0.035em | 1.1 | Page hero heading (`/apply`) |
| H1 | 28–36px | 500 | −0.03em | 1.15 | Page titles |
| H2 | 22–24px | 500–600 | −0.025em | 1.2 | Card titles, section titles |
| Lead | 17–20px | 400 | normal | 1.45 | Intro paragraph under a heading |
| Body | 15–16px | 400 | normal | 1.5 | Default |
| Small | 13–14px | 400 | normal | 1.45 | Hints, metadata |
| Eyebrow | 11–12px | 700 | 0.12em, uppercase | 1.4 | Section labels, with a 6px dot |
| Table header | 11px | 700 | 0.08em, uppercase | 1.3 | Column headings, `muted` |

Headings use `font-medium tracking-heading` (−0.03em); a second line or key phrase may be colored `brand` (the site's "Hire the best talent. **We'll handle immigration.**" pattern).

## 4. Shape, space, depth

- **Radius:** 6px inputs and compact buttons, 12px primary buttons and rows, 16px cards, 24px large panels, full pills for badges.
- **Spacing:** 4 / 8 / 16 / 32 / 48 / 64px steps. Cards pad 20–40px depending on width; hero panels pad 48–80px on desktop.
- **Shadows:**
  - `shadow-card`: `0 1px 2px rgb(0 0 0 / 0.04), 0 24px 60px -20px rgb(5 77 42 / 0.15)` for primary cards.
  - `shadow-row`: `0 2px 4px rgb(0 0 0 / 0.04)` for rows or the active segment in a segmented control.
- **Borders:** 1px `line`; cards may use `1px rgb(0 0 0 / 0.06)` together with `shadow-card`.

## 5. Components

**Buttons**

| Variant | Style | Use |
|---|---|---|
| Primary | `bg-accent text-white`, 12px radius, 14×24px padding, 16px/500, hover `accent-hover` | The one main action on a page (Submit, Sign in) |
| Compact | `bg-moss text-white`, 6px radius, 8×14px padding, 14px/500 | In-row or secondary actions (Mark as reached out) |
| Outline | transparent, `1px moss` border, `text-moss`, 6px radius | Low-emphasis actions (Sign out) |
| Link | `text-accent`, underline on hover | Inline navigation |

**Form fields:** white, 1px `line` border, 6px radius, 12px padding, 15–16px text, `muted` placeholder. Focus: `accent` border plus a 3px `accent/20` ring. Errors: `danger` border and a message below. Labels are 14px/500 above the field.

**File upload:** a `panel` grey drop area with an upload icon and "Upload resume or CV", the size limit in `muted` below. Hover tints to `apple-soft`.

**Cards:** `bg-surface`, 16px radius, `shadow-card`. A card's title is H2.

**Hero / intro panel:** `bg-apple`, 16–24px radius, holding the eyebrow, a display heading and a short checklist. On desktop it sits beside the white form card (the get-started layout); on phones they stack.

**Eyebrow:** 6px `moss` dot, then the label in `brand`, uppercase, 700, tracked.

**Status badge:** pill, 12px/600, 4×10px padding: Pending = `honey`, Reached out = `brand` with white text.

**Segmented control (filters):** `panel` track with 4px padding; the active segment is `surface` with `shadow-row` and `ink` text; inactive segments are `ink-soft`.

**Table:** in a card; header row has no fill, just `line` below and table-header text; rows divided by `line`, hover `apple-soft`; name in `ink` 500, other cells `ink-soft`.

**Checklist item:** 20px rounded-square `accent` tile with a white check, then the text.

**Header (dashboard):** `paper` background, `line` bottom border; wordmark in `brand`, 500, tight tracking; nav actions in `moss`.

## 6. Accessibility

- Text colors meet WCAG AA on their backgrounds: `ink`, `ink-soft` and `muted` on cream and white; white on `accent`, `moss` and `brand`; `#8C5A12` on `honey`.
- Every interactive element keeps a visible focus style (2px `accent` outline, 2px offset).
- Status is never shown by color alone: badges always carry their label.
