# Decisions Log

Every meaningful decision made while changing the code, with the reasoning behind it. Newest at the bottom.

**Format:** each entry has an ID, date, the phase/requirement it serves, **Decision**, **Why**, **Alternatives considered**, and **Consequences / follow-ups**.

Related: [PRD](PRD_BPMap_for_Workday.md) · [Design System](DESIGN_SYSTEM.md) · [Architecture](ARCHITECTURE.md) · [Flow](FLOW.md)

---

## DEC-001 · Archive the prototype instead of patching it in place
- **Date:** 2026-11-10 · **Serves:** Phase 0, Architecture §24
- **Decision:** Copy the original prototype (`src/`, `index.html`, configs, `package.json`) to `archive/prototype-v0/` and rebuild in the new workspace layout. The prototype is excluded from builds and type-checks.
- **Why:** The folder was not a git repository, so there was no history to fall back on. Architecture §24 planned to hot-fix D1/E1/E3/E4/E10 in place first, but almost every hot-fixed file (`FlowchartEditor.tsx`, `gemini.ts`, `DataVerification.tsx`) is replaced in Phase 1 anyway. Patching code we're about to delete is wasted effort, but deleting it without a copy loses the user's work.
- **Alternatives:** (a) Baseline git commit, then delete. Committing needs the user's go-ahead, so it's offered instead. (b) Hot-fix in place, as Architecture §24 suggested. Rejected as throwaway work.
- **Consequences:** The archive can be deleted once the user makes a baseline commit. Note: the prototype's `package-lock.json` was removed **without** being archived, so the archived `package.json` installs with caret ranges, which may resolve newer versions than the originals.

## DEC-002 · npm workspaces instead of pnpm
- **Date:** 2026-11-10 · **Serves:** Architecture §5, ADR-003 (amended)
- **Decision:** Use **npm workspaces** (`apps/*`, `packages/*`) with the npm 11 that ships with Node 26.
- **Why:** pnpm isn't installed, and corepack is no longer bundled with Node ≥ 25, so pnpm would need a separate global install on the user's machine. npm workspaces give the same package boundaries ADR-003 cares about (engine packages reusable by the future AI gateway) with zero extra tooling.
- **Alternatives:** Install pnpm globally (another system change); a single app with folder boundaries only (loses reuse by `apps/gateway`).
- **Consequences:** ADR-003's intent (framework-free packages, boundary rules) is unchanged; only the package manager differs. Commands in docs use `npm run … -w <workspace>`.

## DEC-003 · Workspace packages ship TypeScript source (no build step)
- **Date:** 2026-11-10 · **Serves:** Architecture §5
- **Decision:** Each package's `exports` points at `src/index.ts`. Vite, Vitest and `tsc --noEmit` all consume the source directly.
- **Why:** There's one consumer today (the web app), and the tools resolve symlinked workspace TS natively. A per-package build adds watch processes and stale-output bugs for no benefit yet.
- **Alternatives:** `tsup` per package; TypeScript project references with `tsc -b`.
- **Consequences:** When `apps/gateway` (Phase 3) runs on a server runtime, add a build (or run it with a TS-aware runtime). Revisit then.

## DEC-004 · Respect our own 14-day dependency delay at install time
- **Date:** 2026-11-10 · **Serves:** Architecture §18.1 ("Renovate with a 14-day delay")
- **Decision:** Install dependencies with `npm install --before=<today − 14 days>` and pin major versions explicitly in `package.json`.
- **Why:** The architecture asks for delayed adoption of new releases as a supply-chain control. Applying it from the very first install keeps us honest.
- **Alternatives:** Install whatever is latest today.
- **Consequences:** The lockfile reflects versions at least 14 days old. A future Renovate config will enforce the same rule.

## DEC-005 · Start on current major versions (TypeScript 7, Vite 8, Vitest 5)
- **Date:** 2026-11-10 · **Serves:** Architecture §4 (tech stack)
- **Decision:** Ranges are pinned to the major only (`^7.0.0`, `^8.0.0`…), and the install applies the 14-day cutoff (DEC-004). Resolved: TypeScript 7.0.2 (native compiler), Vite 8.3, Vitest 5.0, React 19.3, @xyflow/react 12.12, zod 4.6, Tailwind 4.3.
- **Why:** A greenfield codebase should begin on the supported majors rather than inherit a migration on day one. The architecture names libraries, not versions.
- **Alternatives:** Pin the older majors the prototype used (TS 5.8, Vite 6). Rejected: they would need migrating within months.
- **Consequences:** `npm view --before` turned out to ignore the cutoff and reported versions newer than it, so exact-version pins failed (`ETARGET`). Major-only ranges let the cutoff choose. If a TS 7 or Vite 8 incompatibility appears, it is logged here with the workaround.

## DEC-006 · Read XLSX with fflate + fast-xml-parser; exceljs only for generating fixtures
- **Date:** 2026-11-10 · **Serves:** IMP-01, NFR-SEC-02, Architecture §7.2 (supersedes the reader half of ADR-009)
- **Decision:** The importer unzips with **fflate** and parses the sheet XML with **fast-xml-parser**. **exceljs** is a root dev-dependency used only by the fixture generator script (and later, possibly, the XLSX *export* worker).
- **Why:**
  1. **Zip-bomb guard.** fflate exposes each entry's declared uncompressed size *before* inflating, so the §7.2 limits (≤ 2,000 entries, ≤ 150 MB uncompressed) are enforced up front. exceljs inflates first.
  2. **Worker-safe.** Both libraries are pure ESM with no Node polyfills. exceljs's browser build is a ~1 MB UMD bundle that assumes `global`/polyfills.
  3. **Smaller attack surface.** The install showed exceljs pulls deprecated transitive dependencies (`rimraf@2`, `fstream`, `glob@7`, `uuid@8`). These now stay out of the shipped bundle.
  4. **We only need cell text.** Formulas are ignored by design (§7.2), so a full spreadsheet engine isn't needed.
- **Alternatives:** exceljs in the worker (as ADR-009 proposed); SheetJS (the npm release is stale; the current one ships only from its own CDN).
- **Consequences:** We own a small reader (`packages/importer-xlsx/src/xlsx.ts`) covering shared strings, inline strings, rich text and the cell types `s/str/inlineStr/b/n/e`. Golden tests use real files written by exceljs, so the reader is tested against an independent writer.

## DEC-007 · Synthetic fixtures until real exports arrive
- **Date:** 2026-11-10 · **Serves:** NFR-QUAL, Architecture §21 (fixture policy), open question T1
- **Decision:** `packages/fixtures/scripts/make-fixtures.mjs` writes three synthetic workbooks: canonical layout, renamed and shuffled headers, and an unknown layout. The canonical one doubles as the in-app sample (`apps/web/public/sample-change-job.xlsx`), so the sample goes through the *real* import path.
- **Why:** No real Workday export is available yet. Golden tests are needed now, and the synthetic files are written by an independent writer (exceljs), so they genuinely exercise our reader. Step and condition wording is our own, not copied from Workday's delivered definitions or from Incubane's sample.
- **Alternatives:** Hand-written JSON fixtures (wouldn't test the XLSX reader); copying a public sample (licensing and provenance unclear).
- **Consequences:** The header synonyms and the "`<Process> (<Variant>) step <order> - <Type>`" Step label pattern are **assumptions** until T1 is answered. Regenerating fixtures changes the file bytes (exceljs stamps timestamps), so the golden snapshot's `contentHash` must be refreshed with `vitest -u`.

## DEC-008 · Content hash = FNV-1a 32-bit + byte length
- **Date:** 2026-11-10 · **Serves:** IMP-06 (re-import detection), Architecture §13
- **Decision:** `contentHash(bytes)` is a synchronous FNV-1a over the file bytes, suffixed with the length.
- **Why:** The hash is used only to detect "is this the same export as last time?" for overlay reconciliation. It isn't a security boundary. `importWorkbook` is synchronous (it runs in a worker and in tests), and WebCrypto's SHA-256 is async-only.
- **Alternatives:** SHA-256 via `crypto.subtle` (would make the whole import async); no hash.
- **Consequences:** Collisions are possible but harmless: the worst case is a missed "this export changed" prompt. Never use this hash for integrity or security.

## DEC-009 · Notifications sheet is detected, not yet parsed
- **Date:** 2026-11-10 · **Serves:** IMP-02 (P0) vs MOD-09 (P1)
- **Decision:** The importer recognises a Notifications sheet (and says so in the sheet report), but `definition.notifications` stays empty in Increment 1.
- **Why:** Detection is P0, but modelling notifications is P1 (Phase 2). We also don't know the real column layout, so a parser written now would be guesswork baked into the model.
- **Alternatives:** Parse it speculatively now.
- **Consequences:** The parse report shows "Notifications sheet found, shown from Phase 2".

## DEC-010 · Condition numbering follows stage order and is keyed by normalised text
- **Date:** 2026-11-10 · **Serves:** MOD-08, Architecture §7.4, §12, §13
- **Decision:** Condition text is split on line breaks (one condition per line), and a trailing "(Workday Owned)" sets `workdayOwned` and is removed. Conditions are deduplicated by lower-cased, whitespace-collapsed text and numbered C1…Cn by first appearance in **stage order** (then source row).
- **Why:** Stage order matches how people read the diagram (C1 is the first condition you meet). Text-keying is what lets plain-word overrides and diffs survive renumbering.
- **Alternatives:** Number by source row (unstable when rows are re-ordered, which the renamed-and-shuffled fixture proves).
- **Consequences:** A condition can be attached to several steps (the fixture's "Location changed?" is on i and k).

## DEC-011 · Lane assignment rules
- **Date:** 2026-11-10 · **Serves:** VIS-01, MOD-06
- **Decision:** A step's lane is its **first** security group. Service and integration steps always go to the system lanes ("Workday (automatic)", "Integrations") at the bottom, whatever their group column says. An initiation step with no group goes to "Initiator", and any other step with no group goes to "Unassigned" (plus a `W-GROUP-EMPTY` warning). Lanes are ordered by first appearance in **stage order**.
- **Why:** VIS-01 says system work sits at the bottom so readers can see where people stop and the system takes over. Using the first group gives one deterministic lane per step; the extra groups are shown as "Also:" in the Configurator view (Phase 2).
- **Alternatives:** Duplicate a multi-group step into every lane (misleading: it is one task); order lanes alphabetically (loses the narrative order).
- **Consequences:** Lane IDs are `lane-<slug(label)>`, which is what overlay lane renames key on.

## DEC-012 · Tokens: TypeScript source, CSS mirror guarded by a test
- **Date:** 2026-11-10 · **Serves:** Design System §15.2
- **Decision:** `packages/design-tokens/src/index.ts` is the source (primitives, semantic light/dark, node tokens, canvas type). `tokens.css` mirrors the semantic layer for Tailwind, and `tokens.test.ts` fails if any value drifts. The same test re-checks the Design System §14.2 contrast guarantees.
- **Why:** The Design System's target is a W3C `tokens.json` plus a generator. That's worth it once PPTX and draw.io exporters also consume the tokens (Phase 2). Today there are two consumers, and a drift test gives the same safety without a build step.
- **Alternatives:** Build the generator now; CSS-only tokens (the canvas and exporters can't read CSS in a worker).
- **Consequences:** Move to `tokens.json` + generator when the third consumer arrives.

## DEC-013 · Edge routing: "gutter router" for Increment 1; decision diamonds deferred
- **Date:** 2026-11-10 · **Serves:** VIS-05, ADR-004 (phase 2 of the layout), open question T2
- **Decision:** Transitions between consecutive stages are orthogonal polylines that bend **only in the gutter** (the boundary between two columns). Parallel stages get split/join bars, with short stubs to each step. Conditional steps are shown with the dashed amber outline and C-badges; **no decision diamonds yet**.
- **Why:** Because nodes live strictly inside their column, an edge that only turns at column boundaries can never cross a node (a layout test proves it). That meets VIS-05 for Increment 1 without pulling in ELK or libavoid before the T2 spike. Diamonds belong with SCN-02 ("show as a yes/no decision"), which is P1, and the DS says diamonds appear only on approvals or when toggled.
- **Alternatives:** Run the ELK spike now; draw a diamond for every condition (the prototype's approach, which DS principle 2 rejects).
- **Consequences:** `routeTransition` is isolated in `engine-layout`, so the router can be swapped after the T2 spike. Long diagrams have one vertical segment per gutter, which is readable but not optimised for crossings.

## DEC-014 · Scene resolves colours at build time; the canvas background *is* the export scene
- **Date:** 2026-11-10 · **Serves:** ADR-007, EXP-01, VIS-06
- **Decision:**
  1. `buildDiagramScene` and `buildExportScene` take a theme and emit concrete colours.
  2. The canvas draws the **export scene** (header, lanes, stage headers, edges, bars, legend, condition list) as its background, and renders the step boxes as interactive React Flow nodes at the same coordinates.
  3. Step icons are left out of Increment 1, both on the canvas and in exports.
- **Why:**
  - The architecture's `TokenRef` indirection only pays off with user branding (Pro, Phase 3). Resolving early keeps exporters trivial.
  - Reusing the export scene for the canvas means "what you see is exactly what you export", the strongest form of ADR-007.
  - The kind label text already carries the meaning (DS principle 6), and icons would need an SVG icon pipeline for exports, so they wait for Phase 2 to keep canvas and export identical.
- **Alternatives:** A separate canvas renderer for lanes and edges (risk of drift); React Flow edges for transitions (React Flow edges need node handles; our bars aren't nodes).
- **Consequences:** Scene text is measured with a width approximation (no DOM in workers), so the canvas's DOM-rendered node text may wrap slightly differently from the export. This is acceptable because both clamp to 2 lines.

## DEC-015 · Leave the `fsevents` install script blocked
- **Date:** 2026-11-10 · **Serves:** Architecture §18.1 (supply chain)
- **Decision:** npm 11 blocks dependency install scripts unless they're allow-listed. The only one in the tree is `fsevents` (an optional macOS file watcher pulled in by the dev tooling). We leave it blocked.
- **Why:** fsevents ships a prebuilt binary; its install script is only a compile fallback. Blocking install scripts by default is the supply-chain posture we want.
- **Consequences:** If a future dependency genuinely needs an install script, approve it explicitly with `npm install-scripts approve <pkg>` and log it here.

## DEC-016 · Production CSP injected at build time; theme script is an external file
- **Date:** 2026-11-10 · **Serves:** NFR-PRIV-01, NFR-SEC-02, Architecture §18.1
- **Decision:** A small Vite plugin (`apply: 'build'`) adds a `<meta http-equiv="Content-Security-Policy">` to the built HTML: `connect-src 'self'`, `script-src 'self'`, `worker-src 'self' blob:`, `img-src 'self' blob: data:`, `font-src 'self'`. The pre-paint theme script is `public/theme-init.js` (external), not inline.
- **Why:** Increment 1 has no optional services, so nothing besides our own origin needs to be reachable. The architecture's `connect-src` entries for the AI and team domains are added only when those features exist. Vite's dev server needs inline scripts for hot reload, so the policy applies to builds only.
- **Verified:** In the production preview, the sample imported through the worker, all 18 steps rendered, there were **0 CSP violations**, the self-hosted Inter font loaded, and there were **0 off-origin requests**.
- **Consequences:** A meta CSP can't set `frame-ancestors`. When hosting is chosen, move the policy to an HTTP response header and add `frame-ancestors 'none'`.

## DEC-017 · IndexedDB: one key-value table for Increment 1
- **Date:** 2026-11-10 · **Serves:** NFR-REL, IMP-07, Architecture §14.2 (simplified)
- **Decision:** Dexie database `bpmap` v1 has a single `kv` table holding `project` (definitions, overlays, reports, activeId) and `mappingProfiles`. Autosave is debounced at 500 ms. On load, every definition goes back through `parseDefinition` (zod), and invalid entries are dropped, not loaded.
- **Why:** There's one local project per browser in Increment 1. The architecture's multi-table schema is for multiple projects, scenarios and versions (Phase 2+). A single document is simpler and atomic.
- **Alternatives:** The full §14.2 schema now.
- **Consequences:** Moving to the multi-table schema is a Dexie `version(2).upgrade()` migration when projects or scenarios arrive. If storage fails (private mode, quota), the status bar says so and suggests exporting a project file.

## DEC-018 · Overlay subset lives in the web app for now
- **Date:** 2026-11-10 · **Serves:** CUS-01 (P0 part), Architecture §13
- **Decision:** The overlay type (labels, notes, hidden, laneNames) is defined in `apps/web/src/store/overlay.ts`. The graph receives `hiddenStepIds`/`laneNames`, and the scene receives `labels`/`notes`.
- **Why:** Only the web app uses overlays today. Re-import reconciliation and orphan detection (IMP-06, P1) is when overlay logic becomes worth a package (`packages/overlay` per the architecture).
- **Consequences:** Overlays are keyed by StepId / lane ID, so they already survive re-import of an unchanged step. Orphan reporting comes with IMP-06.

## DEC-019 · Undo groups keystrokes per field
- **Date:** 2026-11-10 · **Serves:** CUS-04, ADR-005
- **Decision:** zundo tracks only `overlays`. Its `handleSet` is wrapped so a burst of edits becomes one undo step, and the burst ends after 500 ms of quiet **or as soon as a different field is edited**. Imports, hydration and project loads run inside `untracked()` (temporal tracking paused). Removing a definition clears the history.
- **Why:** The first version used time-only grouping. Browser testing showed one Undo removed *both* a label and a note typed back to back. Users expect one undo per field. Loads aren't user edits, so they mustn't be undoable.
- **Verified in browser:** label + note → Undo removes the note only → Undo removes the label → Undo is disabled.

## DEC-020 · Derivation runs on the main thread in Increment 1
- **Date:** 2026-11-10 · **Serves:** Architecture §8 (worker threshold), §23
- **Decision:** `buildGraph → layout → buildExportScene` run in a `useMemo` on the main thread. Only XLSX parsing is in a worker.
- **Why:** The architecture puts derivation in a compute worker only above ~40 steps. The sample has 18, and the derivation is pure and fast. A worker round-trip would add latency and complexity for no gain yet.
- **Consequences:** Add the compute worker when the T6 benchmark (or a real 60+ step export) shows main-thread time above 50 ms.

## DEC-021 · Show only what works; mark the roadmap honestly
- **Date:** 2026-11-10 · **Serves:** Design System §13.1 ("honest about limits")
- **Decision:**
  - The right panel shows only the implemented tabs (Step, Import report). Health, Scenario and Customise aren't shown yet.
  - The view switcher shows Executive and Configurator **disabled**, with a "Coming in Phase 2" tooltip, because the three-view model is central to the product.
  - The Export menu lists SVG, PNG and Project file, with a footnote that PDF, PowerPoint and draw.io arrive in Phase 2.
  - The sample button says "synthetic".
- **Why:** Empty tabs would read as broken. The disabled views tell a beta user where the product is going without pretending it's there.

## DEC-022 · Lazy-load the workspace to meet the bundle budget
- **Date:** 2026-11-10 · **Serves:** Architecture §23 (≤ 180 KB gzip initial JS)
- **Decision:** `App` lazy-loads `Workspace` (React Flow, engines, scene, panels, exporters). The import screen ships React, zod, Dexie and the store only.
- **Measured:** Before, one 715 KB chunk (226 KB gzip, **over** budget). After, 163 KB gzip initial (+8 KB CSS) and 65 KB gzip for Workspace, loaded when a definition exists. The import worker (177 KB raw) loads on first import.
- **Consequences:** Initial JS is within budget but has little headroom. The next candidates are moving zod validation of stored data into the worker, and trimming the lucide imports.

## DEC-023 · Native `<dialog>` and `<details>` instead of Radix for Increment 1
- **Date:** 2026-11-10 · **Serves:** Design System §9.10, §15.3 (deferred)
- **Decision:** The mapping dialog uses the native `<dialog>` (focus trap, Esc, backdrop for free), and the Export menu uses `<details>`. Tabs and radio groups are hand-written with ARIA roles and arrow-key handling.
- **Why:** These few primitives work well natively. Radix becomes worth it with the Phase 2 component set (popovers, tooltips, toggle groups, dropdown menus with typeahead).
- **Consequences:** Swap to Radix as part of the Storybook component library work. `<details>` menus don't close on outside click; acceptable for now, revisit with Radix.

## DEC-024 · "Fit" fits the whole scene, not just the steps
- **Date:** 2026-11-10 · **Serves:** VIS-07, VIS-06
- **Decision:** On open, and from the Fit control, the canvas calls `fitBounds` with the export scene's bounds (title, lanes, legend, conditions). React Flow's default fit button is replaced.
- **Why:** The browser test showed React Flow's `fitView` frames only the step nodes, which cut off the lane headers, the title and the legend. Those are part of the diagram's meaning (DS principle 2).

## DEC-025 · Dev server: run Vite via npm in the background; launch config uses an absolute node path
- **Date:** 2026-11-10 · **Serves:** developer tooling only
- **Decision:** `.claude/launch.json` runs `/usr/local/bin/node node_modules/vite/bin/vite.js apps/web`. The dev script binds to the default `localhost` (`--strictPort`).
- **Why:** Starting the server from the browser pane with `npm` produced no process and no logs, probably because `npm`/`node` aren't on that launcher's PATH. Running `npm run dev` from the shell works.
- **Consequences:** Run `npm run dev` from a terminal and open http://localhost:5173.

---

# Increment 1.1: fixes from the first real Workday export (2026-11-11)

Source: a real *Change Job (Default Definition)* export (26 steps, 6 sheets), compared with the Incubane BP Visualizer's output for the same file. The file stays **out of git** (it contains company-specific names); it's kept locally in the git-ignored `.local/` folder for manual checks. An anonymised mirror is the new golden fixture (DEC-030).

## DEC-026 · Order letters sort alphabetically (corrects Architecture §7.4)
- **Decision:** `stageKeyOf` pads letters on the **right** (`"ba" → "ba_"`), so stage keys sort alphabetically: `a < ba < bb < bd < d`. Numeric suffixes still sort numerically (`k < k1 < k2 < k10 < m`). The importer adds `W-ORDER-MISMATCH` if the export's row order ever disagrees with this sort. Stored definitions get their stage keys recomputed on load (`withFreshStageKeys`), because keys written before this change used the old format.
- **Why:** The real export lists its rows as `a, ba, bb, bc, bd, d, e …`, and the Notifications sheet repeats that order, so Workday runs the `b*` reviews straight after initiation. Our previous rule (shorter letter runs first: `a…z`, then `aa…`) was a guess written into the architecture. It put `ba` to `bd` at the very end, **after** the process-complete step. Incubane's tool makes exactly the same mistake on this file.
- **Alternatives:** Use the file's row order as the stage order. Rejected as the primary rule because the renamed/shuffled fixture shows rows can be out of order; the order letters are the semantic source, and the row order is now a cross-check.
- **Consequences:** Architecture §7.4 is corrected. The old synthetic golden snapshot changed only in its `stageKey` strings.

## DEC-027 · Decode Workday's literal `&#xa;` before splitting; never split on `;`
- **Decision:**
  - `decodeCell` turns numeric entities (`&#xa;`, `&#10;`) and basic named entities into characters, and normalises line endings.
  - `cellLines` then splits on line breaks **only**.
  - Any entity left after decoding (double-encoding) raises `W-ENCODING` rather than being guessed at.
- **Why:** The real export writes in-cell line breaks as the literal text `&#xa;` (in the XML, `&amp;#xa;`), with list items separated by `&#xa;&#xa;`. Our old splitter also split on `;`, and `&#xa;` *ends* in `;`, so every multi-value cell broke apart. The effects:
  - a phantom condition `C2 = "&#xa"` attached to 11 steps;
  - stray `&#xa` text on 15 conditions;
  - two Workday-owned conditions labelled Custom;
  - duplicate conditions (37 instead of 34);
  - a phantom lane `"HR Administrator&#xa"`.

  And the import report said "no warnings".
- **Consequences:** Groups are no longer split on `;` either. A group name containing `;` stays intact.

## DEC-028 · Identify sheets by their section-title row
- **Decision:** Every sheet of the export has a one-cell title row ("Business Process Steps", "Notifications", "Allowed Actions by Role", "Allowed Services", "Related Links", "Available Rules & Fields"). The title decides the sheet's role, and header heuristics are only a fallback for files without titles. Recognised-but-unused sections are reported as "recognised, used in a later phase".
- **Why:** The old header heuristic marked the real Notifications sheet as *ignored* (its header row doesn't contain the word "notification") and the "Available Rules & Fields" sheet as *notifications* (a long data cell happened to mention notifications and recipients). The fallback heuristic now also ignores cells longer than 40 characters.

## DEC-029 · Parse notifications (MOD-09 brought forward) and read all 17 step columns
- **Decision:**
  - The importer now maps every column of the real Steps sheet: `Additional Information` (split into `restriction`, `alternate` and other text), `Routing Modifier`, `All`, `Run As User`, `Validation` (with severity), `Due Date Is Based On Effective Date`, `Do Not Advance`, `Subprocess Definitions`.
  - It also reads the definition settings above the table: effective date (Excel serial → ISO), most recent used date, overall due date, autocomplete, and **Initiating Security Groups**.
  - It parses the Notifications sheet's *System* and *Custom* tables. Notifications are linked to steps by order (`On Exit : o - …` → step `o`).
- **Why:** These fields were the Configurator-level detail the real file contained, but they were silently dropped (9 of 17 columns mapped, `initiatingGroups=[]`). Now that a real layout is known, parsing notifications is no longer speculation. DEC-009 deferred it only because the format was unknown.
- **Schema:** `Step` gains `validations` (default `[]`), `runAs` and `additionalInfo`. `ProcessDefinition` gains `meta` (default `{}`). `Notification` is reshaped (`kind`, `name`, `condition`, `disabled`, `stepOrder`). `SCHEMA_VERSION` stays 1 because every new field has a default, so older saved data still validates.

## DEC-030 · Anonymised mirror of the real export as a golden fixture
- **Decision:** `change-job-workday-layout.xlsx` is generated by the fixture script. It has the same sheets, title rows, preamble, all 17 columns, the literal `&#xa;` encoding, and the same order values (`a, ba…bd, d … v`). Conditions, groups and company wording are invented, and it includes `1=0?`-style conditions and a disabled custom notification. The real file is never committed.
- **Why:** The fixture policy (Architecture §21) requires anonymised fixtures. A mirror keeps every structural property that caused a bug, so each fix has a regression test.

## DEC-031 · First health rule: HC-16 "step can never run"
- **Decision:** New package `@bpmap/engine-rules` with the Architecture §11 shape (rules → findings with stable fingerprints). The first rule, **HC-16**, flags steps whose condition name is constant-false (`1=0?`, `1 = 0?`, `False?`, `Never?`). The web app gains a **Health** tab with finding cards (DS §9.7).
- **Why:** In the real export, steps `s` (Create Subordinate) and `s1` (Change Superior Organization) carry `1=0?`. That's a common Workday trick for switching a step off without deleting it, but both tools drew them as ordinary conditional steps, which misleads readers and testers.
- **Consequences:** HC-16 is added to the PRD rule catalogue (Markdown; the PDF is regenerated with the next PRD revision). Detection works on the condition *name*, because the export doesn't contain the rule logic. Rules HC-01 to HC-15 follow in Phase 2.

## DEC-032 · Decision diamonds on conditional approvals; start/end markers
- **Decision:**
  - Every conditional **approval** gets a decision diamond in a 96 px slot in front of it, with "Yes" into the step and a dashed amber **"No, skip"** path that runs under the step and rejoins after it. The diamond label reads in words, with IDs sorted: "C5 and C6?", "C3, C6 and C8?", or "4 conditions?" for more than three. Never "C5+C6".
  - The flow gets a start marker (green ring) and an end marker (navy ring).
  - Non-approval conditional steps keep the dashed outline and badges only (DS §9).
- **Why:**
  - This implements the Design System default that Increment 1 had deferred (DEC-013).
  - Incubane's "C5+C6?" labels are ambiguous (AND or OR?), and it also draws diamonds on some action steps, which contradicts its own rule.
  - The skip path rejoins *after* the step and never points backwards. The scene test "no backwards arrows" still holds.
- **Consequences:** The diamond slot widens only the columns that need it. The "No, skip" label sits on the line inside a surface-coloured pill (DS §10.4), after a browser check showed it crowding the step box.

## DEC-033 · Legend and condition list keep a fixed reading width
- **Decision:** Legend columns are capped at 290 px, and condition-list columns at 600 px, whatever the diagram's width.
- **Why:** The legend's columns were a quarter of the diagram's width, which spread the items across a 26-stage diagram about 4,000 px wide. The user's screenshot showed "Action or review" thousands of pixels from "Approval".

---

# Phase 2 · Increment 2.1: views, scenarios, health (2026-11-11)

Phase 2 ("Parity+") is split in two. **2.1** (this increment) covers views (VW-01/03/04), scenarios (SCN-01..03), health rules (HLT-01/02 with HC-01..07) and the Phase 1 leftovers that gate everything else (automated privacy e2e and CI). **2.2** covers exports (PDF, PPTX, draw.io), packs, re-import reconciliation (IMP-06), focus role (VIS-08) and the screen-reader step list.

## DEC-034 · Scenario semantics: "No" skips, "Yes" resolves, "Not set" may run
- **Decision:** New package `@bpmap/engine-scenario`. A step is skipped if any of its conditions is answered **No**. A condition answered **Yes** is *resolved*: it no longer makes a step conditional, so the dashed outline, its badge and the decision diamond disappear for that case. **Not set** leaves the step conditional (dashed).
  - `buildGraph` takes `resolvedConditionIds` and `decisionConditionIds`. `GraphStep.conditional` now means "has an *unresolved* condition", and `openConditionIds` drives badges and diamond labels.
  - Skipped steps are removed through the same `hiddenStepIds` path as overlay-hidden steps, so empty lanes and stages collapse with no extra code.
  - Scenario state (answers, decisions, presets) is stored per definition, persisted, included in project files, undoable like overlays, and pruned to existing conditions on re-import.
- **Why:** Architecture §10.1 defined skipping. Resolving "Yes" answers is what makes a scenario diagram *read* as a single path rather than a sea of dashed boxes.
- **Verified on the real export:** C6 = No removes the four approvals (26 → 22 steps, lanes 11 → 7), and save / reset / re-apply of a preset works.

## DEC-035 · Views: Configurator = detail lines; Executive = stage cards from the scene
- **Decision:**
  - **Configurator:** boxes are 140 px tall, with up to 4 detail lines from `stepMetaLines` (due, alternate, routing, restriction, extra groups, run-as, validations, notifications, do-not-advance; "+n more" beyond 4). The scene and the canvas node use the same function.
  - **Executive:** `executiveLayout` (engine-layout, text measurement injected) places one card per stage, 6 per row, snaking arrows between rows. `buildExecutiveDiagram` draws the cards with a dot per step coloured by kind, the title, and a caption "lane · only if C… · process complete". The canvas shows Executive as background only (no interactive nodes).
  - The view is stored per definition (VW-04), drives exports, and is named in the export subtitle.
- **Why:** Matches DS §11's view matrix. Text measurement stays in the scene package, so layout remains font-free and testable.
- **Bug caught in the browser:** the first Executive render showed only arrows. The cards had the scene role `step`, which the canvas deliberately skips because React Flow draws steps live. Cards now have their own role, `stage-card`, plus a unit test and an e2e assertion (26 cards).

## DEC-036 · Health rules HC-01..HC-07: rules skip themselves when their column is missing
- **Decision:** Rules receive `{ def, graph, settings }`, with `maxSerialApprovals = 4` and `maxTasksPerStage = 3`.
  - HC-01, HC-02 and HC-03 return nothing when no step in the export has a value for the column they rely on (restriction, alternate, due date).
  - HC-07 is a single summary finding, not one per condition.
  - HC-02 ignores optional steps and "Employee As Self" / "Initiator" groups.
  - Health always runs on the **full** definition, not the scenario.
- **Why:** Without the skip, an export that lacks a column (like our synthetic sample) would produce a wall of false "critical" findings. On the real-layout fixture, HC-01 correctly flags approval `i`, which is restricted to "Subject" only, so the initiator could approve. The real file has the same pattern.
- **Dismissals (HLT-02):** each finding can be dismissed with a reason. Dismissals are stored in the overlay by fingerprint (so they're undoable and survive re-import) and can be restored from a "Dismissed" list. Older stored overlays without `dismissedFindings` are upgraded on load (`normaliseOverlay`).

## DEC-037 · Health badge counts Critical + Warning only
- **Decision:** The tab badge shows open Critical + Warning findings. Info findings are listed, grouped by rule (groups with more than 3 findings start collapsed), but don't count.
- **Why:** On the real export the badge first read **34**, mostly Info ("no due date"). A number that large reads as "everything is broken" and trains people to ignore it. It now reads 14.

## DEC-038 · E2E with Playwright on the system Chrome; CI on GitHub Actions
- **Decision:** `@playwright/test` with `channel: 'chrome'` runs against the **production build** (`vite preview`, CSP active).
  - `privacy.spec.ts` (NFR-PRIV-01) records every request through import → three views → scenario → Health → SVG export, and asserts no off-origin request, no request body and no CSP violation.
  - `flows.spec.ts` covers Workday order and diamonds, scenario skip and reset, views, and the dismiss → reload → restore cycle.
  - `.github/workflows/ci.yml` runs typecheck → unit tests → build with a secret scan of `dist/` → e2e, uploading traces on failure. Browser download is skipped; the runner's Google Chrome is used.
- **Why:** The privacy promise is the product's main differentiator (PRD §2.2), so it must be enforced by a test, not by a manual check. Using the installed Chrome avoids a large browser download on every machine.
- **Results:** 5/5 e2e tests pass locally. The first run failed in 2 tests because of an ambiguous test locator (`'No'` also matched "**No**t set"), fixed with `exact: true`.
- **Consequences:** Actions are pinned to major tags (`@v4`); pinning to commit SHAs is a follow-up once Renovate is set up. Bundle check: initial JS is 169 KB gzip + 8 KB CSS = **177 KB of the 180 KB budget**. Increment 2.2 must move the zod validation of stored data off the initial chunk before adding more to it.

## DEC-039 · Verify against an independent oracle, not against ourselves
- **Date:** 2026-11-11 · **Serves:** NFR-QUAL, Architecture §21
- **Decision:** `tools/oracle/workday_export_oracle.py` re-parses Workday exports with Python's standard library and its own implementation of the rules. Cross-checks compare our model, scenarios and views with it. A local-only Playwright spec (`real-export.local.spec.ts`) drives the real UI against a private file and the oracle's expected counts, and skips when either is absent.
- **Why:** Golden snapshots only prove the importer is *stable*, not *right*. Both earlier real-file bugs (DEC-026, DEC-027) would have passed our own snapshots. Results are in `docs/testing/TEST_REPORT_2026-11-11.md`: 1,116 scenario × view renders, 70/73 checks, 23/23 edge cases, 4/4 real-UI tests. The 3 failures (F-01..F-03) plus a rule false positive (F-04) are open.

## DEC-040 · Executive captions: one fact per line (fixes F-01, F-02, F-03)
- **Date:** 2026-11-11 · **Serves:** VW-01, test report F-01..F-03
- **Decision:** Under each step title, the Executive card now draws separate lines:
  1. the lane;
  2. the **full** "only if C5, C6, C7 and C8" list (`conditionPhrase(ids, Infinity)`, wrapped to at most 2 lines; never collapsed to "4 conditions");
  3. "✓ Process complete after this step" in the success colour.

  Card heights are measured from the same lines. The export header now adds "effective 2026-11-10 · overall due 1 Week" from `def.meta`.
- **Why:** The single joined caption was cut at one line, so "process complete" vanished in all 224 scenarios where step `o` is visible, and long condition lists became "only if 4…". Separate lines mean no fact competes with another for space. The dates were already parsed (DEC-029) but never shown.
- **Verified:** oracle cross-check 73/73 (was 70/73). New unit regression test on the real-layout fixture. Visual check on the real file.

## DEC-041 · Flow rules ignore steps that never run and mutually exclusive pairs (fixes F-04)
- **Date:** 2026-11-11 · **Serves:** HLT-01, test report F-04
- **Decision:**
  - HC-04, HC-05 and HC-06 skip steps guarded by a constant-false condition (the HC-16 set).
  - HC-04 also skips a pair when one step's condition is the single-negation of the other's (`areExclusive`: "Country is NOT Canada?" vs "Country is Canada?", "isn't" vs "is"), because the two steps never both run.
- **Why:** On the real export, HC-04 reported "HR Administrator acts at s and again at s1" (both can never run) and "Employee As Self acts at t and again at t1" (mutually exclusive by country). Both were false positives that would erode trust in Health.
- **Limits:** Exclusivity is inferred from condition *names* only. The export doesn't contain rule logic, so complementary rules with different wording (e.g. "Hourly?" vs "Salaried?") are not detected. Revisit when condition-rule import (IMP-09) lands.

## DEC-042 · Replace the pan/zoom canvas with a scrolling viewer and a frozen lane column
- **Date:** 2026-11-11 · **Serves:** user request ("fixed canvas, scroll, first column frozen"), VIS-07, NFR-A11Y. Supersedes "React Flow (keep)" in Architecture §11.2 and §15.
- **Decision:**
  - `DiagramViewer` puts the scene at a **fixed zoom** inside a native `overflow: auto` container. You scroll with the wheel, trackpad, scrollbars or the keyboard.
  - The **lane-name column is `position: sticky; left: 0`**, drawn with the same `laneHeaderItems` as the scene at the same coordinates. At scroll 0 it sits exactly over the scene's headers; when scrolled it stays pinned, with a shadow.
  - **Zoom:** −/+ steps (30–200%), click the percentage for 100%, "Fit height" / "Fit width", and Ctrl/⌘ + wheel (or pinch) zooms around the cursor. The default is fit-height for swimlanes and fit-width for Executive, clamped to **60–100%** so text stays readable.
  - Steps are focusable `<button>`s (`data-testid="step"`, `aria-pressed`), and "Show step" scrolls the selected step to the centre.
  - **React Flow is removed** (dependency, provider, CSS) along with its minimap.
- **Why:** In React Flow, wide processes (26 stages ≈ 6,800 px) opened fitted to a tiny scale and had to be dragged around. You lost track of which lane you were in. Steps are never dragged or connected (the layout is deterministic), so the library only added free panning, which is exactly what hurt readability.
- **Results:**
  - Workspace chunk **65 KB → 13 KB** gzip; CSS 8.2 → 6.4 KB.
  - Tests: 122 unit, 10 e2e (incl. a new viewer test: frozen column at the left edge after scrolling 1,500 px; zoom controls).
  - Browser-verified on the real export: frozen lanes after scrolling 1,900 px; Ctrl+wheel 100% → 165% while plain wheel scrolls; Show step centres step `s`.
- **Consequences:**
  - Stage headers ("Step k") scroll away vertically. A frozen top row is a possible follow-up.
  - Free-form node dragging (VIS-11 nudges) will need its own pointer handling when it's built.
  - Architecture §11.2/§15 are updated to match.

## DEC-043 · Pin the page furniture too: title, legend, conditions, footer
- **Date:** 2026-11-11 · **Serves:** user request ("the lower half should also stay fixed"), VIS-06
- **Decision:** The viewer's sticky layer is now as wide as the visible area. Besides the lane column, it holds the scene groups `header`, `legend`, `conditions` and `footer` (the footer is now its own group), on a surface background. The scrolling layer skips those groups, so nothing is drawn twice. `groupTop()` (scene) finds where the legend starts so the pinned background covers exactly that band.
- **Why:** The legend and the condition list sit in the scene's lower-left. On a wide process they scrolled away as soon as you moved right, which is exactly when you need them to decode C-badges.
- **Limit (deliberate):** furniture is pinned only when its full width (~1,300 px of scene × zoom) fits the visible area. Otherwise a pinned block would be clipped with no way to scroll to its right half, so it scrolls with the diagram instead (e.g. at 100% zoom in a narrow window).
- **Verified:** scrolled 2,500 px right and to the bottom on the real export, the legend and conditions stay at the left edge with one copy. The e2e viewer test asserts this.

## DEC-044 · Load persistence after the entry chunk; exporters only on use
- **Date:** 2026-11-11 · **Serves:** NFR-PERF (startup budget), Architecture §13
- **Decision:**
  - `main.tsx` dynamically imports `persistence/db.ts` (Dexie + zod validation of stored data), awaits `hydrateFromStorage()`, then renders. If storage fails, the app still renders and works in memory.
  - Exporters (`pptxgenjs`, `jspdf` + `svg2pdf.js`, draw.io) are imported inside the export handlers.
  - The import dialog imports field labels from the new `@bpmap/importer-xlsx/fields` subpath, so the parser doesn't get pulled into the entry chunk.
- **Why:** The entry chunk was 169 KB gzip, almost all of it code needed only after first paint, or never.
- **Result:** Entry 169 → **81 KB** gzip. Startup total ≈ 142 KB (entry 81 + model 24 + order 7 + db 30, fetched in parallel). On first use: PDF ≈ 150 KB, PowerPoint ≈ 121 KB.
- **Trade-off:** The first render waits for the db chunk (one extra round trip on a cold load). This is intentional, so the user never sees an empty workspace flash before their project restores.

## DEC-045 · Exports are built from the same scene: native PowerPoint shapes, draw.io XML, vector PDF
- **Date:** 2026-11-11 · **Serves:** EXP-02/03/04, PCK-01/03
- **Decision:**
  - New package `packages/exporters`. `flatten(scene)` turns the scene display list into absolute primitives (rect, ellipse, diamond, text, polyline).
  - `toDrawio(scenes[])` writes one multi-page `mxfile`, one page per definition. Shapes use `html=0` and every value is XML-escaped, so labels can't inject markup.
  - `buildPptx(slides)` uses **native shapes and text boxes**, so steps stay editable in PowerPoint. Each routed segment is its own line, with a triangle arrow on the last one. The slide size is scaled so the scene's longest side ≤ 56 in (PowerPoint's limit).
  - PDF: `jspdf` + `svg2pdf.js` render our own SVG as vectors.
  - Packs ("All N definitions") put one page or slide per definition in a single file.
- **Why:** One display list keeps the screen and every export identical (Architecture §10). Native shapes beat a pasted image: the PRD's personas edit decks.
- **Accepted risk:** `npm audit` flags a high-severity `image-size` issue via `pptxgenjs`. It is reachable only through `addImage`, and we never pass images, so the vulnerable code never runs. Revisit if image export is added.
- **Tests:** 6 unit tests (drawio is well-formed XML with every step label, escaping, multi-page; pptx is a valid zip with N slides and editable text). e2e: real downloads on the production build under CSP (`%PDF-`, `PK`, `<mxfile`).

## DEC-046 · Exports always use the light theme; the PDF text is limited to WinAnsi
- **Date:** 2026-11-11 · **Serves:** EXP-*, DS §3 (print)
- **Decision:**
  - `page()` and `pack()` in Workspace derive the scene with `theme: 'light'`, whatever the UI theme is.
  - For PDF only, text passes through `toWinAnsi`, which maps smart quotes, dashes and ellipses to ASCII, and other characters outside Latin-1 to `?`.
- **Why:** Exports are printed, pasted into decks and emailed, so a dark-theme export looks broken on white paper. jsPDF's standard fonts cover WinAnsi only. Without the sanitizer, non-Latin text becomes garbage glyphs and corrupts spacing.
- **Limit:** PDFs of definitions with non-Latin names (e.g. Japanese) lose those characters. SVG, PNG, PowerPoint and draw.io keep full Unicode. The fix is embedding a subset font, deferred until a customer needs it.

## DEC-047 · Re-import keeps orphaned edits visible; focus a role; accessible step list
- **Date:** 2026-11-11 · **Serves:** IMP-06, VIS-08, NFR-A11Y
- **Decision:**
  - **Orphans:** When a definition is re-imported, overlay entries (labels, notes, hidden, lane names) whose step or lane ID no longer exists are **not dropped silently**. `findOrphans()` lists them, and the Import tab shows "N customisations no longer match a step", with the text, plus a **Remove** button (`withoutOrphans`, undoable). Step IDs are derived from order + kind + task (`makeStepIds`, Architecture §6.2), not row position, so unchanged steps keep their edits automatically.
  - **Focus a role:** A toolbar select sets `focusLaneId`. The viewer overlays the other lanes with a dim band and fades their steps to 30%. Steps stay clickable. Switching definitions resets the focus.
  - **Step list:** A toggle replaces the diagram with a semantic `<table>`: one `<tbody>` per stage, row headers "order · letter", and columns for type, who, runs only if, and due. Step names are buttons that select the step, the same as clicking it in the diagram.
- **Why:** Silently losing someone's notes after a re-import is the worst trust failure for this tool, and keeping them invisibly is almost as bad. A diagram is unusable with a screen reader, so the table is the equivalent view, not an afterthought.
- **Tests:** e2e: focus dims (roles − 1) lanes; the step list has 26 stages in Workday order; re-import with the v2 fixture (step `o` removed) shows the orphaned note, and Remove clears it. New fixture: `change-job-workday-layout-v2.xlsx`.

## DEC-048 · Close without a confirm dialog (Undo instead); focus scrolls to the role; pre-bundle export libraries in dev
- **Date:** 2026-11-11 · **Serves:** user feedback on Increment 2.2, VIS-08, EXP-02..04
- **Close:**
  - The × on a definition tab used `window.confirm()`. Embedded browsers (including the desktop app's preview pane) can suppress native dialogs, and then `confirm()` returns false, so the button silently did nothing.
  - Now × closes immediately. The definition, its overlay, report, scenario and view are kept in `lastRemoved`, and a toast offers **Undo** for 10 s (`restoreRemoved` puts it back at the same tab position).
  - Both changes are `untracked`, so they don't enter the customisation undo history.
  - Why: an undoable action needs no confirmation, and Undo is faster and works everywhere.
- **Focus:** choosing a role scrolls (smoothly) so that role's first step, in reading order, sits just right of the frozen lane column, with its lane vertically centred. A **‹ n / N ›** stepper then walks through that role's steps; each one is selected, centred, and shown in the Step panel. The scroll fires only when the role changes, not on later zooms.
  - Why: dimming alone left users hunting for a lane that might start 3,000 px to the right, which defeats the feature.
- **Exports in dev:** the export libraries are imported lazily (DEC-044), so Vite's dev server only discovered them on the first click. That triggered a dependency re-optimisation, which (a) invalidates modules the page already loaded, causing "Failed to fetch dynamically imported module", and (b) failed outright here because a stale cache still listed the removed `@xyflow/react`.
  - Fix: `optimizeDeps.include: ['jspdf', 'svg2pdf.js', 'pptxgenjs']` pre-bundles them at startup.
  - The production build was never affected, which is why the e2e suite (run on `vite preview`) passed.
  - Lesson: verify new lazy dependencies on the dev server too, not only on the build.
- **Tests:** e2e +2 (focus scrolls to Assign Pay Group and the stepper selects it; close → toast → Undo restores the note → close → reload stays closed). 16 e2e tests in total. Dev-server check: PDF, PowerPoint and draw.io each downloaded.

# Phase 2 · Increment 2.3: customise & hand off (2026-11-11)

Scope: the remaining Phase 2 P1 items that are about handing work to other people: CUS-01 (plain-word conditions), CUS-03 (customisations file), EXP-08 (Excel), EXP-03 (conditions slide) and PCK-03 (pack cover). Deferred to Increment 2.4: IMP-04 (subprocess linking) and VIS-11 (layout nudges).

## DEC-049 · Plain-word conditions are keyed by the Workday condition text, not by "Cn"
- **Date:** 2026-11-11 · **Serves:** CUS-01, US-07, CUS-02
- **Decision:**
  - New overlay field `conditionText: Record<conditionKey, string>`, where `conditionKey` is the Workday text lower-cased with collapsed whitespace.
  - `plainConditions()` maps it to `conditionId → words` for one derivation. The scene, Scenario panel, Step panel, step list, Excel export and conditions page all show the plain words first, with "Workday: <original>" underneath. The original is never hidden.
  - The Scenario panel has an "In plain words" field per condition (coalesced undo per field, like labels).
  - A re-import that no longer contains the condition text lists the rewrite as an orphan (DEC-047).
- **Why not the C-number:** C-numbers follow stage order (DEC-010), so adding a step earlier in the process renumbers every later condition. Keyed by C-number, rewrites would silently attach to the wrong condition after a re-import, which is worse than losing them. The condition text changes only when the rule itself changes, and then the rewrite *should* be reviewed.
- **Old data:** stored overlays and project files without the field load with `{}` (`normaliseOverlay`).

## DEC-050 · A customisations file separate from the project file
- **Date:** 2026-11-11 · **Serves:** CUS-03, SCN-03 ("exportable presets")
- **Decision:**
  - Export ▸ Project ▸ "Customisations only" writes `<name>.customisations.json` (`format: 'bpmap-customisations'`) containing the overlay, scenario presets and saved view for **one** definition, plus its process name and variant. It contains no steps, groups or conditions.
  - "Open" (formerly "Open project") accepts either file type and branches on `format`.
  - A customisations file is applied to the open definition with the same process + variant (case-insensitive), else any loaded one; otherwise it fails with "Import that definition first".
  - Applying **merges**: incoming entries win per key, everything else is kept, and presets with the same name are replaced. It is one undo step.
- **Why:** Consultants share edits with colleagues who already have the export (often a newer one) from their own tenant. Sending the project file would overwrite their definition and spread tenant data further than needed. Merging rather than replacing means applying a colleague's file never deletes your own work.
- **Limit:** presets store answers by C-number, so they can point at the wrong condition if the colleague's export numbers conditions differently. Keying preset answers by condition text (as in DEC-049) is a follow-up.

## DEC-051 · Excel writer, conditions page and pack cover, built as scenes
- **Date:** 2026-11-11 · **Serves:** EXP-08, EXP-03, PCK-03
- **Excel:**
  - `packages/exporters/src/xlsx.ts` is a ~100-line SpreadsheetML writer on `fflate` (already a dependency). No exceljs/SheetJS in the app: they would add ≥ 300 KB, and SheetJS's npm distribution is outdated.
  - Text is written as **inline strings**, which Excel never evaluates, so `=HYPERLINK(...)` in a step name stays text (no formula injection). The header row is bold, frozen and filtered. XML-invalid control characters are dropped.
  - Sheets: Steps (full definition in stage order, with label, note and hidden flag), Conditions (plain words + Workday text), Health (findings by severity with dismissal reasons). Packs add a Definition column.
  - Tested by a round trip through our own importer's XLSX reader.
  - The workbook ignores the scenario on purpose: it is the reference copy people filter, while the diagram is the case view.
- **Conditions page:** `buildConditionsScene` is a 16:9 page listing every condition at 17 px (one or two columns), plain words first. PDF, PowerPoint and draw.io exports of a view now produce diagram + conditions; SVG and PNG stay single images.
  - Why: on a 26-stage process, the condition list under the diagram is shrunk to fit the slide and becomes unreadable.
- **Pack cover:** `buildCoverScene` shows title, date and contents (name, summary, view) with open findings per definition (critical · warning · info; dismissed ones excluded).
- **Why scenes:** each page is an ordinary `Scene`, so every exporter renders it with no format-specific code, and the cover looks the same in PDF, PowerPoint and draw.io.
- **Dev server:** `fflate` added to `optimizeDeps.include` (it is now lazily used on the main thread as well as in the worker; see DEC-048).

# Phase 2 · Increment 2.4: subprocesses, layout nudges, renumbering-proof scenarios (2026-11-11)

Closes Phase 2's buildable scope. Not built: EXP-09 (account-gated export formats), which needs accounts and a backend (Phase 3+); every format stays free and local for now.

## DEC-052 · Scenario answers and presets follow the condition text across re-imports
- **Date:** 2026-11-11 · **Serves:** SCN-01..03, IMP-06; closes the limit noted in DEC-050
- **Problem:** Answers, decision toggles and presets were stored by condition id. On re-import, `pruneScenario` kept every id that still existed. If a step was added or removed earlier in the process, "C7" became a *different* condition and the saved answer silently applied to it. The v2 fixture reproduces this: removing step `o` shifts every later Cn.
- **Decision:**
  - `rekeyScenario(oldDef, newDef, state)` (engine-scenario) translates answers, decisions and preset answers old id → condition text → new id, and drops conditions that no longer exist. The store calls it on every re-import.
  - Presets also carry `byText` (answers keyed by `conditionKey`). `presetAnswersFor(def, preset)` applies by text when present, else by id (older presets still work).
  - The customisations file writes `byText`, and applying it re-derives answers against the receiving export.
  - `conditionKey` moved to `@bpmap/model`, so the overlay (DEC-049) and scenarios share one normalisation.
- **Tests:** 4 unit tests on the renumbering fixture (rekey, drop, text-keyed preset on a renumbered export, legacy preset).

## DEC-053 · Multi-file import and subprocess linking
- **Date:** 2026-11-11 · **Serves:** IMP-04
- **Finding first:** the real Change Job export has a "Subprocess Definitions" column, but it is empty on every step. Its two "Sub Process" mentions are *allowed actions* in the security sheet, not steps, so the importer was not missing anything. Linking is therefore built and tested on synthetic fixtures (`hire-with-subprocesses.xlsx` calls two subprocesses; `propose-compensation-hire.xlsx` is one of them).
- **Decision:**
  - `linkSubprocesses(defs)` (pure, `@bpmap/model/links.ts`) matches each Sub-Process step to a loaded definition, in order: exact "Process (Variant)" → process name when exactly one definition has it → the step's task name. It never links a definition to itself, and ambiguous matches stay unlinked rather than guessing.
  - UI:
    - **Step panel:** "Runs a subprocess" with **Open**, or "Not loaded, add its export".
    - **Back chip:** opening a subprocess shows "← Back to Hire · step c", which returns with the calling step selected.
    - **Tabs:** subprocess tabs get a ↳ marker with a "Subprocess of …" tooltip.
    - **Import tab:** "Calls N · M not loaded" and "Called by".
  - Up to **20 files** per drop. Extra files are named in a dismissible notice, not dropped silently.
  - Sub-Process steps no longer raise W-GROUP-EMPTY: in Workday the subprocess's own steps carry the groups.
- **Not built:** a separate notifications export as its own file. Workday's View Definition already includes the Notifications sheet, which we parse (DEC-029).

## DEC-054 · Layout nudges grow the grid instead of breaking it
- **Date:** 2026-11-11 · **Serves:** VIS-11
- **Decision:**
  - Overlay `nudges: Record<stepId, {dx, dy}>`, passed to `layout()`, which applies them at node placement (step 4), *before* diamonds, bars and gutter routing, so every connector follows the moved box with no routing changes.
  - A nudge never leaves the step's lane or stage. Moving down makes the lane taller; moving left or right adds room on that side of the stage column. Later lanes and stages shift accordingly. Moves up stop at the lane's top edge, and each axis is capped at ±480.
  - With no nudges the layout is byte-identical (the golden snapshots did not change).
  - **Arrange** mode in the viewer toolbar:
    - Drag shows a preview while moving and commits on drop as one undo step.
    - The arrow keys move the focused step 8 px (Shift: 32 px), as a keyboard alternative.
    - **Reset layout** clears all nudges, and can be undone.
    - The mode is off by default, so clicking and scrolling behave as before. The click that ends a drag is ignored, so dropping doesn't change the selection.
  - Nudges are keyed by stable step id, so they survive re-import. Removed steps' nudges are listed as orphans. Executive view ignores nudges.
- **Why not free placement:** free x/y would let a box drift into another role's lane or the wrong stage, making the swimlane lie, and would need a general edge router. Growing the grid keeps the diagram truthful and keeps routing trivial.

# Test campaign after Phase 2 (2026-11-12)

Full report: [testing/TEST_REPORT_2026-11-12.md](testing/TEST_REPORT_2026-11-12.md). 17 defects fixed with regression tests; 14 open findings ranked there.

## DEC-055 · Fixes from the Phase 2 test campaign
- **Date:** 2026-11-12 · **Serves:** NFR-REL, NFR-COMP, NFR-A11Y, EXP-01/02, MOD-05, IMP-02
- **Format limits as tested code:** `@bpmap/exporters/limits` (a subpath, so pptxgenjs stays out of the startup bundle) holds `pngScale` and `pdfPointsPerPx`.
  - **PNG** is capped at 16,384 px per side and 128 MP, and gives a clear "use SVG or PDF" error below 0.5×, plus a 30 s timeout. Before this, a 200-step process hung with no message.
  - The cap is Safari-safe and therefore conservative for Chrome (open finding O12).
  - **PDF** pages are scaled to the 14,400 pt (200 in) reader limit. Text weights are mapped to the standard fonts' regular/bold, because 500/600 fell back to Times.
- **Autosave:**
  - A pending save is flushed on `pagehide` or when the tab is hidden. An edit made < 0.5 s before closing was lost.
  - Each save is broadcast on a `BroadcastChannel`, and other tabs show "changed in another tab, Reload". This is a warning, not a merge: merging per key, or a single-writer lock, is open finding O7. We chose a warning over silent last-writer-wins because the user can act on it.
- **Narrow screens:** below 1,024 px the details panel is a drawer, opened by a toolbar "Details" button or by selecting a step, and the toolbar wraps. This meets the PRD's "tablet read-only".
- **Importer:**
  - Consolidated Approval → approval; Batch/Job and Report → system (service); Document → review.
  - "System/Custom Notifications" are recognised as section titles, and a sheet with a non-steps title is never guessed as Steps. Before, the mapping dialog opened on the Notifications sheet.
  - A header with no rows is an error. Two Initiation steps raise a warning. Unnamed custom notifications are kept. "No Steps sheet" says how many rows were searched.
- **Accessibility:** Escape deselects; the completion green is darkened to 700 (white ✓ ≈ 5:1); tab targets are 24 px.
- **Copy:** the "Customisations only" hint now says the file contains condition wording (as keys of rewrites); it previously said "no Workday data".

## DEC-056 · User guide built from the running app, with arrows placed from real element boxes
- **Date:** 2026-11-12 · **Serves:** IMP-11 (how-to), onboarding of design partners
- **Decision:** `docs/BPMap_User_Guide.pdf` is generated, not hand-made.
  - `docs/guide-build/capture.mjs` drives the production build with Playwright on the **synthetic fixtures only** (no tenant data can reach the guide). It saves 2× screenshots plus the on-screen box of every control the guide points at.
  - `build_guide.py` draws numbered markers and arrows as SVG over each screenshot, from those boxes, and Chrome prints the PDF (the same pipeline as the PRD).
  - Marker placement avoids other markers, targets and crossing arrows. A per-pointer side hint keeps markers off panel text.
  - The build **fails** if a target is mostly outside its screenshot, which happened twice when the diagram had scrolled. Without that check the arrow would silently point at the wrong control.
- **Why:** hand-annotated screenshots go stale with every UI change. Here, a UI change means one re-run: `npm run guide:capture && npm run guide`.
- **Trade-offs:**
  - Screenshots are embedded as PNG; JPEG made the PDF larger (11 MB vs 7 MB) for flat UI images.
  - Screenshots and the intermediate HTML are git-ignored; only the scripts and the PDF are committed.
