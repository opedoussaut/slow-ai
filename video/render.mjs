// Renders video/scene.html frame by frame and encodes an MP4 with ffmpeg.
// Usage (from the repository root, with a static server on port 8765):
//   python -m http.server 8765 &
//   node video/render.mjs slowai-story.mp4
// Requires: playwright (chromium) and ffmpeg on PATH.
import { spawn } from 'node:child_process';
import { chromium } from 'playwright';

const out = process.argv[2] || 'slowai-story.mp4';
const FPS = 30, BASE = process.env.SCENE_URL || 'http://localhost:8765/video/scene-v3.html';

const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(BASE);
await page.waitForFunction(() => window.__ready === true, { timeout: 30000 });
const DURATION = await page.evaluate(() => window.__duration || 90);
const frames = FPS * DURATION;
for (let i = 0; i < frames; i++) {
  await page.evaluate((t) => window.__render(t), i / FPS);
  const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % 300 === 0) console.log(`frame ${i}/${frames}`);
}
ff.stdin.end();
await new Promise((r, j) => ff.on('close', (c) => (c === 0 ? r() : j(new Error(`ffmpeg exited ${c}`)))));
await browser.close();
console.log(`Wrote ${out}`);
