# HiSMap Frontend Design Standard

> Based on the Swiss International Typographic Style (International Style), adapted for HiSMap's historical map application context.

## Design Philosophy

The International Typographic Style is a philosophy of objective communication: universal clarity, mathematical precision, and logical structure. For HiSMap, this means the ancient travel journals and historical geography are the content — the design recedes to let them speak.

**Core Tenets:**

1. **Objectivity over Subjectivity** — Every visual decision serves the content. No ornamentation. The designer is a conduit for historical information, not an artist.
2. **The Grid as Law** — The grid is the visible skeleton. Asymmetrical organization creates dynamic rhythm. Grid patterns are visible through subtle background textures.
3. **Typography is the Interface** — Type is the primary structural element. Grotesque sans-serif (Inter) as neutral vessels. Scale, weight, position create hierarchy.
4. **Active Negative Space** — White space is structural. It defines boundaries and gives weight to content.
5. **Layered Texture & Depth** — Subtle CSS pattern overlays (grid lines, dot matrices, diagonal stripes, noise) add tactile richness without breaking flatness.
6. **Universal Intelligibility** — Clean, legible, instantly understood.

**The Vibe for HiSMap:**
- Intellectual & Architectural — like a museum exhibition or transit map
- Structured yet Organic — subtle textures provide warmth
- Brutally Precise — depth comes from pattern, not shadow
- Timeless — no glassmorphism, neumorphism, or soft rounded corners

---

## Design Token System

### Colors (Strict Palette)

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#FFFFFF` (Pure White) | Canvas, main surfaces |
| Foreground | `#000000` (Pure Black) | Text, borders, structure |
| Muted | `#F2F2F2` (Light Gray) | Secondary backgrounds, alternating sections |
| Accent | `#FF3000` (Swiss Red) | CTAs, critical emphasis, section numbering |
| Border | `#000000` (Pure Black) | Structure definition |

**Tailwind extension:**

```ts
// tailwind.config.ts theme.extend
colors: {
  swiss: {
    bg: "#FFFFFF",
    fg: "#000000",
    muted: "#F2F2F2",
    accent: "#FF3000",
    border: "#000000",
  },
},
```

### Typography

- **Font Family:** `Inter` (Google Fonts) — closest to Helvetica/Akzidenz-Grotesk
- **Weights:** Black (900) / Bold (700) for headings. Regular (400) / Medium (500) for body.
- **Style:** UPPERCASE for headings and labels
- **Tracking:** `tracking-tighter` for large headlines, `tracking-widest` for small labels
- **Scale:** Extreme contrast. Headlines: `text-6xl` (mobile) to `text-9xl`+ (desktop). Body: legible and objective.

**Tailwind extension:**

```ts
fontFamily: {
  sans: ["Inter", "system-ui", "sans-serif"],
},
```

### Radius & Border

- **Radius:** `0px` — strictly rectangular. No rounded corners anywhere.
- **Borders:** Thick, visible (`border-2` or `border-4`). Used to define the grid and sections.

### Shadows & Effects

- **Shadows:** No drop shadows. Flat design. Only subtle ring shadows for compositional geometry (e.g., `shadow-[0_0_0_8px_rgba(255,48,0,0.1)]` for accent circles).
- **Effects:** Color inversion (Black → White, White → Red), scale transforms (1.0 → 1.05), vertical translation (-1px lift on hover).

---

## Textures & Patterns

CSS-based patterns for visual depth while maintaining flatness. Apply to muted backgrounds (`#F2F2F2`) and occasionally white surfaces. Never on pure black or red accent areas.

```css
/* Grid Pattern — 24×24px grid lines at 3% opacity */
.swiss-grid-pattern {
  background-image:
    linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px);
  background-size: 24px 24px;
}

/* Dot Matrix — 16×16px spacing, 4% opacity */
.swiss-dots {
  background-image: radial-gradient(circle, rgba(0,0,0,0.04) 1px, transparent 1px);
  background-size: 16px 16px;
}

/* Diagonal Lines — 45°, 10px spacing, 2% opacity */
.swiss-diagonal {
  background-image: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 10px,
    rgba(0,0,0,0.02) 10px,
    rgba(0,0,0,0.02) 11px
  );
}

/* Noise Texture — SVG filter overlay, 1.5% opacity */
.swiss-noise {
  position: relative;
}
.swiss-noise::after {
  content: "";
  position: absolute;
  inset: 0;
  opacity: 0.015;
  pointer-events: none;
  background-image: url("data:image/svg+xml,..."); /* inline SVG noise */
}
```

**Application Strategy for HiSMap:**
- Map sidebar (`#F2F2F2` background) → `.swiss-grid-pattern`
- Section headers → `.swiss-dots`
- Detail page sidebars → `.swiss-diagonal`
- Global body background → `.swiss-noise`

---

## Component Styles

### Buttons

- **Shape:** Strictly rectangular (`rounded-none`)
- **Primary:** Solid Black bg, White text
- **Secondary:** White bg, Black border
- **Hover:** Invert colors or switch to Swiss Red (`#FF3000`)
- **Typography:** Uppercase, bold, tracking-wide

```tsx
// Primary button pattern
<button className="bg-swiss-fg text-swiss-bg px-6 py-3 font-bold uppercase tracking-wider
  hover:bg-swiss-accent transition-colors duration-200">
  查看详情
</button>

// Secondary button pattern
<button className="bg-swiss-bg text-swiss-fg border-2 border-swiss-fg px-6 py-3 font-bold uppercase tracking-wider
  hover:bg-swiss-fg hover:text-swiss-bg transition-colors duration-200">
  返回
</button>
```

### Cards / Containers

- **Structure:** Defined by borders (`border-black`)
- **Background:** White or Muted Gray
- **Padding:** Generous and uniform (`p-8`, `p-12`)
- **Hover:** Entire card inverts (e.g., to Red or Black) with text color inversion

```tsx
// Card pattern
<div className="border-2 border-swiss-fg p-6 hover:bg-swiss-accent hover:text-white transition-colors duration-200">
  ...
</div>
```

### Inputs

- **Style:** Underlined (`border-b`) or solid rectangular with thick border
- **Focus:** Sharp border color change to Swiss Red. No glow rings.

```tsx
<input className="w-full border-b-2 border-swiss-fg py-2 px-0 text-sm
  focus:outline-none focus:border-swiss-accent transition-colors duration-200" />
```

### Tags / Badges

```tsx
// Location type tag
<span className="inline-block border border-swiss-fg px-2 py-0.5 text-xs uppercase tracking-wider">
  {location.location_type}
</span>
```

---

## Layout Strategy

- **The Grid is God** — visible through borders on elements
- **Asymmetry** — embrace asymmetrical balance (e.g., large map on left, text cluster on right)
- **Alignment** — strict left alignment for text
- **Separators** — horizontal and vertical lines to divide sections

---

## HiSMap-Specific Patterns

### Numbered Section Labels

Every major section gets a numbered prefix in red:

```tsx
<div className="flex items-baseline gap-3 mb-6">
  <span className="text-swiss-accent font-bold text-sm tracking-widest">01.</span>
  <h2 className="text-2xl font-black uppercase tracking-tight">地点概述</h2>
</div>
```

### Map Marker Custom Styling

Override Leaflet's default marker to match Swiss aesthetic:

```css
.swiss-marker {
  background: #000000;
  border: 2px solid #000000;
  border-radius: 0; /* square markers */
}
.swiss-marker:hover {
  background: #FF3000;
  border-color: #FF3000;
}
```

### Entry List (Sidebar)

```tsx
<button className="w-full text-left p-4 border-b-2 border-swiss-fg
  hover:bg-swiss-accent hover:text-white transition-colors duration-200 group">
  <div className="flex items-baseline gap-2 mb-1">
    <span className="text-swiss-accent text-xs font-bold tracking-widest group-hover:text-white">01</span>
    <h3 className="font-bold text-sm uppercase">{entry.title}</h3>
  </div>
  <p className="text-xs text-gray-500 line-clamp-2 group-hover:text-gray-200">{entry.original_text}</p>
</button>
```

### Detail Page Four-Layer Structure

Each layer uses numbered section labels and generous spacing:

```
┌─────────────────────────────────────────────────┐
│  01. 地点概述          ← Red number + Black heading │
│  ─────────────────────────────────────────────── │
│  [Grid pattern background]                       │
│  Ancient name / Modern name                      │
│  One-line summary                                │
│                                                  │
│  02. 原文与译文                                    │
│  ─────────────────────────────────────────────── │
│  [Tab: 原文 | 白话译文 | English]                  │
│  Left-aligned text block                         │
│                                                  │
│  03. 现代解释                                      │
│  ─────────────────────────────────────────────── │
│  [Dots pattern background]                       │
│  Structured academic content                     │
│                                                  │
│  04. 关系网络                                      │
│  ─────────────────────────────────────────────── │
│  [Diagonal pattern background]                   │
│  Related locations as bordered cards             │
└─────────────────────────────────────────────────┘
```

---

## Animation & Interaction

- **Feel:** Instant, mechanical, snappy, precise
- **Transitions:** `duration-200 ease-out` or `duration-150 ease-linear`
- **Hover States:** Always bold — color inversion, scale, or position changes. Never subtle fades.

```tsx
// Navigation link animation
<a className="relative overflow-hidden group">
  <span className="block group-hover:-translate-y-full transition-transform duration-200">地点</span>
  <span className="absolute inset-0 translate-y-full text-swiss-accent group-hover:translate-y-0 transition-transform duration-200">地点</span>
</a>
```

---

## Responsive Strategy

### Mobile (< 768px)
- Typography scales down but remains bold: `text-4xl` for hero headings
- Single column, vertical stacking
- Borders remain 4px thick
- CTAs full-width with consistent height (`h-16`)
- Grid patterns maintain same opacity/scale
- Bottom drawer replaces sidebar

### Tablet (768px - 1024px)
- Two-column layouts where appropriate
- Typography scales to `text-6xl`
- Asymmetric grids appear

### Desktop (1024px+)
- Full asymmetric layouts
- Maximum typography scale
- Multi-column layouts
- All hover states and micro-interactions active

**Key Principles:**
- Never compromise on border thickness or contrast
- Maintain uppercase typography and tight tracking
- Patterns remain visible at all breakpoints
- Red accent used consistently
- Spacing generous (reduce from `p-12` to `p-6` on mobile, never less)

---

## Accessibility

- **Contrast:** Black/White/Red offers 21:1 contrast. Ensure red text on white meets AA.
- **Focus:** `focus-visible:ring-2 focus-visible:ring-swiss-accent focus-visible:ring-offset-2`
- **Touch Targets:** Minimum 44×44px on mobile
- **Motion:** All CSS-based, respect `prefers-reduced-motion`
- **Semantics:** Proper heading hierarchy, semantic HTML5, ARIA labels

---

## Implementation Checklist

When implementing any frontend component:

1. Use `rounded-none` on all elements — no rounded corners
2. Use the Swiss color tokens (`swiss-bg`, `swiss-fg`, `swiss-muted`, `swiss-accent`)
3. Use Inter font with bold/black weights for headings, uppercase + tracking
4. Use thick borders (`border-2` or `border-4`) for structure
5. Apply texture patterns to muted backgrounds
6. Use color inversion for hover states (not opacity fades)
7. Number major sections with red accent prefix
8. Keep spacing generous
9. Ensure responsive behavior maintains Swiss character at all breakpoints