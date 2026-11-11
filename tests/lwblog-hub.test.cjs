const {test}=require('node:test');
const assert=require('node:assert/strict');
const modulePromise=import('../integrations/lwblog/radar-hub.mjs');
const payload=()=>({latest:{date:'2026-11-11',url:'https://leeeway.github.io/daily-trend-radar/daily/2026-11-11.html'},entry_count:388,
 latest_discoveries:{date:'2026-11-11',total:16,repos:2,stories:8,advisories:6}});
test('hub links preserve radar origin and reading filters',async()=>{
 const {hubLinks}=await modulePromise;
 assert.equal(new URL(hubLinks.discoveries).searchParams.get('fresh'),'1');
 assert.equal(new URL(hubLinks.growth).searchParams.get('sort'),'growth');
 assert.equal(new URL(hubLinks.reading).searchParams.get('unread'),'1');
 assert.equal(new URL(hubLinks.saved).searchParams.get('saved'),'1');
 for(const url of Object.values(hubLinks)) assert.equal(new URL(url).origin,'https://leeeway.github.io');
});
test('validates calendar dates and reconstructs daily and ISO week destinations',async()=>{
 const {parseLatest,weeklyUrl}=await modulePromise;
 assert.equal(parseLatest(payload()).weekly,'https://leeeway.github.io/daily-trend-radar/weekly/2026-W46.html');
 assert.equal(weeklyUrl('2021-01-01'),'https://leeeway.github.io/daily-trend-radar/weekly/2020-W53.html');
 for(const date of ['2026-02-30','2026-13-01','invalid']) assert.throws(()=>parseLatest({latest:{date}}));
 assert.throws(()=>parseLatest({latest:{date:'2026-11-11',url:'https://evil.example/'}}));
 assert.throws(()=>parseLatest({latest:{date:'2026-11-11',url:'javascript:alert(1)'}}));
});
test('count validation handles zero, missing, mismatched and stale API stats',async()=>{
 const {parseLatest}=await modulePromise;
 assert.equal(parseLatest(payload()).discoveries.total,16);
 const p=payload();p.latest_discoveries={date:'2026-11-11',total:0,repos:0,stories:0,advisories:0};p.entry_count=0;
 assert.equal(parseLatest(p).discoveries.total,0);assert.equal(parseLatest(p).entryCount,0);
 for(const stats of [undefined,{...payload().latest_discoveries,date:'2026-11-10'}, {...payload().latest_discoveries,total:17}, {...payload().latest_discoveries,repos:'2'}, {...payload().latest_discoveries,repos:-1}]) {
  assert.equal(parseLatest({...payload(),latest_discoveries:stats}).discoveries,null);
 }
 assert.equal(parseLatest({...payload(),entry_count:'388'}).entryCount,null);
});
function root(){
 const nodes=new Map();
 const get=selector=>{if(!nodes.has(selector))nodes.set(selector,{textContent:'fallback',href:'https://leeeway.github.io/daily-trend-radar/',setAttribute(k,v){this[k]=v;}});return nodes.get(selector);};
 return {dataset:{radarLang:'zh'},querySelector:get,querySelectorAll:selector=>[get(selector)],nodes};
}
test('client updates native counters as text and keeps generic links on fetch failure',async()=>{
 const {refreshHub}=await modulePromise;
 const r=root();await refreshHub(r,async()=>({ok:true,json:async()=>payload()}));
 assert.equal(r.dataset.radarState,'ready');assert.equal(r.querySelector('[data-radar-new-count]').textContent,'16 条新发现');
 assert.equal(r.querySelector('[data-radar-library-count]').textContent,'在 388 条资讯中继续阅读');
 const failed=root();await refreshHub(failed,async()=>{throw new Error('network unavailable')});
 assert.equal(failed.dataset.radarState,'fallback');assert.equal(failed.querySelector('[data-radar-latest]').href,'https://leeeway.github.io/daily-trend-radar/');
 assert.equal(failed.querySelector('[data-radar-new-count]').textContent,'fallback');
 const partial=root();partial.dataset.radarLang='en';await refreshHub(partial,async()=>({ok:true,json:async()=>({...payload(),latest_discoveries:null})}));
 assert.equal(partial.dataset.radarState,'partial');assert.equal(partial.querySelector('[data-radar-status]').textContent,'LATEST ARCHIVE');
});
