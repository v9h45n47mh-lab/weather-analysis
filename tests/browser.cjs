const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
let chromium;try{({chromium}=require('playwright'));}catch{({chromium}=require(path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES,'playwright')));}
const root=path.resolve(__dirname,'..'),screens=path.join(root,'test-results');fs.mkdirSync(screens,{recursive:true});
const server=http.createServer((req,res)=>{const requested=decodeURIComponent(req.url.split('?')[0]);const file=path.resolve(root,'.'+(requested==='/'?'/tests/demo.html':requested));if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}try{res.setHeader('content-type',file.endsWith('.js')?'application/javascript':file.endsWith('.json')?'application/json':'text/html');res.end(fs.readFileSync(file));}catch{res.writeHead(404);res.end();}});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,args:['--no-sandbox'],...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1100,height:1100}}),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:'+server.address().port);
  const card=()=>page.locator('weather-analysis-card').first(),action=name=>card().locator('[data-action="'+name+'"]');
  await card().locator('#wa-current').waitFor();assert.match(await card().locator('#wa-current').innerText(),/11,4/);
  assert.equal(await action('period').first().getAttribute('aria-pressed'),'true');
  assert.equal(await card().locator('.wa-chart .wa-hit').count(),24);
  await card().locator('.wa-hit').first().focus();assert.match(await card().locator('#wa-inspector').innerText(),/Min.*Max/);
  await action('period').filter({hasText:'Monat'}).click();await page.waitForFunction(()=>demo.card._data?.chart_daily);
  assert.match(await card().locator('.wa-inspector').innerText(),/Tageswerte/);
  await action('period').filter({hasText:'Zeitraum'}).click();
  const before=await page.evaluate(()=>demo.calls.filter(x=>x.type==='weather_analysis/analyse').length);
  await card().locator('#wa-from').fill('2026-10-01');await card().locator('#wa-to').fill('2026-10-31');
  assert.equal(await page.evaluate(()=>demo.calls.filter(x=>x.type==='weather_analysis/analyse').length),before);
  await action('custom-apply').click();await page.waitForFunction(()=>demo.calls.at(-1)?.end_date==='2026-10-31');
  await action('navigate').filter({hasText:'Statistik'}).click();
  await card().locator('#wa-frost').waitFor();assert.match(await card().locator('#wa-frost').innerText(),/42 %/);
  assert.match(await card().locator('#wa-records-content').innerText(),/Datum.*nicht gespeichert/);
  await card().locator('[aria-controls="wa-months-content"]').click();assert.equal(await card().getByRole('table',{name:'Monatliche Temperaturwerte'}).count(),1);
  for(const width of [1100,390,320])for(const dark of [false,true]){
   await page.setViewportSize({width,height:1100});await page.evaluate(d=>document.body.classList.toggle('dark',d),dark);
   await action('navigate').filter({hasText:'Verlauf'}).click();
   await page.screenshot({path:path.join(screens,`overview-${width}-${dark?'dark':'light'}.png`),fullPage:true});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overview overflow at ${width}`);
   await card().locator('[data-page="statistics"]').click();
   await page.screenshot({path:path.join(screens,`statistics-${width}-${dark?'dark':'light'}.png`),fullPage:true});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Statistics overflow at ${width}`);
   await card().locator('[data-page="settings"]').click();
   await page.screenshot({path:path.join(screens,`settings-${width}-${dark?'dark':'light'}.png`),fullPage:true});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Settings overflow at ${width}`);
   assert.match(await card().locator('.version-info').innerText(),/1\.7\.0/);
  }
  await page.setViewportSize({width:1100,height:1100});await page.evaluate(()=>document.body.classList.remove('dark'));
  await card().locator('#wa-title').fill('Nordseite');await card().locator('#wa-sensor').selectOption('sensor.north');
  await action('save-settings').click();await card().locator('#wa-current').waitFor();
  assert.equal(await page.evaluate(()=>demo.saved.get('test-garden').entity),'sensor.north');
  assert.match(await card().locator('h3').first().innerText(),/Nordseite/);
  await card().locator('[data-page="settings"]').click();await card().locator('#wa-title').fill('Entwurf');
  await page.evaluate(()=>{demo.hass.states['sensor.north'].state='12';demo.card.hass=demo.hass;});
  assert.equal(await card().locator('#wa-title').inputValue(),'Entwurf');
  await card().locator('#wa-base').fill('10');await card().locator('#wa-limit').fill('15');await action('save-settings').click();
  await card().getByRole('alert').waitFor();assert.equal(await card().locator('#wa-title').inputValue(),'Entwurf');
  await action('cancel-settings').click();assert.equal(await page.evaluate(()=>demo.saved.get('test-garden').title),'Nordseite');
  await card().locator('[data-page="settings"]').click();await card().locator('#wa-title').fill('<img src=x onerror=alert(1)>');await action('save-settings').click();
  await card().locator('#wa-current').waitFor();assert.equal(await card().locator('img').count(),0);assert.match(await card().locator('h3').first().innerText(),/<img/);
  await page.evaluate(()=>demo.fail=true);await action('reload').click();await card().getByRole('alert').waitFor();
  await page.evaluate(()=>demo.fail=false);await action('reload').click();await page.waitForFunction(()=>!demo.card._error);
  // A stale slow response must not overwrite a newer period selection.
  await page.evaluate(()=>demo.delayNext=350);await action('period').filter({hasText:'Gestern'}).click();await action('period').filter({hasText:'Heute',exact:true}).click();
  await page.waitForFunction(()=>demo.card._data&&demo.card.period==='today');
  const expected=await page.evaluate(()=>demo.card._dates()[0]);await page.waitForTimeout(400);
  assert.equal(await page.evaluate(()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Berlin'}).format(new Date(demo.card._data.start*1000))),expected);
  // Independent card IDs preserve the first card's settings.
  await page.evaluate(()=>{const c=document.createElement('weather-analysis-card');c.setConfig({card_id:'second',entity:'sensor.garden',title:'Zweite Karte'});document.body.append(c);c.hass=demo.hass;demo.second=c;});
  await page.locator('weather-analysis-card').nth(1).locator('#wa-current').waitFor();
  assert.equal(await page.evaluate(()=>demo.second.settings.entity),'sensor.garden');
  assert.notEqual(await page.evaluate(()=>customElements.get('weather-analysis-card').getStubConfig().card_id),await page.evaluate(()=>customElements.get('weather-analysis-card').getStubConfig().card_id));
  await page.evaluate(()=>{demo.second.remove();demo.admin=false;demo.card.setConfig({card_id:'viewer',entity:'sensor.garden'});});
  await card().locator('#wa-current').waitFor();await card().locator('[data-page="settings"]').click();
  assert.equal(await action('save-settings').count(),0);assert(await card().locator('#wa-sensor').isDisabled());
  await page.evaluate(()=>{demo.empty=true;demo.card.setConfig({card_id:'empty'});});
  await page.waitForFunction(()=>demo.card._ready);assert.match(await card().innerText(),/Integration Weather Analysis hinzufügen/);
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(screens,'browser-summary.json'),JSON.stringify({passed:true,viewports:[1100,390,320],themes:['light','dark'],screenshots:18,errors},null,2));
  console.log('Browser checks passed: periods, charts, settings, stale responses, permissions, independent cards, 3 widths × 2 themes.');
 }finally{await browser.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});
