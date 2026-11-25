/* CLI verification for the published model-switching page. Requires Playwright.
 * SCV_CHROMIUM_PATH optionally selects an installed Chromium executable.
 * Screenshots and the report stay in a supplied --output directory.
 */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const root = path.resolve(__dirname,'../..');
const docs = path.join(root,'docs');
const site = path.join(docs,'scv-showcase');
const outputIndex = process.argv.indexOf('--output');
if(outputIndex<0 || !process.argv[outputIndex+1]) throw new Error('Provide --output <private QA directory>');
const output = path.resolve(process.argv[outputIndex+1]);
fs.mkdirSync(output,{recursive:true});
const data = JSON.parse(fs.readFileSync(path.join(site,'results.json'),'utf8'));
const models = data.models;
const mime={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.webp':'image/webp','.mp4':'video/mp4','.mp3':'audio/mpeg','.md':'text/plain; charset=utf-8'};
const server=http.createServer((req,res)=>{
  let file=path.resolve(docs,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if(!file.startsWith(docs+path.sep) && file!==docs){res.writeHead(403).end();return;}
  try{
    if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');
    const size=fs.statSync(file).size;
    const headers={'Content-Type':mime[path.extname(file)]||'application/octet-stream','Accept-Ranges':'bytes'};
    const range=/bytes=(\d+)-(\d*)/.exec(req.headers.range||'');
    if(range){
      const start=Number(range[1]),end=Math.min(range[2]?Number(range[2]):size-1,size-1);
      res.writeHead(206,{...headers,'Content-Range':`bytes ${start}-${end}/${size}`,'Content-Length':end-start+1});
      fs.createReadStream(file,{start,end}).pipe(res);
    }else{res.writeHead(200,{...headers,'Content-Length':size});fs.createReadStream(file).pipe(res);}
  }catch{res.writeHead(404).end();}
});

(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  const browser=await chromium.launch({headless:true,...(process.env.SCV_CHROMIUM_PATH?{executablePath:process.env.SCV_CHROMIUM_PATH}:{})});
  const failures=[],checks=[];
  try{
    for(const width of [1440,768,390,360]){
      const page=await browser.newPage({viewport:{width,height:1100},reducedMotion:'reduce'});
      page.on('pageerror',error=>failures.push(error.message));
      page.on('response',response=>{if(response.status()>=400)failures.push(`${response.status()} ${response.url()}`);});
      await page.goto(base+'/scv-showcase/',{waitUntil:'networkidle'});
      assert.equal(await page.locator('.score-table tbody tr').count(),2);
      assert.equal(await page.locator('.model-tabs [role=tab]').count(),2);
      for(const model of models){
        assert.ok((await page.locator('.score-table').innerText()).includes(model.scores.total.toFixed(2)));
      }
      const urls=await page.evaluate(()=>{
        const elements=[...document.querySelectorAll('[href],[src]')];
        for(const t of document.querySelectorAll('template'))elements.push(...t.content.querySelectorAll('[href],[src]'));
        return elements.flatMap(e=>['href','src'].map(k=>e.getAttribute(k)).filter(Boolean));
      });
      for(const value of urls){
        if(value.startsWith('#') || /^(https?:|data:)/.test(value))continue;
        const url=new URL(value,base+'/scv-showcase/');
        assert.ok(fs.existsSync(path.join(docs,decodeURIComponent(url.pathname))),value);
      }
      for(const model of models){
        await page.locator(`#model-tab-${model.id}`).click();
        await page.waitForFunction(()=>document.querySelector('video').readyState>=1);
        for(const section of ['results','execution','analysis']){
          assert.equal(await page.locator(`[data-model-section=${section}]`).getAttribute('data-model'),model.id);
        }
        const video=page.locator('#showcase-video');
        const metadata=await video.evaluate(v=>({width:v.videoWidth,height:v.videoHeight,duration:v.duration,src:new URL(v.currentSrc).pathname}));
        assert.equal(metadata.width,model.delivery.width);
        assert.equal(metadata.height,model.delivery.height);
        assert.ok(Math.abs(metadata.duration-model.delivery.video_duration_seconds)<.03);
        assert.ok(metadata.src.endsWith(model.delivery.video));
        assert.equal(await page.locator('#model-results-panel .detail-evidence').count(),0);
        assert.equal(await page.locator('#model-analysis-panel .detail-evidence').count(),3);
        assert.equal(await page.locator('.model-score-cards').isVisible(),width<=600);
        assert.equal(await page.locator('body').evaluate(e=>e.scrollWidth<=window.innerWidth),true,`overflow ${width}/${model.id}`);
        assert.ok((await page.locator('#model-results-panel .runtime-list').innerText()).includes(String(model.runtime.tool_calls)));
        for(const link of await page.locator('#model-results-panel .delivery-links a').all()){
          const href=await link.getAttribute('href');
          assert.ok(href.startsWith(model.assets_root+'/'),href);
        }
        assert.equal(await page.locator('[data-selected-asset]').getAttribute('href'),model.delivery.asset);
        for(const view of ['front','back','left','right','top','bottom']){
          await page.locator(`[data-view=${view}]`).click();
          await page.waitForFunction(()=>{const e=document.querySelector('#comparison-image');return e.complete&&e.naturalWidth>0;});
          assert.equal(await page.locator('#comparison-image').getAttribute('src'),`${model.assets_root}/comparison/${view}.webp`);
          assert.equal(await page.locator('#comparison-reconstruction').getAttribute('href'),`${model.assets_root}/reconstruction/${view}.png`);
        }
        await page.locator('#comparison-zoom').click();
        assert.equal(await page.locator('#image-dialog').evaluate(d=>d.open),true);
        assert.ok((await page.locator('#dialog-image').getAttribute('src')).includes(model.assets_root+'/comparison/bottom.webp'));
        await page.locator('.dialog-close').click();
        const lastShot=page.locator('#model-execution-panel .shot-timeline [data-seek]').last();
        const target=Number(await lastShot.getAttribute('data-seek'));
        await lastShot.click();
        await page.waitForFunction(t=>Math.abs(document.querySelector('video').currentTime-t)<.03,target);
        await page.locator('#model-analysis-panel .detail-evidence summary').first().click();
        const evidence=page.locator('#model-analysis-panel .detail-evidence [data-seek]').first();
        const evidenceTime=Number(await evidence.getAttribute('data-seek'));
        await evidence.click();
        await page.waitForFunction(t=>Math.abs(document.querySelector('video').currentTime-t)<.03,evidenceTime);
        await video.evaluate(v=>{v.muted=true;return v.play();});
        await page.waitForFunction(t=>document.querySelector('video').currentTime>t+.15,evidenceTime);
        await video.evaluate(v=>v.pause());
        assert.equal((await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.length===new Set(ids).size;})),true);
        if(width===1440 || width===390){
          await page.locator('#results').evaluate(e=>window.scrollTo(0,e.offsetTop));
          await page.screenshot({path:path.join(output,`${model.id}-results-${width}.png`)});
          await page.locator('#analysis').evaluate(e=>e.scrollIntoView({block:'start',behavior:'instant'}));
          await page.screenshot({path:path.join(output,`${model.id}-analysis-${width}.png`)});
        }
        checks.push({width,model:model.id,score:model.scores.total,media:metadata,sixViews:true,zoom:true,shotSeek:true,evidenceSeek:true,playback:true,overflow:false});
      }
      // A playing Sol video must stop when its entire panel is replaced.
      const previousVideo=await page.locator('video').elementHandle();
      await previousVideo.evaluate(v=>{v.muted=true;return v.play();});
      await page.locator('#model-tab-astra62-xhigh').click();
      assert.equal(await previousVideo.evaluate(v=>v.paused),true);
      await page.locator('#model-tab-astra62-xhigh').focus();
      await page.keyboard.press('ArrowRight');
      assert.equal(await page.locator('#model-tab-sol62-xhigh').getAttribute('aria-selected'),'true');
      assert.equal(await page.locator('#model-tab-sol62-xhigh').evaluate(e=>e===document.activeElement),true);
      assert.equal(new URL(page.url()).searchParams.get('model'),'sol62-xhigh');
      await page.locator('#analysis').evaluate(e=>e.scrollIntoView({block:'start',behavior:'instant'}));
      await page.locator('#model-tab-astra62-xhigh').click();
      assert.ok(await page.locator('#analysis').evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=document.querySelector('#model-switcher').offsetHeight&&r.top<window.innerHeight/2;}));
      await page.locator('#model-tab-sol62-xhigh').click();
      await page.reload({waitUntil:'networkidle'});
      assert.equal(await page.locator('#model-results-panel').getAttribute('data-model'),'sol62-xhigh');
      await page.goto(base+'/scv-showcase/?model=invalid',{waitUntil:'networkidle'});
      assert.equal(await page.locator('#model-results-panel').getAttribute('data-model'),'astra62-xhigh');
      await page.close();
    }
    const page=await browser.newPage();
    await page.goto(base+'/',{waitUntil:'networkidle'});
    const card=await page.locator('a.case-card[href="scv-showcase/"]').innerText();
    assert.ok(card.includes('35.38')&&card.includes('32.90'));
    assert.deepEqual(failures,[]);
    fs.writeFileSync(path.join(output,'comparison-checks.json'),JSON.stringify({checks,failures,catalog:true,keyboard:true,deepLink:true,reload:true,stopsPreviousVideo:true},null,2));
    console.log(JSON.stringify({passed:true,widths:[1440,768,390,360],models:models.map(m=>m.id),output}));
  }finally{await browser.close();server.close();}
})().catch(error=>{console.error(error);process.exitCode=1;server.close();});
