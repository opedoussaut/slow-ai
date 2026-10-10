import test from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const url=pathToFileURL(resolve('challenge/index.html')).href;

test('Intelligence Challenge loads, switches scenarios and exports evidence', async () => {
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:900},acceptDownloads:true});
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(url);
    await assert.equal(await page.title(),'ƧlowAI | The Intelligence Challenge');
    await assert.equal(await page.locator('#testCount').textContent(),'90');
    for(const scenario of ['nominal','drift','critical','conflict']){
      await page.locator('[data-case="'+scenario+'"]').click();
      assert.equal(await page.locator('[data-case="'+scenario+'"]').getAttribute('aria-pressed'),'true');
      assert.match(await page.locator('#ruleState').textContent(),/^(NORMAL|INSPECT|STOP)$/);
      assert.match(await page.locator('#knnState').textContent(),/^(NORMAL|INSPECT|STOP)$/);
    }
    assert.match(await page.locator('#rulesAcc').textContent(),/^\d+\.\d%$/);
    assert.match(await page.locator('#knnAcc').textContent(),/^\d+\.\d%$/);
    const downloadPromise=page.waitForEvent('download');
    await page.locator('#download').click();
    const download=await downloadPromise;
    assert.equal(download.suggestedFilename(),'slowai-intelligence-challenge-001.json');
    const stream=await download.createReadStream();
    const chunks=[];
    for await (const chunk of stream) chunks.push(chunk);
    const report=JSON.parse(Buffer.concat(chunks).toString('utf8'));
    assert.equal(report.training.length,180);
    assert.equal(report.testing.length,90);
    assert.equal(report.results.rules.total,90);
    assert.equal(report.results.knn.total,90);
    assert.equal(report.measurements.energy_joules,null);
    assert.equal(report.measurements.frontier_ai,null);
    assert.deepEqual(errors,[]);
    await page.setViewportSize({width:390,height:844});
    await assert.equal(await page.locator('h1').isVisible(),true);
    await assert.equal(await page.locator('#download').isVisible(),true);
  } finally {
    await browser.close();
  }
});
