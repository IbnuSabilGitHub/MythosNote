---
name: Aura
colors:
  surface: '#131317'
  surface-dim: '#131317'
  surface-bright: '#39393d'
  surface-container-lowest: '#0e0e12'
  surface-container-low: '#1b1b1f'
  surface-container: '#1f1f23'
  surface-container-high: '#2a292e'
  surface-container-highest: '#353439'
  on-surface: '#e4e1e7'
  on-surface-variant: '#d7c3ae'
  inverse-surface: '#e4e1e7'
  inverse-on-surface: '#303034'
  outline: '#9f8e7a'
  outline-variant: '#524534'
  surface-tint: '#ffb955'
  primary: '#ffc880'
  on-primary: '#452b00'
  primary-container: '#f5a623'
  on-primary-container: '#644000'
  inverse-primary: '#835500'
  secondary: '#c9c6c1'
  on-secondary: '#31302d'
  secondary-container: '#474743'
  on-secondary-container: '#b7b5b0'
  tertiary: '#d3d0dc'
  on-tertiary: '#303038'
  tertiary-container: '#b7b5c0'
  on-tertiary-container: '#474750'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffddb4'
  primary-fixed-dim: '#ffb955'
  on-primary-fixed: '#291800'
  on-primary-fixed-variant: '#633f00'
  secondary-fixed: '#e5e2dd'
  secondary-fixed-dim: '#c9c6c1'
  on-secondary-fixed: '#1c1c19'
  on-secondary-fixed-variant: '#474743'
  tertiary-fixed: '#e4e1ec'
  tertiary-fixed-dim: '#c7c5d0'
  on-tertiary-fixed: '#1b1b23'
  on-tertiary-fixed-variant: '#46464f'
  background: '#131317'
  on-background: '#e4e1e7'
  surface-variant: '#353439'
typography:
  h1:
    fontFamily: Newsreader
    fontSize: 40px
    fontWeight: '400'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Newsreader
    fontSize: 32px
    fontWeight: '400'
    lineHeight: '1.3'
  h3:
    fontFamily: Newsreader
    fontSize: 24px
    fontWeight: '400'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  code-block:
    fontFamily: Space Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.7'
    letterSpacing: 0.02em
  label-caps:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 1200px
  gutter: 24px
---

## Brand & Style

This design system is built upon the intersection of intellectual depth and technical precision. It adopts a **Minimalist** and **High-Precision** style, blending the spatial clarity of Linear with the document-centric focus of Notion. The aesthetic is designed to disappear, allowing the user's thoughts and AI-generated insights to take center stage. 

The emotional response is one of "monastic focus"—a calm, dark environment that feels premium and intentional. Every pixel is accounted for, using subtle borders and high-contrast typography to create a professional workspace for high-level synthesis and research.

## Colors

The palette is anchored by a deep, monochromatic foundation to minimize eye strain during long sessions of intellectual work. 

- **Backgrounds:** The primary workspace uses a "Deep Dark" (#0E0E12), while elevated cards and sidebars use "Surface Grey" (#1A1A22) to create structural hierarchy.
- **Accents:** "Amber Gold" (#F5A623) is reserved strictly for primary actions and state indicators, providing a warm, high-contrast focal point.
- **Typography:** "Ivory White" (#F0EDE8) is used for body text to reduce the harshness of pure white on dark backgrounds, while secondary text uses a muted grey to maintain a clear information hierarchy.

## Typography

The typographic system utilizes a tri-font pairing to distinguish between intent and origin:

1.  **Headings (Newsreader):** A refined serif that evokes a literary and authoritative feel. Used for page titles and section headers to provide an "editorial" quality to the notes.
2.  **Body (Manrope):** A modern, highly legible sans-serif for the core interface and user-written content. It provides the "Linear-like" technical clarity.
3.  **AI & Technical (Space Grotesk):** A geometric monospace used for AI outputs, citations, and metadata. This visual distinction ensures the user always knows when they are interacting with machine-generated content.

## Layout & Spacing

This design system employs a **Fixed Grid** philosophy for the central content area (reminiscent of a notebook page) combined with **Fluid** sidebars for utility (reminiscent of an IDE). 

- **Layout Model:** A 12-column grid is used for dashboard views, while document views center-align to a 720px reading width.
- **Rhythm:** A strict 4px baseline grid ensures high-precision alignment.
- **Negative Space:** Generous margins (40px+) are used between major content blocks to foster a sense of "calm" and prevent information density from becoming overwhelming.

## Elevation & Depth

To maintain a minimalist profile, the design system eschews heavy shadows in favor of **Tonal Layers** and **Subtle Outlines**.

- **Surfaces:** Depth is communicated by shifting the background color. The further "forward" an element is (e.g., a modal), the lighter its background hex becomes.
- **Borders:** Low-contrast 1px strokes (#2A2A32) define the edges of cards and input fields.
- **Interaction:** Hover states are indicated by a slight brightening of the border color rather than an increase in shadow.
- **Overlays:** Modals and dropdowns use a subtle backdrop blur (8px) to provide context without distracting from the primary task.

## Shapes

The shape language is "Soft" and disciplined. 

- **Standard Radius:** 4px (0.25rem) for buttons, inputs, and small UI components to maintain a sharp, professional edge.
- **Large Radius:** 8px (0.5rem) for primary content cards and containers.
- **Precision:** Edges are never fully sharp (0px) to avoid a "brutalist" feel, but never so rounded as to appear "playful." The intent is to look like finely machined hardware.

## Components

- **Buttons:** Primary buttons use the Amber accent with dark text. Secondary buttons are ghost-style with a subtle border.
- **AI Response Cards:** Distinguished by a left-border accent in Amber and a background using the Space Grotesk font.
- **Inputs:** Clean, 1px bordered boxes that highlight the border in Amber only when focused.
- **Chips/Tags:** Small, monospace labels with low-opacity Amber backgrounds for categorizing research notes.
- **Command Palette:** A central, floating interface element with a blur background and a refined search input—the "hub" of the productivity experience.
- **Sidebars:** Collapsible, using the #1A1A22 surface color to distinguish navigation from the active thought-space.