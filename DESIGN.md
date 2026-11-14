---
name: Biblio AI Café Companion
description: The reading-room menu — a calm, editorial café companion in deep teal and cream.
colors:
  ink-teal: "#10302F"
  teal-deep: "#0E3B39"
  teal: "#1F5C57"
  teal-mist: "#DCE8E3"
  cream-page: "#FBF6EC"
  cream-card: "#F3EAD8"
  cream-line: "#E4D4B5"
  caramel: "#B9823F"
  muted-ink: "#5B6B66"
  success: "#2F6B4F"
  warning: "#8A5A12"
  danger: "#A63A2B"
typography:
  display:
    fontFamily: "Fraunces, Georgia, serif"
    fontSize: "clamp(2.25rem, 9vw, 3rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.01em"
  heading:
    fontFamily: "Fraunces, Georgia, serif"
    fontSize: "1.375rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "normal"
  section-label:
    fontFamily: "Be Vietnam Pro, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.08em"
  body:
    fontFamily: "Be Vietnam Pro, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  price:
    fontFamily: "Be Vietnam Pro, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  caption:
    fontFamily: "Be Vietnam Pro, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "6px"
  md: "12px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.teal}"
    textColor: "{colors.cream-page}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    padding: "12px 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.teal-deep}"
  button-secondary:
    backgroundColor: "{colors.cream-card}"
    textColor: "{colors.ink-teal}"
    rounded: "{rounded.pill}"
    padding: "12px 20px"
    height: "44px"
  chip:
    backgroundColor: "{colors.cream-card}"
    textColor: "{colors.ink-teal}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: "6px 12px"
  chip-selected:
    backgroundColor: "{colors.teal-mist}"
    textColor: "{colors.teal-deep}"
  card-index:
    backgroundColor: "{colors.cream-card}"
    textColor: "{colors.ink-teal}"
    rounded: "{rounded.md}"
    padding: "16px"
  slip:
    backgroundColor: "{colors.cream-page}"
    textColor: "{colors.ink-teal}"
    rounded: "{rounded.sm}"
    padding: "16px"
  input:
    backgroundColor: "{colors.cream-page}"
    textColor: "{colors.ink-teal}"
    rounded: "{rounded.md}"
    padding: "12px 14px"
    height: "44px"
  masthead:
    backgroundColor: "{colors.teal-deep}"
    textColor: "{colors.cream-page}"
    padding: "32px 16px"
---

# Design System: Biblio AI Café Companion

> Directional seed written before implementation (2026-11-14). After the UI exists, run `/impeccable document` in scan mode
> to refresh this file from the shipped code. Screen-level specs: `docs/ui-ux-spec.md`.

## Overview

**The reading-room menu.** Biblio is a large book café in a student village: reading rooms, co-working, meeting rooms, a
printed menu in deep teal on cream. The interface borrows from that world — library index cards, catalogue stamps, the dotted
leaders of a printed menu, paper order slips — and stays calm, legible and warm. The AI concierge is a quiet librarian at the
desk: always reachable, never covering the menu on desktop. Customer surfaces are **Operate** with brand expression (the Discover
masthead leans Persuade); Admin is pure **Operate**: scan speed over decoration. Light theme only.

## Colors

### Primary
- **Teal Deep `#0E3B39`** — masthead and dark surfaces. **Teal `#1F5C57`** — primary actions, focus ring, active states.
- **Ink Teal `#10302F`** — all body text on cream.

### Secondary
- **Caramel `#B9823F`** — accents only: the masthead rule, active tab underline, small icons. Never for body text (contrast).

### Neutral
- **Cream Page `#FBF6EC`** — page background. **Cream Card `#F3EAD8`** — cards, sheets, chips. **Cream Line `#E4D4B5`** — hairlines, borders, dotted leaders.
- **Muted Ink `#5B6B66`** — secondary text (≥4.5:1 on Cream Page). **Teal Mist `#DCE8E3`** — selected chips, highlight flash.

### Status
- Success `#2F6B4F` (ready/completed), Warning `#8A5A12` (unconfirmed availability/price), Danger `#A63A2B` (sold out, rejected, errors).

### Named Rules
- **Data honesty colour**: anything unverified (availability "Chưa xác nhận", price notice) uses Muted Ink or Warning — never Success.
- **No gradients, no glass, no neon.** Flat paper colours only.

## Typography

Fraunces (display/headings, variable optical size) + Be Vietnam Pro (UI/body; designed for Vietnamese diacritics), both
self-hosted via `@fontsource/*` (offline-safe). If the Fraunces package lacks the Vietnamese subset, use Be Vietnam Pro 600 for
display and keep Fraunces only for Latin-only words ("BIBLIO").

### Hierarchy
- Display (masthead "BIBLIO"): Fraunces 600, clamp(2.25rem, 9vw, 3rem), tight leading.
- Heading (screen/section titles): Fraunces 600, 1.375rem.
- Section label (menu category, column headers): Be Vietnam Pro 600, 0.8125rem, uppercase, +0.08em tracking.
- Body: Be Vietnam Pro 400, 1rem/1.55. Caption: 0.8125rem.
- Price: Be Vietnam Pro 600 with `font-variant-numeric: tabular-nums`; format `45.000đ`.

### Named Rules
- **Prices align**: tabular numerals, right-aligned, joined to names by a dotted leader in Cream Line.
- Never more than two typefaces; never all-caps body text.

## Layout

Mobile-first customer app (360–430 px) with a 16 px gutter and bottom tab bar (Khám phá · Menu · Trợ lý · Giỏ). At ≥1024 px the
chat becomes a fixed 400 px right column and the content area keeps the menu usable. Admin is desktop-first (≥1280 px, usable at
1024 px): top bar + status columns. Spacing scale 4/8/16/24/32/48; vertical rhythm in multiples of 8. Touch targets ≥44 px.

## Elevation & Depth

Mostly flat paper. One shadow for floating paper (order slips, sheets): `0 1px 0 #E4D4B5, 0 8px 24px rgb(16 48 47 / 0.08)`.
Sheets get a scrim `rgb(16 48 47 / 0.35)`. No other shadows.

## Shapes

Radii: 6 px (slips, small controls), 12 px (cards, inputs, sheets), pill (buttons, chips). Order slips have a perforated top and
bottom edge (CSS radial-gradient mask), the signature shape of the system.

## Components

### Buttons
Primary: Teal fill, cream text, pill, 44 px. Secondary: Cream Card fill, ink text. Destructive actions (Từ chối, Hủy đơn) use a
Danger outline, never a filled red button. Loading: inline spinner + disabled, label unchanged.

### Chips
Category tabs, price filters, suggestion chips, tool-activity chips. Selected = Teal Mist fill. Tool chips carry a 20 px orb
while running and a check/cross when finished.

### Cards / Containers
**Index card** (Discover highlights): Cream Card, 12 px radius, a small "catalogue stamp" source label (e.g. `Google Maps`,
`Bảng giá tại quán`). **Menu row**: name · dotted leader · price; availability line beneath in caption size.

### Inputs / Fields
Cream Page fill, Cream Line border, 12 px radius, 44 px; focus = 2 px Teal outline offset 2 px; errors in Danger below the field
via `aria-describedby`.

### Navigation
Customer: bottom tab bar with Caramel underline for the active tab. Admin: top bar with text tabs and a live-connection dot.

### Signature Components
- **Order slip** — draft card (Đơn nháp: lines, total, warnings, **Xác nhận đặt món** / **Bỏ qua**) and admin order cards.
- **Concierge orb** — `thinking-orbs` `ThinkingOrb` (64 px header, 20 px in chips), `theme="light"`, state mapped strictly from the
  backend `agent_state` (`idle→breathing, thinking→connecting, searching→searching, working→working, composing→composing,
  error→breathing+paused`), `aria-label` = Vietnamese state label.

### Motion
GSAP 3.15 via `@gsap/react` `useGSAP`; transforms/opacity only; 150–260 ms, `power2.out`; masthead stagger once per load;
admin new-slip highlight 1.2 s. Under `prefers-reduced-motion: reduce`, `gsap.matchMedia()` sets end states without tweening.

## Do's and Don'ts

### Do:
- Show the source and date next to facts that come from the knowledge base or photos.
- Label unverified data plainly ("Chưa xác nhận còn món", "Giá theo menu 14/11/2026 — chờ quán xác nhận").
- Keep the menu usable while the assistant is open (desktop side panel; mobile sheet with clear close).
- Use the orb only as a truthful status indicator.
- Announce completed assistant messages and new admin orders through `aria-live` regions.

### Don't:
- Don't use emoji as icons, gradients, glassmorphism, neon accents or SaaS dashboard tiles.
- Don't animate layout properties, parallax, or scroll-jack; don't delay input for motion.
- Don't show inferred menu tags as facts (only "Gợi ý theo tên món" in the item sheet).
- Don't put the Wi-Fi password, prices or stock claims anywhere they are not backed by data.
- Don't let a fake/timer-driven loading animation imply the agent is working.
