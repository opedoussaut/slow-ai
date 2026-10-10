import test from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

test('steel explorer loads and validates real evidence locally', async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    const errors=[];
    page.on('pageerror', e=>errors.push(e.message));
    await page.goto(pathToFileURL(resolve('challenge/steel.html')).href);
    assert.match(await page.title(),/Steel Evidence Explorer/);
    assert.equal(await page.locator('#results').isVisible(),false);
    await page.locator('#file').setInputFiles({
      name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{}')
    });
    await page.locator('#status').getByText(/Unable to load evidence/).waitFor();
    assert.equal(await page.locator('#results').isVisible(),false);
    const classes=['Pastry','Z_Scratch','K_Scatch','Stains','Dirtiness','Bumps','Other_Faults'];
    const metrics=Object.fromEntries(classes.map(c=>[c,{support:1,precision:1,recall:1,f1:1}]));
    const evidence={
      experiment:'UCI Steel Plates Faults 7-class classification',
      dataset_size:14,train_count:7,test_count:7,classes,
      source_sha256:'a'.repeat(64),
      results:Object.fromEntries(['majority_class_non_ai','knn_3'].map(k=>[k,{
        accuracy:1,macro_f1:1,per_class:metrics,
        predictions:classes.map((c,i)=>({id:i,expected:c,predicted:c}))
      }]))
    };
    await page.locator('#file').setInputFiles({
      name:'evidence.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(evidence))
    });
    assert.equal(await page.locator('#results').isVisible(),true);
    assert.equal(await page.locator('#classgrid .classcard').count(),7);
    assert.equal(await page.locator('#predictions tr').count(),7);
    await page.locator('#model').selectOption('knn_3');
    assert.equal(await page.locator('#predictions tr').count(),7);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.locator('h1').isVisible(),true);
    assert.deepEqual(errors,[]);
  } finally {await browser.close()}
});
