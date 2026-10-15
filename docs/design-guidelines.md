# Design Guidelines

Principle: **simple, clean, and calm.** White pages, lots of whitespace, one obvious main action per screen. Orange is the brand color, used as an accent, not as large fills.

## 1. Colors

All colors are CSS variables in `static/css/app.css`. Do not hard-code hex values elsewhere.

| Token | Hex | Use |
|---|---|---|
| `--primary` | `#f97316` | Brand accent: logo mark, focus ring, card hover border, small highlights |
| `--primary-light` | `#fff4eb` | Active nav tab, active chip, hover backgrounds, dashed boxes |
| `--primary-dark` | `#c2410c` | Primary buttons and links (white text on it passes WCAG AA, 5.2:1) |
| `--ink` | `#7c2d12` | Text placed **on** `--primary-light` (never white text on `#f97316`: contrast too low) |
| `--text` | `#1f2937` | Headings and body text |
| `--muted` | `#6b7280` | Secondary text, captions, inactive nav tabs |
| `--bg` | `#ffffff` | Page background |
| `--surface-soft` | `#fafaf9` | Card insets, code/formula boxes |
| `--border` | `#e7e5e4` | Header line, card and input borders |
| `--danger` | `#dc2626` | Errors, delete buttons |
| `--success` | `#15803d` | Success messages, "Accepted answer" badge |

## 2. Typography
- Font: system stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`)
- Sizes: hero title 40px bold, page title 32px bold, section title 20px semibold, body 16px, caption 14px
- Line height: 1.5

## 3. Layout & spacing
- Desktop only. Max content width 1100px, centered, 24px side padding.
- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48px

## 4. Components
- **Header**: white, thin bottom border. Left: orange rounded-square logo mark with a white Σ, then a bold "MathInteract" wordmark. Middle: tabs **Home · US · Canada · IB · OSSD · Weekly Problem · Q&A**. Active tab: rounded pill, `--primary-light` background, `--ink` text; inactive: `--muted`. Right: "Log in" (text link) + "Sign up" (primary button), or the username + "Log out".
- **Hero**: big bold centered title, one muted subtitle line.
- **Button (primary)**: `--primary-dark` background, white text, 10px radius.
- **Button (secondary)**: white background, `--text` label, 1.5px `--border` border, 10px radius.
- **Card**: white, 14px radius, 1px `--border`; hover lifts slightly and the border turns `--primary`.
- **Entry card** (home): icon in a `--primary-light` circle, title, one-line description.
- **Chips** (filters, tags): rounded-full. Inactive: white with a `--border` border. Active: `--primary-light` background, `--ink` text.
- **Form**: centered card 400px wide; labels above inputs; inputs 1px `--border`, 10px radius, orange focus ring; errors in `--danger` under the form.
- **Dashed box** (empty states, upload zone): 1.5px dashed `--border`, `--primary-light` background, 14px radius.

## 5. Copy (English)
- Short and plain: "This username is taken. Please choose another.", "No resources yet."
- Sentence case for buttons and titles.
- Use official contest names (AMC 10, Euclid, CMO…).

## 6. Accessibility
- Text contrast ≥ 4.5:1.
- Every image has `alt` text.
- Buttons, links, and inputs are keyboard-focusable with a visible `--primary` focus ring.
- Every input has a `<label>`.
