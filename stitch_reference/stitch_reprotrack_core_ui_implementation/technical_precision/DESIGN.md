---
name: Technical Precision
colors:
  surface: '#f7f9fc'
  surface-dim: '#d8dadd'
  surface-bright: '#f7f9fc'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f7'
  surface-container: '#eceef1'
  surface-container-high: '#e6e8eb'
  surface-container-highest: '#e0e3e6'
  on-surface: '#191c1e'
  on-surface-variant: '#44474d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f4'
  outline: '#74777d'
  outline-variant: '#c4c6cd'
  surface-tint: '#4f5f77'
  primary: '#001125'
  on-primary: '#ffffff'
  primary-container: '#15263b'
  on-primary-container: '#7d8da7'
  inverse-primary: '#b7c8e3'
  secondary: '#47617b'
  on-secondary: '#ffffff'
  secondary-container: '#c5dfff'
  on-secondary-container: '#4a637e'
  tertiary: '#00140c'
  on-tertiary: '#ffffff'
  tertiary-container: '#002c1d'
  on-tertiary-container: '#09a075'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d3e4ff'
  primary-fixed-dim: '#b7c8e3'
  on-primary-fixed: '#0a1c31'
  on-primary-fixed-variant: '#37485e'
  secondary-fixed: '#cfe4ff'
  secondary-fixed-dim: '#afc9e8'
  on-secondary-fixed: '#001d34'
  on-secondary-fixed-variant: '#2f4962'
  tertiary-fixed: '#7ff9c7'
  tertiary-fixed-dim: '#61dcac'
  on-tertiary-fixed: '#002115'
  on-tertiary-fixed-variant: '#005139'
  background: '#f7f9fc'
  on-background: '#191c1e'
  surface-variant: '#e0e3e6'
typography:
  headline-xl:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-sm: 0.75rem
  gutter-lg: 1.5rem
  margin: 1.5rem
  margin-sm: 1rem
  margin-lg: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system serves a bug tracking, issue triage, and fix verification workspace where precision, high visual density, and instantaneous scan speed are critical. The aesthetic is rooted in modern, utilitarian enterprise software: authoritative, reliable, and noise-free.

### Brand Personality & Core Mood
- **Disciplined Precision:** The interface recedes into the background, prioritizing issue hierarchy, reproduction steps, and pipeline statuses without visual distraction.
- **Engineered Confidence:** Sturdy deep-navy anchors juxtaposed with crisp verification mint signal stability, systematic execution, and resolution.
- **High-Density Legibility:** Optimized for QA leads, test engineers, and developers who evaluate dense lists, stack traces, and verification matrices rapidly.

### Design Movement & Visual Language
The system combines modern corporate data density with subtle tactile cues. Crisp 1px slate borders, neutral matte backgrounds, controlled component radii, and muted tonal layers replace flashy ornamentation. Functional accents like severity and verification states deliver sharp semantic cues with strict accessibility compliance.

## Colors

The palette uses deep navy foundations for structural context, paired with action mint for workflows, approvals, and verified states. Functional colors enforce unmistakable severity and pipeline health.

### Core Roles
- **Primary Navy (`#15263B`):** Global navigation rails, header chrome, critical modals, and primary keylines.
- **Secondary Navy (`#213B54`):** Secondary navigation surfaces, selected item backgrounds, active row tints, and structural dividers.
- **Action Mint (`#36B78A`):** Positive verification actions, resolved bugs, primary completion buttons, and interactive verification highlights.
- **Canvas Base (`#F5F7FA`):** App background, workspace canvas, and side drawer backing.
- **Surface / Card (`#FFFFFF`):** High-priority work planes, bug detail panels, floating sheets, and dropdown menus.

### Typography & Structure
- **Main Text (`#1E293B`):** Headlines, bug summaries, issue keys, and field values.
- **Secondary Text (`#64748B`):** Metadata, timestamps, breadcrumbs, placeholder text, and subtle table column headers.
- **Border (`#E2E8F0`):** Table row dividers, input field boundaries, card outlines, and split-pane resizers.

### Status & Severity Badges
All status and severity chips use a structured tinted background with high-contrast text:
- **Success / Verified (`#198754`):** Closed tickets, passing tests, verified reproductions.
- **Warning / Blocked (`#D99000`):** Pending approvals, non-reproducible flags, medium severity warnings.
- **Error / Critical (`#DC3545`):** Blocker bugs, crash reports, regression failures, failed test runs.
- **Info / Triage (`#2673C8`):** Under review, backlog tickets, linked PRs, environment configuration data.

## Typography

The type system prioritizes high-density data legibility and effortless code/ID identification.

### Primary Font: Hanken Grotesk
Used for interface headers, body text, form fields, and modal messaging. Its geometric yet humanized grotesque structure ensures clean readability at 12px and 14px inside data grids and dense issue trees.

### Monospace / Technical Font: JetBrains Mono
Used across issue keys (e.g., `REP-1049`), git commit hashes, terminal logs, stack traces, and verification environment tags. Its strict horizontal rhythm and differentiated characters prevent misreading in code snippets and reproduction logs.

### Hierarchy & Usage Rules
- Issue keys and commit SHAs always render in `label-md` or `label-sm`.
- Table column headers rely on uppercase `label-sm` with letter spacing for unambiguous scanning across columns.
- Bug descriptions and reproduction step entries render in `body-md` with 20px line heights to keep dense documentation digestible.

## Layout & Spacing

The workspace uses a fluid split-pane layout to balance high-volume triage lists with detailed verification side-by-side.

### Grid & Layout Structure
- **Navigation Rail:** 64px collapsed icon rail or 240px expanded navigation tree fixed to the left edge.
- **Main Working Canvas:** Fluid grid adapting from 12 columns on desktop to full-width stacked panels on smaller viewports.
- **Split-Pane Architecture:** In issue triage mode, a 40/60 dual pane splits the bug list (40% width, min 360px) and the verification inspector (60% width, min 520px).

### Breakpoints & Adaptations
- **Desktop (1280px+):** Full 3-pane experience (Navigation, Filtered Issue Grid, Detail Inspector). Gutters at `1rem`, outer margins at `2rem`.
- **Tablet / Small Desktop (768px – 1279px):** Inspector transforms into an overlay drawer (`margin-sm: 1rem`), while issue tables retain dense horizontal layouts with horizontal scroll.
- **Mobile (<768px):** Single-column stacked workflow. Navigation converts to an app bar with off-canvas sheet; issue list and detail view switch via view toggles. Outer margins contract to `1rem`.

### Density Model
All component gaps adhere strictly to the 4px baseline. Table rows, metadata badges, and form controls leverage `space-xs` and `space-sm` for an efficient footprint without sacrificing touch or click accuracy.

## Elevation & Depth

This system avoids heavy drop shadows and dramatic skeuomorphism in favor of structural clarity: crisp 1px borders, subtle tonal contrast, and low-amplitude ambient diffusion.

### Depth Hierarchy
- **Level 0 (Canvas):** `#F5F7FA` base layer for canvas space, background scaffolding, and inert gutters.
- **Level 1 (Panels & Cards):** `#FFFFFF` surfaces with a 1px border of `#E2E8F0`. Shadows are suppressed; boundaries are defined solely by borders.
- **Level 2 (Hover States & Dropdowns):** Interactive rows and active menus gain an ultra-subtle diffuse elevation: `0 2px 6px -1px rgba(21, 38, 59, 0.08)`.
- **Level 3 (Modals & Verification Sheets):** Floating dialogue boxes, slide-over test runners, and context menus: `0 12px 28px -6px rgba(21, 38, 59, 0.16)`, bordered with `#E2E8F0`.

### Interaction Layers
Row hovers in tables and lists shift from `#FFFFFF` to `#F8FAFC`. Selected or active inspection targets receive an inset 2px border on their left margin using the primary mint `#36B78A`.

## Shapes

The design system uses a restrained corner radius (Level 1: Soft) to support an engineering-grade, structured tool aesthetic. 

### Corner Geometry
- **Standard Controls & Badges (0.25rem / 4px):** Applied to buttons, input fields, severity chips, code tags, dropdown buttons, and table row selections.
- **Cards, Panels & Modals (0.5rem / 8px):** Applied to issue detail cards, verification matrix panels, popovers, and dialog windows (`rounded-lg`).
- **Inner Nested Containers:** Any sub-panel or code block nested within a card inherits the standard 4px radius to preserve visual harmony.

Pill-shaped elements are strictly avoided, ensuring the UI retains a cohesive, technical silhouette.

## Components

### Buttons
- **Primary / Verification Action:** Background `#36B78A`, text `#FFFFFF`, font `Hanken Grotesk` 600 weight. Hover: `#2E9D76`. Focus: 2px offset ring in `#36B78A`.
- **Secondary / Navy Action:** Background `#15263B`, text `#FFFFFF`. Hover: `#213B54`. Focus: 2px offset ring in `#213B54`.
- **Neutral Outline:** Background `#FFFFFF`, border 1px solid `#E2E8F0`, text `#1E293B`. Hover: background `#F8FAFC`, border `#CBD5E1`.
- **Danger Button:** Background `#DC3545`, text `#FFFFFF`. Hover: `#B02A37`. Used exclusively for defect deletion or verification invalidation.
- **Sizing:** Compact (28px height, `space-xs` padding) for table actions; Default (36px height, `space-sm` padding) for panel actions.

### Badges & Status Chips
Badges use `JetBrains Mono` at `label-sm` (11px) with uppercase text, 4px border radius, and explicit text labels alongside an optional 6px circular indicator dot.
- **Critical / Blocker:** Background `#DC3545` at 12% opacity, text `#B02A37`, border 1px solid `#DC3545` at 30% opacity.
- **Verified / Resolved:** Background `#198754` at 12% opacity, text `#146C43`, border 1px solid `#198754` at 30% opacity.
- **Warning / Non-Repro:** Background `#D99000` at 12% opacity, text `#996500`, border 1px solid `#D99000` at 30% opacity.
- **Triage / Info:** Background `#2673C8` at 12% opacity, text `#1A4F8B`, border 1px solid `#2673C8` at 30% opacity.

### Form Inputs & Filters
- **Text Inputs:** Height 36px, background `#FFFFFF`, border 1px solid `#E2E8F0`, text `#1E293B`, placeholder `#64748B`. Focused state: border `#36B78A` with a 1px outline of `#36B78A`.
- **Filter Bars:** Multi-select dropdown filters styled as pills or square tags using 4px border radius, showing category and selected count (e.g., `Severity: Critical (2)`).

### Issue Tables & Lists
- **Header:** Sticky table header with `#F8FAFC` background, text `#64748B` in `label-sm`, 1px bottom border `#E2E8F0`.
- **Rows:** Alternating subtle hover states (`#F8FAFC`), 44px fixed height for high data density, 1px bottom border `#E2E8F0`.
- **Cell Content:** Monospace issue key pinned to the left column (`label-md`), status chip, summary in `body-md`, timestamp in `body-sm`.

### Checkboxes & Radio Controls
- **Checkboxes:** 16x16px square with 3px border radius. Unchecked: border 1px solid `#CBD5E1`, background `#FFFFFF`. Checked: background `#36B78A`, white check icon.
- **Radio Buttons:** 16x16px circle. Selected: ring and inner dot `#36B78A`.

### Cards & Panels
- **Bug Card (Kanban / List):** Background `#FFFFFF`, 1px border `#E2E8F0`, 8px corner radius, padding `space-md`. Top row: issue key and severity badge. Middle: title and short description. Bottom: assignee avatar (24px) and reproduction status.
- **Reproduction Log Panel:** Dark or muted inset box (`#F8FAFC`), 4px corner radius, 1px border `#E2E8F0`, containing monospaced logs, environment details, and execution timestamps.