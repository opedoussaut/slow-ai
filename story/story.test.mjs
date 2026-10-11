// Browser tests for the SlowAI story. Run: node --test story/story.test.mjs
// Set STORY_URL to test a deployed site instead of a local server, e.g.
// STORY_URL=https://opedoussaut.github.io/slow-ai/story/ node --test story/story.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { chromium } from 'playwright';
import { predict, featureVector } from './models.js';

const ROOT = resolve('.');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' };
let server, browser, base;

before(async () => {
  if (process.env.STORY_URL) {
    base = process.env.STORY_URL;
  } else {
    server = createServer(async (req, res) => {
      const path = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname)).replace(/^([/\\])+/, '');
      const file = join(ROOT, path.endsWith('/') || path === '' ? join(path, 'index.html') : path);
      if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
      try { res.writeHead(200, { 'Content-Type': TYPES[extname(file)] || 'application/octet-stream' }).end(await readFile(file)); }
      catch { res.writeHead(404).end('not found'); }
    });
    await new Promise((r) => server.listen(0, r));
    base = `http://localhost:${server.address().port}/story/`;
  }
  browser = await chromium.launch();
});
after(async () => { await browser?.close(); server?.close(); });

async function open(options = {}) {
  const context = await browser.newContext(options);
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(base);
  await page.waitForSelector('html[data-ready="true"]', { timeout: 20000 });
  return { page, errors };
}

test('loads without errors and shows the simulated raw record count', async () => {
  const { page, errors } = await open({ viewport: { width: 1280, height: 900 } });
  assert.match(await page.title(), /Think first/);
  assert.match(await page.locator('#rawTotal').innerText(), /^\d{2},\d{3}$/);
  assert.deepEqual(errors, []);
  await page.close();
});

test('the one-hour overview shows the campus simulation counts', async () => {
  const campus = JSON.parse(await readFile('story/data/campus-v1.json', 'utf8'));
  const { page } = await open();
  assert.equal(await page.locator('#hourRoutes').getAttribute('data-loaded'), 'true');
  const shown = await page.locator('#hourRoutes .hour-count').allInnerTexts();
  const fmt = new Intl.NumberFormat('en-GB');
  assert.deepEqual(shown, ['1', '2', '3', '4'].map((k) => fmt.format(campus.route_counts[k])));
  const esc = await page.locator('#hourEscalation').innerText();
  assert.match(esc, new RegExp(`right ${campus.escalation_summary.specialized_correct} times`));
  await page.close();
});

test('loads the real published steel evidence', async () => {
  const { page } = await open();
  assert.equal(await page.locator('#steelAcc').getAttribute('data-loaded'), 'true');
  const text = await page.locator('#steelAcc').innerText();
  assert.match(text, /34\.8%/);
  assert.match(text, /69\.6%/);
  assert.match(text, /1,941 records/);
  await page.close();
});

test('every number carries an evidence badge of its kind', async () => {
  const { page } = await open();
  const problems = await page.evaluate(() => {
    const kinds = new Set(['measured', 'simulation', 'illustrative', 'not-measured']);
    const out = [];
    for (const n of document.querySelectorAll('[data-metric]')) {
      const kind = n.getAttribute('data-ev');
      const scope = n.closest('[data-ev-scope]');
      if (!kinds.has(kind)) out.push(`no kind: ${n.textContent}`);
      else if (!scope || !scope.querySelector(`.ev[data-kind="${kind}"]`)) out.push(`no ${kind} badge near: ${n.textContent}`);
    }
    return { out, count: document.querySelectorAll('[data-metric]').length };
  });
  assert.ok(problems.count > 20, `expected many metrics, got ${problems.count}`);
  assert.deepEqual(problems.out, []);
  await page.close();
});

test('four routes, with route 3 reached by escalation and route 4 not run', async () => {
  const { page } = await open();
  const routes = page.locator('#routes .route');
  assert.equal(await routes.count(), 4);
  assert.deepEqual(await routes.evaluateAll((els) => els.map((e) => e.dataset.route)), ['1', '2', '3', '4']);
  assert.match(await routes.nth(2).innerText(), /Escalated from route 2/);
  assert.match(await routes.nth(2).innerText(), /Branch restriction/);
  assert.match(await routes.nth(3).innerText(), /Not run in this demonstration/);
  await page.close();
});

test('a lax contract accepts a wrong answer; a strict one escalates', async () => {
  const { page } = await open();
  const setThreshold = (v) => page.locator('#threshold').evaluate((el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); }, v);
  await setThreshold('0.45');
  assert.match(await page.locator('#verdict').innerText(), /Accepted, and wrong/);
  assert.equal(await page.locator('#specialized').isHidden(), true);
  await setThreshold('0.90');
  assert.match(await page.locator('#verdict').innerText(), /Escalated/);
  assert.equal(await page.locator('#specialized').isVisible(), true);
  await page.close();
});

test('the subtle fault exposes what curation misses', async () => {
  const { page } = await open();
  await page.locator('#curate [data-variant="subtle"]').click();
  assert.equal(await page.locator('#recallValue').innerText(), '2 of 4');
  assert.match(await page.locator('#recallNote').innerText(), /Missed: R07 return temperature, R07 GPU temperature/);
  assert.match(await page.locator('#routes .route').nth(1).innerText(), /probability/);
  await page.close();
});

test('the decision record downloads as JSON and requires approval', async () => {
  const { page } = await open();
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#downloadRecord').click()]);
  const record = JSON.parse(await readFile(await download.path(), 'utf8'));
  assert.equal(record.evidence_kind, 'reproducible_simulation');
  assert.equal(record.approval.required, true);
  assert.equal(record.routes.find((r) => r.route === 4).note, 'not run');
  assert.ok(record.evidence.every((e) => e.records.length > 0));
  await page.close();
});

test('mobile layout has no horizontal overflow', async () => {
  const { page } = await open({ viewport: { width: 375, height: 812 } });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert.ok(overflow <= 0, `page is ${overflow}px wider than the viewport`);
  await page.close();
});

test('reduced motion shows the final curation state immediately', async () => {
  const { page } = await open({ reducedMotion: 'reduce' });
  const width = await page.locator('#funnel .stage-bar i').first().evaluate((e) => e.style.width);
  assert.equal(width, '100%');
  await page.close();
});

test('browser models match the Python generator exactly', async () => {
  const bundle = JSON.parse(await readFile('story/data/scenario-v1.json', 'utf8'));
  const script = `
import json
from story.generator.scenario import predict
b = json.load(open('story/data/scenario-v1.json'))
out = {}
for vk, v in b['variants'].items():
    for mk in ('actionable', 'compact_fault', 'specialized_fault'):
        m = b['models'][mk]
        out[vk + ':' + mk] = predict(m, [v['features'][f] for f in m['features']])
print(json.dumps(out))`;
  const py = JSON.parse(execFileSync('python3', ['-c', script], { encoding: 'utf8' }));
  for (const [key, expected] of Object.entries(py)) {
    const [vk, mk] = key.split(':');
    const got = predict(bundle.models[mk], featureVector(bundle.models[mk], bundle.variants[vk].features));
    got.forEach((p, i) => assert.ok(Math.abs(p - expected[i]) < 1e-9, `${key}[${i}] ${p} vs ${expected[i]}`));
  }
});

test('no serious accessibility violations (axe-core)', async () => {
  const { AxeBuilder } = await import('@axe-core/playwright').then((m) => ({ AxeBuilder: m.default ?? m.AxeBuilder }));
  const { page } = await open();
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  const serious = results.violations.filter((v) => ['serious', 'critical'].includes(v.impact))
    .map((v) => `${v.id}: ${v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(', ')}`);
  assert.deepEqual(serious, []);
  await page.close();
});
