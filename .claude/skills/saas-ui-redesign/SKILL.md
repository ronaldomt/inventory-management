---
name: saas-ui-redesign
description: Redesign a Vue 3 application's UI into a modern SaaS-style interface with a vertical left sidebar instead of a top nav bar, consistent spacing, clean cards, and a collapsible icons-only mode. Use when asked to restyle the app, add a sidebar, modernize the layout, or give the app a polished professional look.
---

# SaaS UI Redesign (Vue 3)

Turn a top-nav Vue 3 app into a SaaS-style app: left sidebar, clean cards, one spacing scale. Change the shell and the shared styles. Do not rewrite every view.

## Decisions (agreed with the user)

| Topic | Choice |
|---|---|
| Sidebar look | Light: white background, slate text, blue active state |
| Accent color | Blue |
| Density | Comfortable: more white space, 12px card radius, soft shadow |
| Small screens | Shrink to an icon-only strip below 900px wide |

If the user changes a choice, follow the user and update this table.

## Design tokens

Define these once as CSS custom properties on `:root` in `client/src/App.vue`. Use the tokens everywhere. Do not scatter raw hex values.

```css
:root {
  --color-bg: #f8fafc;          /* page background */
  --color-surface: #ffffff;     /* sidebar, cards */
  --color-border: #e2e8f0;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-accent: #3b82f6;      /* buttons, focus ring */
  --color-accent-strong: #2563eb; /* active nav text */
  --color-accent-soft: #eff6ff; /* active nav background */

  --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
  --space-4: 16px; --space-6: 24px; --space-8: 32px;

  --radius-card: 12px;
  --radius-control: 8px;
  --shadow-card: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);

  --sidebar-width: 248px;
  --sidebar-width-collapsed: 72px;
  --transition: 200ms ease;
}
```

Keep the status colors the app already uses (green, blue, yellow, red). Do not change their meaning.

## Layout

1. `.app` becomes a two-column layout: sidebar on the left, content column on the right.
2. Sidebar (full height, sticky, `--color-surface`, 1px right border):
   - Top: logo and company name.
   - Middle: one nav link per route, each with an icon and a label.
   - Bottom: language switcher, profile menu, and the collapse toggle.
3. Content column: `FilterBar` first, then `<router-view />` inside `.main-content` with `--space-8` padding.
4. Remove the old `.top-nav` and `.nav-tabs` styles once the sidebar works. Do not leave dead CSS.

### Nav link states
- Default: muted text, transparent background.
- Hover: `--color-bg` background.
- Active: `--color-accent-soft` background, `--color-accent-strong` text, 3px accent bar on the left edge.
- Keyboard focus: 2px `--color-accent` outline. Never remove focus outlines.

## Collapsible sidebar

- Toggle button at the bottom of the sidebar. It flips between expanded (`--sidebar-width`) and collapsed (`--sidebar-width-collapsed`).
- Collapsed: show icons only. Hide labels visually, keep them for screen readers (`aria-label` on each link, plus a `title` tooltip).
- Save the state in `localStorage` under the key `sidebar-collapsed`. Read it once at setup, like `app-locale` in `client/src/composables/useI18n.js`.
- Below 900px wide, force the collapsed state. Use `window.matchMedia('(max-width: 899px)')` with a listener. Remove the listener in `onUnmounted`. A forced collapse must not overwrite the saved user choice.
- Animate width with `transition: width var(--transition)`. Respect `prefers-reduced-motion`.
- Put the state in a small composable (`client/src/composables/useSidebar.js`) so any component can read it.

## Cards and shared classes

Change the existing shared classes in `App.vue`. Views keep their markup.

- `.card`: `--color-surface`, 1px `--color-border`, `--radius-card`, `--shadow-card`, `--space-6` padding.
- `.stat-card`: same look as `.card`. Keep the colored status accent.
- `.page-header`: `--space-6` bottom margin. The title is 24px, weight 600. The subtitle is `--color-text-muted`.
- Tables: header row on `--color-bg`, small uppercase muted labels, row hover on `--color-bg`, no vertical borders.
- Buttons and inputs: `--radius-control`, accent focus ring.

## Rules

- Vue 3 Composition API only. Match the patterns in `client/CLAUDE.md`.
- No emojis in the UI. Draw icons as inline SVG: 20px, 1.5px stroke, `currentColor`, `aria-hidden="true"`.
- Keep i18n. Every label uses `t('...')`. New strings go into both `locales/en.js` and `locales/ja.js`. Check that long Japanese labels do not break the sidebar.
- Do not change routes, API calls, data logic, or business rules. This skill changes presentation only.
- Per `CLAUDE.md`, delegate `.vue` edits to the `vue-expert` agent when it is available.
- Add a short comment above any non-obvious logic (the forced collapse, the media query).

## Steps

1. Read `App.vue`, `main.js`, `FilterBar.vue`, `LanguageSwitcher.vue`, `ProfileMenu.vue`. List the routes.
2. Add the tokens to `:root`.
3. Build the sidebar markup in `App.vue`. Move the language switcher and the profile menu into it. Check that their dropdowns still open in the right direction (they used to open downward from a top bar).
4. Add `useSidebar.js` and the collapse behavior.
5. Update the shared classes (cards, tables, page header).
6. Delete the unused top-nav CSS.
7. Verify (below).

## Verify

Open every page in the browser with the sidebar expanded, then collapsed. Check:
- Each page loads, and the active nav item is highlighted.
- Language switch to Japanese: labels fit, nothing overflows.
- Language and profile dropdowns open fully inside the screen.
- A window narrower than 900px shows the icon-only strip.
- Reload keeps the collapsed or expanded choice.
- The browser console has no new errors or warnings.
- Tab through the sidebar: the focus order and focus outline are visible.

## Gotchas

- `FilterBar` was designed for a full-width top area. Check that it does not overflow in the narrower content column.
- Dropdowns inside a sidebar with `overflow: hidden` get clipped. Use `overflow: visible` or position them outside the sidebar.
- A fixed-width sidebar needs `flex-shrink: 0`. Without it, the content column crushes the sidebar.
- `.main-content` must have `min-width: 0`. Wide tables and charts otherwise push the page sideways.
