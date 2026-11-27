---
version: alpha
colors:
  background: "hsl(221 42% 7%)"
  foreground: "hsl(214 24% 96%)"
  panel: "hsl(221 29% 12%)"
  accent: "hsl(39 94% 63%)"
  success: "#45d483"
  danger: "#ff6b6b"
typography:
  interface:
    fontFamily: "var(--font-sans), sans-serif"
  evidence:
    fontFamily: "var(--font-mono), monospace"
rounded:
  card: "1rem"
  control: "1rem"
spacing:
  page: "1.5rem"
  section: "1.5rem"
components:
  evidence-card:
    backgroundColor: "panel"
  replay-result:
    fontFamily: "evidence"
---

## Overview

MetricTrace is a dark, evidence-led operational product for engineers and data
teams reconstructing a reported number. Its signature is the replay grid: a
compact forensic instrument rather than a generic analytics dashboard. Runtime
CSS variables in `frontend/src/app/globals.css` are the canonical source;
this file mirrors their accepted semantic roles.

## Colors

Deep blue-black surfaces keep attention on evidence. Amber is reserved for
primary action and historical focus; green and red communicate completed and
failed execution states, never decoration.

## Typography

Space Grotesk is the interface voice. JetBrains Mono is reserved for IDs,
metric results and execution evidence so values read as inspectable artifacts.

## Layout

Use dense but breathable cards with a 24px page rhythm. Tables preserve their
tabular form with horizontal overflow on narrow screens; never hide replay
inputs that change the result.

## Elevation & Depth

Panels use a faint border and restrained global shadow. Avoid extra floating
elements: provenance should feel stable, not decorative.

## Shapes

Cards and controls use the shared rounded family. Badges remain compact and
semantic.

## Components

Use existing shared Card, Button and Badge primitives. A replay result always
shows a cell status; a failed cell displays its error instead of a replacement
number.

## Do's and Don'ts

Do make exact inputs and states visible. Do preserve keyboard-focus styling.
Do not invent progress percentages for a synchronous replay. Do not style an
unverified or missing value as a successful metric.
