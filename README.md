# BPMap for Workday

See Workday business process definitions as a readable swimlane flow, privately in your browser.

> Working product name. Independent product, not affiliated with Workday, Inc. Workday® is a trademark of Workday, Inc.

**Status:** Phase 2 complete (Increment 2.4). Import a Workday *View Definition* Excel export → correct stages, parallel steps, conditions, lanes and decisions → **Executive / Process owner / Configurator** views → **scenario simulation** (answer conditions, see the real path) → **health checks** (HC-01..07, HC-16) → import a definition with its subprocesses (linked: open one, come back) → focus on a role or read it as an accessible step list → nudge boxes by hand (Arrange) → customise, including conditions in plain words (edits survive re-import; orphaned ones are flagged; share them as a customisations file) → export **PDF, PowerPoint (editable shapes), draw.io, Excel**, SVG, PNG or a project file, for one definition or a pack with a cover. Everything runs locally: nothing is uploaded, and an e2e test proves it.

## Run it

Requires Node ≥ 22 (developed on Node 26, npm 11).

```bash
npm install
npm run dev          # http://localhost:5173
```

| Command | What it does |
|---|---|
| `npm run dev` | Vite dev server for `apps/web` |
| `npm test` | Unit + golden-file tests for all packages (Vitest) |
| `npm run typecheck` | TypeScript 7 over the whole workspace |
| `npm run build` | Production build with CSP (`apps/web/dist`) |
| `npm run check` | typecheck + test + build |
| `npm run e2e` | Playwright e2e on the production build, using your installed Chrome (incl. the network-privacy test) |
| `npm run guide:capture` then `npm run guide` | Re-capture the guide's screenshots (needs `npm run build` and `vite preview --port 4180`) and rebuild `docs/BPMap_User_Guide.pdf` |
| `npm run fixtures` | Regenerate the synthetic XLSX fixtures and the in-app sample |

## Layout

```
apps/web                 React 19 + Vite 8 app (shell, canvas, panels, import worker, persistence)
packages/model           canonical model: zod schemas, stable IDs, order → stage keys, step kinds
packages/importer-xlsx   worker-safe XLSX reader + Workday normaliser (fflate + fast-xml-parser)
packages/engine-graph    stages, lanes, transitions
packages/engine-layout   grid placement, gutter routing, decision diamonds, executive stage cards
packages/engine-scenario scenario answers → skipped steps, resolved conditions, presets
packages/engine-rules    health rules HC-01..07, HC-16
packages/scene           one display list for canvas background and exports; SVG serialiser
packages/exporters       scene → draw.io XML and native-shape PowerPoint (pptxgenjs); minimal XLSX writer
packages/design-tokens   colours/type tokens (TS) + Tailwind CSS mirror
packages/fixtures        SYNTHETIC workbooks + golden snapshot (replace with anonymised real exports)
archive/prototype-v0     the original AI Studio prototype (not built)
```

## Docs

- [User guide (PDF)](docs/BPMap_User_Guide.pdf): every feature step by step, with annotated screenshots
- [PRD](docs/PRD_BPMap_for_Workday.md) ([PDF](docs/PRD_BPMap_for_Workday.pdf)) · [Design System](docs/DESIGN_SYSTEM.md) · [Architecture](docs/ARCHITECTURE.md)
- [Decisions log](docs/DECISIONS.md): every implementation decision and why
- [Execution flow](docs/FLOW.md): what calls what, and what is being changed now
