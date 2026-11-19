import {test} from 'node:test';
import assert from 'node:assert/strict';
import {RadarController} from '../custom_components/weather_analysis/frontend/radar-controller.js';
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(){
  const calls=[],frames=[{time:100,reference:100,kind:'observation'},{time:400,reference:400,kind:'observation'},{time:700,reference:400,kind:'prediction'}];
  const card=new (RadarController(class {}))();let token=0;
  Object.assign(card,{_request:0,_ready:true,_busy:false,page:'radar',isConnected:true,_radarZoom:1,render(){},_paintRadar(){},_positionSignature(){return 'same';},
    _hass:{async callWS(message){calls.push({...message});if(message.type==='weather_analysis/radar')return {location:{name:'Test',position_available:true},radar:{status:'ok',context:'view-'+card._radarZoom,token:String(++token),frames:frames.map(f=>({...f})),latest:400,now:500}};return {image:'data:image/png;base64,'+message.kind+':'+message.index};}}});
  card._clearRadar();return {card,calls,frames};
}
test('refresh and reopening reuse loaded frames, basemap and legend',async()=>{
  const {card,calls}=fixture();await card._fetchRadar();await settle();
  assert.equal(calls.filter(c=>c.type.endsWith('/radar_image')).length,5);
  await card._showRadarFrame(0);const image=card._radarImage;
  await card._fetchRadar();await settle();
  assert.equal(card._radarIndex,0,'Selected history time stays selected');assert.equal(card._radarImage,image);
  assert.equal(calls.filter(c=>c.type.endsWith('/radar_image')).length,5,'No repeat transfers for the same data');
  card.page='wind';card._stopRadar();card.page='radar';await card._fetchRadar();await settle();
  assert.equal(calls.filter(c=>c.type.endsWith('/radar_image')).length,5);
});
test('new forecast runs reload forecasts while retaining historical measurements',async()=>{
  const {card,calls,frames}=fixture();await card._fetchRadar();await settle();calls.length=0;
  frames[2].reference=500;await card._fetchRadar();await settle();
  assert.deepEqual(calls.filter(c=>c.type.endsWith('/radar_image')).map(c=>[c.kind,c.index]),[['frame',2]]);
});
test('initially displayed frame precedes background history; active selection is foreground',async()=>{
  const {card,calls}=fixture();await card._fetchRadar();await settle();
  const images=calls.filter(c=>c.kind==='frame');assert.equal(images[0].index,1);assert.equal(images[0].background,false);
  assert(images.slice(1).every(c=>c.background===true));
  card._radarCache.clear();card._radarImages.clear();calls.length=0;await card._showRadarFrame(2);
  assert.equal(calls[0].background,false);
});
test('minute ticks and playback do not repeatedly rebuild the radar window',async()=>{
  const {card,calls}=fixture();await card._fetchRadar();await settle();calls.length=0;
  await card._refreshRadarIfDue(560);assert.equal(calls.length,0);
  card._radarPlaying=true;await card._refreshRadarIfDue(1100);assert.equal(calls.length,0);assert(card._radarPlaying);
  card._radarPlaying=false;await card._refreshRadarIfDue(801);await settle();assert.equal(calls.filter(c=>c.type==='weather_analysis/radar').length,1);
});
test('zoom and identity/location invalidation discard cached imagery',async()=>{
  const {card,calls}=fixture();await card._fetchRadar();await settle();calls.length=0;
  await card._radarAction('radar-zoom-in');await settle();assert.equal(calls.filter(c=>c.type.endsWith('/radar_image')).length,5);
  card._clearRadar();assert.equal(card._radarCache.size,0);assert.equal(card._radarBase,'');assert.equal(card._radarLegend,'');assert.equal(card._radar,null);
});
