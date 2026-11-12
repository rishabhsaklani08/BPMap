/**
 * Capture the screenshots for the user guide, with the on-screen box of every control the guide
 * points at. Synthetic fixtures only: no tenant data ever appears in the guide.
 *
 *   npm run build && (cd apps/web && npx vite preview --port 4180)   # in another terminal
 *   node docs/guide-build/capture.mjs                                 # → docs/guide-build/shots/
 *
 * Output: shots/<name>.png (2× pixels) and shots/meta.json { name: { w, h, anns: [{ n, x, y, w, h, label }] } }
 * in CSS pixels relative to the shot. build_guide.py draws the arrows from that metadata.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const HERE = fileURLToPath(new URL('.', import.meta.url));
const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const OUT = `${HERE}shots`;
const BASE = process.env.BPMAP_URL ?? 'http://localhost:4180';
const fixture = (f) => `${ROOT}packages/fixtures/data/${f}`;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, colorScheme: 'light' });
const page = await ctx.newPage();
const meta = {};
const wait = (ms = 300) => page.waitForTimeout(ms);

/** Screenshot `region` (default: viewport) and record the box of each annotation target. */
async function shot(name, anns = [], region) {
  await wait(350);
  const vp = page.viewportSize();
  const r = region ?? { x: 0, y: 0, width: vp.width, height: vp.height };
  const out = [];
  const seen = (b) => Math.max(0, Math.min(b.x + b.width, r.x + r.width) - Math.max(b.x, r.x)) * Math.max(0, Math.min(b.y + b.height, r.y + r.height) - Math.max(b.y, r.y));
  for (const [i, a] of anns.entries()) {
    // When a locator matches several elements, point at the one most visible in this shot.
    const all = (await Promise.all((await a.loc.all()).map((l) => l.boundingBox().catch(() => null)))).filter(Boolean);
    const b = all.sort((p, q) => seen(q) - seen(p))[0];
    if (!b) throw new Error(`${name}: annotation ${i + 1} (${a.label}) not found`);
    out.push({ n: i + 1, x: b.x - r.x, y: b.y - r.y, w: b.width, h: b.height, label: a.label, ...(a.side ? { side: a.side } : {}) });
  }
  await page.screenshot({ path: `${OUT}/${name}.png`, clip: r });
  meta[name] = { w: r.width, h: r.height, anns: out };
  console.log(`✓ ${name} (${out.length} pointers)`);
}
const box = async (loc) => (await loc.first().boundingBox());
const step = (text) => page.locator('[data-testid=step]', { hasText: text });
const importFiles = async (files) => {
  const input = page.locator('input[type=file][accept*=".xlsx"]');
  if (!(await input.count())) await page.getByRole('button', { name: 'Add file' }).click(); // the panel may still be open
  await page.locator('input[type=file][accept*=".xlsx"]').first().setInputFiles(files);
  await wait(1500); // import runs in a worker
  // Re-importing an open definition leaves the "Add file" panel open: close it so it isn't in later shots.
  const add = page.getByRole('button', { name: 'Add file' });
  if ((await add.count()) && (await add.getAttribute('aria-expanded')) === 'true') await add.click();
};
const tab = (name) => page.getByRole('tab', { name });
const scroller = () => page.getByLabel(/^Diagram of /);

// ---------------------------------------------------------------- 1. start screen
await page.goto(BASE);
await page.evaluate(() => new Promise((r) => { const q = indexedDB.deleteDatabase('bpmap'); q.onsuccess = q.onerror = q.onblocked = () => r(); }));
await page.goto(BASE);
await page.getByText('Read in this browser. Nothing is uploaded.').waitFor();
await shot('01-start', [
  { loc: page.getByRole('button', { name: 'Choose files' }), label: 'Choose files' },
  { loc: page.getByRole('button', { name: /sample/i }), label: 'Try the sample' },
  { loc: page.getByRole('heading', { name: 'How to get the export' }), label: 'Export guide' },
  { loc: page.getByText('Local only', { exact: true }), label: 'Local only' },
  { loc: page.getByRole('button', { name: /^Theme:/ }), label: 'Theme' },
]);

// ---------------------------------------------------------------- 2. workspace
await importFiles(fixture('change-job-workday-layout.xlsx'));
await page.locator('[data-testid=step]').nth(25).waitFor();
await shot('02-workspace', [
  { loc: page.getByRole('button', { name: 'Add file' }), label: 'Definition tabs' },
  { loc: page.getByRole('radio', { name: 'Executive', exact: true }).locator('..'), label: 'View' },
  { loc: page.getByRole('button', { name: 'Undo (customisations)' }), label: 'Undo / redo' },
  { loc: page.getByLabel('Focus on a role'), label: 'Focus a role' },
  { loc: page.getByRole('button', { name: 'Step list' }), label: 'Step list' },
  { loc: page.locator('details summary').filter({ hasText: 'Export' }), label: 'Export' },
  { loc: page.getByRole('tablist', { name: 'Panels' }), label: 'Panels' },
  { loc: page.getByRole('toolbar', { name: 'Zoom' }), label: 'Zoom' },
  { loc: page.locator('footer'), label: 'Status bar' },
]);

// ---------------------------------------------------------------- 3. reading the diagram (100 %)
await page.getByTestId('zoom-level').click();
await wait(800);
const firstDiamond = page.locator('svg g[data-role=decisions] polygon').first();
const sc = await box(scroller());
// Top of the diagram (stage headers visible), scrolled sideways so the first decision sits right of centre.
const dx = (await box(firstDiamond)).x - sc.x + (await scroller().evaluate((e) => e.scrollLeft));
await scroller().evaluate((e, left) => e.scrollTo({ left, top: 0, behavior: 'instant' }), Math.max(0, dx - 650));
await wait(600);
await shot('03-reading', [
  { loc: page.getByTestId('frozen-lanes').locator('text', { hasText: 'Manager' }).first(), label: 'Lanes = who' },
  { loc: page.locator('svg g[data-role=stage-headers] text').filter({ hasText: /Step d\b/ }), label: 'Stage' },
  { loc: step('Review Change Job').last(), label: 'Conditional step' },
  { loc: firstDiamond, label: 'Decision' },
  { loc: page.locator('svg g[data-role=edges] text', { hasText: 'No, skip' }).first(), label: 'Skip path' },
], { x: sc.x, y: sc.y, width: sc.width, height: sc.height });

// ---------------------------------------------------------------- 4. legend + conditions (fit)
await page.getByRole('button', { name: /Fit height/ }).click();
await scroller().evaluate((e) => e.scrollTo(0, e.scrollHeight));
await wait(400);
const sc2 = await box(scroller());
await shot('04-legend', [
  { loc: page.locator('svg g[data-role=legend]').last(), label: 'Legend' },
  { loc: page.locator('svg g[data-role=conditions]').last(), label: 'Conditions' },
], { x: sc2.x, y: sc2.y, width: sc2.width, height: sc2.height });
await scroller().evaluate((e) => e.scrollTo(0, 0));

// ---------------------------------------------------------------- 5. views
await page.getByRole('radio', { name: 'Executive', exact: true }).click();
await wait(500);
await shot('05-executive', [
  { loc: page.getByRole('radio', { name: 'Executive', exact: true }), label: 'Executive' },
  { loc: page.locator('svg g[data-role=stage-card]').first(), label: 'Stage card' },
]);
await page.getByRole('radio', { name: 'Configurator', exact: true }).click();
await wait(500);
const sc3 = await box(scroller());
await shot('05-configurator', [
  { loc: page.getByRole('radio', { name: 'Configurator', exact: true }), label: 'Configurator' },
  { loc: step('Review: Current Manager').locator('.flex-col'), label: 'Detail lines' },
], { x: 0, y: 0, width: 1440, height: Math.min(900, sc3.y + 420) });
await page.getByRole('radio', { name: 'Process owner', exact: true }).click();

// ---------------------------------------------------------------- 6. step panel + customise
await page.setViewportSize({ width: 1440, height: 1240 });
await step('Assign Pay Group').click();
await page.getByLabel('Label in the flow').fill('Assign pay group (payroll)');
await page.getByLabel('Note (shows as N on the step)').fill('Payroll owns this step');
await wait(700);
await shot('06-step', [
  { loc: step('Assign pay group (payroll)'), label: 'Selected step' },
  { loc: page.getByRole('tab', { name: /^Step/ }), label: 'Step tab', side: 'left' },
  { loc: page.getByRole('tabpanel').locator('dl').first(), label: 'Details', side: 'left' },
  { loc: page.getByRole('tabpanel').getByText('Runs only if', { exact: true }), label: 'Conditions', side: 'left' },
  { loc: page.getByLabel('Label in the flow'), label: 'Label', side: 'left' },
  { loc: page.getByLabel('Note (shows as N on the step)'), label: 'Note', side: 'left' },
  { loc: page.getByRole('tabpanel').getByRole('checkbox').first(), label: 'Hide', side: 'left' },
]);

// ---------------------------------------------------------------- 7. scenario
await page.keyboard.press('Escape');
await tab(/Scenario/).click();
await page.getByLabel('Plain words for C1', { exact: true }).fill('Transfer was requested');
await page.getByRole('radiogroup', { name: 'Answer for C6' }).getByRole('radio', { name: 'No', exact: true }).click();
await page.getByRole('radiogroup', { name: 'Answer for C6' }).scrollIntoViewIfNeeded();
await page.getByRole('tabpanel').evaluate((e) => e.scrollTo(0, 0));
await scroller().evaluate((e) => e.scrollTo({ left: 0, top: 0, behavior: 'instant' })); // selecting a step scrolled the diagram
await wait(500);
await shot('07-scenario', [
  { loc: page.locator('footer').getByText(/^Scenario:/), label: 'Active scenario' },
  { loc: page.getByRole('radiogroup', { name: 'Answer for C1' }), label: 'Answer', side: 'left' },
  { loc: page.getByLabel('Plain words for C1', { exact: true }), label: 'Plain words', side: 'left' },
  { loc: page.getByRole('tabpanel').getByText('Show as a yes/no decision').first(), label: 'Decision', side: 'left' },
  { loc: page.getByPlaceholder(/Promotion/), label: 'Save scenario', side: 'left' },
  { loc: page.getByRole('button', { name: 'Reset' }), label: 'Reset' },
]);
await page.getByRole('button', { name: 'Reset' }).click();

// ---------------------------------------------------------------- 8. health
await tab(/Health/).click();
await wait(400);
await shot('08-health', [
  { loc: tab(/Health/), label: 'Health tab' },
  { loc: page.getByRole('tabpanel').locator('section, details').first(), label: 'Finding', side: 'left' },
  { loc: page.getByRole('button', { name: 'Show step' }).first(), label: 'Show step', side: 'left' },
  { loc: page.getByRole('button', { name: /^Dismiss/ }).first(), label: 'Dismiss', side: 'left' },
]);

// ---------------------------------------------------------------- 9. import report + re-import
await importFiles(fixture('change-job-workday-layout-v2.xlsx')); // same definition, step o removed
await page.locator('[data-testid=step]').nth(24).waitFor();
await tab(/^Import/).click();
await page.getByTestId('orphans').waitFor();
await shot('09-import', [
  { loc: tab(/^Import/), label: 'Import tab' },
  { loc: page.getByTestId('orphans'), label: 'Kept edits', side: 'left' },
  { loc: page.getByTestId('orphans').getByRole('button'), label: 'Remove', side: 'left' },
  { loc: page.getByRole('tabpanel').locator('dl').first(), label: 'Report', side: 'left' },
]);
await importFiles(fixture('change-job-workday-layout.xlsx')); // back to 26 steps; the note re-attaches
await page.locator('[data-testid=step]').nth(25).waitFor();
await page.setViewportSize({ width: 1440, height: 900 });

// ---------------------------------------------------------------- 10. focus a role
await page.getByLabel('Focus on a role').selectOption({ label: 'Payroll Partner' });
await wait(900);
await shot('10-focus', [
  { loc: page.getByLabel('Focus on a role'), label: 'Choose a role' },
  { loc: page.getByRole('group', { name: 'Steps for this role' }), label: 'Previous / next' },
  { loc: step('Assign pay group (payroll)'), label: 'Role step' },
  { loc: page.getByTestId('dimmed-lane').first(), label: 'Other lanes dimmed' },
]);
await page.getByLabel('Focus on a role').selectOption({ label: 'All roles' });
await scroller().evaluate((e) => e.scrollTo(0, 0));

// ---------------------------------------------------------------- 11. step list
await page.getByRole('button', { name: 'Step list' }).click();
await wait(400);
await shot('11-step-list', [
  { loc: page.getByRole('button', { name: 'Step list' }), label: 'Step list' },
  { loc: page.getByRole('rowheader').nth(1), label: 'Order' },
  { loc: page.getByRole('table').getByRole('button').nth(1), label: 'Open step' },
  { loc: page.getByRole('columnheader', { name: /Runs only if/ }), label: 'Conditions' },
]);
await page.getByRole('button', { name: 'Step list' }).click();

// ---------------------------------------------------------------- 12. arrange
await page.getByRole('button', { name: 'Arrange', exact: true }).click();
await step('Review: Receiving Manager').focus();
for (let i = 0; i < 3; i++) await page.keyboard.press('Shift+ArrowDown');
await wait(500);
await shot('12-arrange', [
  { loc: page.getByRole('button', { name: 'Arrange', exact: true }), label: 'Arrange' },
  { loc: step('Review: Receiving Manager'), label: 'Moved step' },
  { loc: page.getByRole('button', { name: 'Reset layout' }), label: 'Reset layout' },
]);
await page.getByRole('button', { name: 'Reset layout' }).click();
await page.getByRole('button', { name: 'Arrange', exact: true }).click();

// ---------------------------------------------------------------- 13. subprocesses
await importFiles([fixture('hire-with-subprocesses.xlsx'), fixture('propose-compensation-hire.xlsx')]);
await page.getByRole('button', { name: /^Close Propose Compensation Hire/ }).waitFor();
await page.getByRole('button', { name: 'Hire (Default Definition)', exact: true }).click();
await step('Propose Compensation Hire').click();
await shot('13-subprocess', [
  { loc: step('Propose Compensation Hire'), label: 'Sub-process step' },
  { loc: page.getByTestId('subprocess-link'), label: 'Runs a subprocess', side: 'left' },
  { loc: page.getByTestId('subprocess-link').getByRole('button'), label: 'Open', side: 'left' },
  { loc: page.locator('button[title^="Subprocess of Hire"]'), label: 'Subprocess tab' },
]);
await page.getByTestId('subprocess-link').getByRole('button').click();
await wait(500);
await shot('13-back', [
  { loc: page.getByTestId('back-from-subprocess'), label: 'Back' },
  { loc: page.locator('[aria-current=page]'), label: 'Subprocess open' },
], { x: 0, y: 0, width: 1440, height: 330 });
await page.getByTestId('back-from-subprocess').click();
await tab(/^Import/).click();
await shot('13-summary', [{ loc: page.getByTestId('subprocess-summary'), label: 'Subprocesses', side: 'left' }], { x: 560, y: 90, width: 880, height: 420 });

// ---------------------------------------------------------------- 14. export menu
await page.setViewportSize({ width: 1440, height: 1240 }); // the menu is taller than 900 px
await page.getByRole('button', { name: 'Change Job (Default Definition)', exact: true }).click();
await page.locator('details summary').filter({ hasText: 'Export' }).click();
await wait(400);
await shot('14-export', [
  { loc: page.getByRole('menuitem', { name: /^PDF/ }).first(), label: 'This view', side: 'left' },
  { loc: page.getByRole('menuitem', { name: /^PowerPoint/ }).first(), label: 'PowerPoint', side: 'left' },
  { loc: page.getByRole('menuitem', { name: /^Excel/ }).first(), label: 'Excel', side: 'left' },
  { loc: page.getByRole('menuitem', { name: /^PDF pack/ }), label: 'Packs', side: 'left' },
  { loc: page.getByRole('menuitem', { name: /^Project file/ }), label: 'Project file', side: 'left' },
  { loc: page.getByRole('menuitem', { name: /^Customisations only/ }), label: 'Customisations', side: 'left' },
  { loc: page.getByRole('button', { name: /^Open a project/ }), label: 'Open' },
]);
await page.keyboard.press('Escape');
await page.locator('details[open] summary').click().catch(() => undefined);

await page.setViewportSize({ width: 1440, height: 900 });
// ---------------------------------------------------------------- 15. close + undo
await page.getByRole('button', { name: /^Close Propose Compensation Hire/ }).click();
await page.getByTestId('removed-toast').waitFor();
await shot('15-close', [
  { loc: page.getByRole('button', { name: /^Close Hire/ }), label: 'Close (×)' },
  { loc: page.getByTestId('removed-toast').getByRole('button', { name: 'Undo' }), label: 'Undo' },
]);
await page.getByTestId('removed-toast').getByRole('button', { name: 'Undo' }).click();

// ---------------------------------------------------------------- 16. tablet + dark
await page.setViewportSize({ width: 820, height: 1000 });
await page.getByRole('button', { name: 'Change Job (Default Definition)', exact: true }).click();
await step('Assign pay group (payroll)').click();
await page.getByTestId('details-drawer').waitFor();
await shot('16-tablet', [
  { loc: page.getByRole('button', { name: 'Show details panel' }), label: 'Details' },
  { loc: page.getByTestId('details-drawer').locator('aside'), label: 'Drawer', side: 'left' },
]);
await page.getByTestId('details-drawer').getByRole('button', { name: 'Close details' }).last().click();
await page.setViewportSize({ width: 1440, height: 900 });
await page.emulateMedia({ colorScheme: 'dark' });
await wait(500);
await shot('17-dark', [{ loc: page.getByRole('button', { name: /^Theme:/ }), label: 'Theme' }]);

writeFileSync(`${OUT}/meta.json`, JSON.stringify(meta, null, 1));
await browser.close();
console.log(`done: ${Object.keys(meta).length} shots`);
