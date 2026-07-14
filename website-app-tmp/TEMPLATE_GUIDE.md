# General Website Template — Usage Guide

This file is the usage guide for the agent building on this template. It is
read-only reference material: do not update it for the app, do not treat it as
an app deliverable, and do not delete it. Read it once before writing code —
it replaces exploring the template source file-by-file.

Minimal SPA-style Next.js website scaffold for websites, landing pages, public
pages, portals, documentation-style pages, and lightweight CMS-backed sites.
It intentionally has no prebuilt landing sections.

## Commands

```bash
pnpm install               # once after template pull
pnpm generate:contracts    # after every lib/app-definition/definition.ts change
pnpm typecheck             # once before pushing; fix what it reports
pnpm dev                   # local dev server; rarely needed
```

`pnpm build` / `pnpm start` exist for the deployment pipeline — do not run
them locally; the preview deployment builds automatically on push and build
errors are retrievable from the deployment logs.

## Structure

- `app/page.tsx`: the site entry — start building here.
- `app/layout.tsx`: root layout wiring providers; `app/api/**`: optional semantic App API routes.
- `components/providers/`: TanStack Query + Kylon workspace provider; keep.
- `components/ui/`: reusable UI primitives; keep and reuse.
- `lib/app-definition/definition.ts`: App metadata, entities, table mapping, API declarations; source of `pnpm generate:contracts`.
- `lib/kylon/`: Kylon bridge helpers and workspace member profiles; keep.
- `lib/db.ts`: DB connection/query helpers; `lib/query-keys.ts`: query key registry.
- `generated/`: disposable output of `pnpm generate:contracts`; never hand-edit.

## Build The Site

Start from `app/page.tsx`. If the site needs persisted CMS/content/form/
subscription data, define entities and TiDB table mapping in
`lib/app-definition/definition.ts`, add semantic App API routes under
`app/api/**`, run `pnpm generate:contracts`, and put the schema in
`db/migrations/` as numbered SQL files.

## UI Component Index

All under `components/ui/`. Before using any component you have not used yet,
read the props interface at the top of its file (one targeted read) — do not
guess props and fix them after typecheck.

- `data-table/` — the table engine: header, rows, card list fallback, column-width persistence (`index.tsx` is the entry).
- `data-types.ts` — canonical field value/type aliases shared by table + field components.
- `field.tsx`, `field-list.tsx`, `field-list-layout.ts` — record detail field grid primitives.
- `field-value.tsx`, `field-value-popover.tsx`, `field-values/` — per-type field renderers/editors (text, number, date, select, checkbox, relation, attachment) with view/edit modes.
- `drilldown-dialog.tsx` — chart→records drilldown dialog (`DrilldownScope` + rows).
- `metrics.tsx` — dashboard summary metric cards (`SummaryMetric[]`).
- `chart.tsx` — Recharts wrapper with themed tooltip/legend.
- `calendar.tsx`, `calendar-view.tsx`, `calendar-utils.ts` — date-picker primitive and month/week event calendar (`CalendarEvent[]`).
- `combobox.tsx` — searchable select for relation/user pickers.
- `overflow-list.tsx` — collapses overflowing chips into a "+N" popover.
- `file-preview.tsx` — attachment preview (image/pdf) with fallback link.
- `alert-dialog.tsx`, `dialog.tsx`, `sheet.tsx`, `popover.tsx`, `hover-card.tsx`, `tooltip.tsx`, `context-menu.tsx`, `dropdown-menu.tsx` — overlay primitives (shadcn-style).
- `button.tsx`, `input.tsx`, `input-group.tsx`, `textarea.tsx`, `select.tsx`, `checkbox.tsx`, `radio-group.tsx`, `switch.tsx`, `slider.tsx`, `toggle.tsx`, `toggle-group.tsx`, `label.tsx` — form primitives.
- `card.tsx`, `tabs.tsx`, `accordion.tsx`, `separator.tsx`, `scroll-area.tsx`, `skeleton.tsx`, `badge.tsx`, `avatar.tsx`, `alert.tsx`, `item.tsx`, `kbd.tsx`, `sonner.tsx` — layout/display primitives and toasts.
- `use-responsive-input.ts` — hook for mobile-friendly input behavior.

## Platform Topics (read the build-app skill references, not template source)

- Workspace members and `user`/`multi_user` fields → `references/workspace-data.md`.
- Entity/field/relation registration contracts and Data Viewer behavior → `references/data-definition-contracts.md`.
- KylonBridge, in-app Data Viewer buttons, destructive-action confirmation, and other UI conventions → `references/ui-guidelines.md`.
- `db/migrations` rules, the App id placeholder and registration gates, and the develop→push→publish loop → the build-app skill body.

You have now seen the whole template. Start building — do not read template
source files to "understand the project" beyond the targeted reads above.
