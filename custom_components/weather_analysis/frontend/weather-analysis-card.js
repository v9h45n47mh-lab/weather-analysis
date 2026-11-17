import {UI_CSS, UI_VERSION, navigation, section, row, button, iconButton, selectField,
  field, notice, versionInfo, bindUI, escapeHtml as esc, accountTile, accountTiles,
  statisticsTable, filterButton, multiSelect, dateNavigation} from './family-ui/1.7.1/family-ui.js';

const VERSION = '1.1.0';
const PERIODS = [['day','Tag'],['week','Woche'],['month','Monat'],['year','Jahr'],['custom','Zeitraum']];
const num = (value, digits=1) => value == null || !Number.isFinite(value) ? '—' : value.toLocaleString('de-DE',{minimumFractionDigits:digits, maximumFractionDigits:digits});
const delta = (value,unit='°C') => value == null ? '—' : `${value>0?'+':''}${num(value)} ${unit}`;
const dateKey = (date, timezone) => {
  const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date).map(p=>[p.type,p.value]));
  return `${p.year}-${p.month}-${p.day}`;
};
export function shiftDay(key, days) { const d=new Date(key+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10); }
export function periodDates(period, timezone, now=new Date()) {
  const today=dateKey(now,timezone);
  if(period==='yesterday')return [shiftDay(today,-1),shiftDay(today,-1)];
  if(period==='week'){const dow=new Date(today+'T12:00:00Z').getUTCDay();return [shiftDay(today,-((dow+6)%7)),today];}
  if(period==='month')return [today.slice(0,7)+'-01',today];
  if(period==='year')return [today.slice(0,4)+'-01-01',today];
  return [today,today];
}

const CSS = `
.wa-title{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:12px 0;overflow-wrap:anywhere}
.wa-periods{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px}
.wa-date-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.wa-date-fields .field{min-width:0}.wa-date-fields input{min-width:0;max-width:100%}
.wa-range{margin:12px 0}.wa-chart{width:100%;display:block;height:auto;overflow:visible}
.wa-chart text{font:inherit;font-size:12px;fill:var(--secondary-text-color,#727272)}
.wa-chart .wa-grid{stroke:var(--divider-color,#e0e0e0);stroke-width:1;stroke-dasharray:3 4}
.wa-chart .wa-line{fill:none;stroke:var(--primary-color,#03a9f4);stroke-width:2.5;stroke-linejoin:round}
.wa-chart .wa-band{fill:var(--primary-color,#03a9f4);opacity:.13}
.wa-chart .wa-point{fill:var(--primary-color,#03a9f4);stroke:var(--ha-card-background,var(--card-background-color,#fff));stroke-width:2}
.wa-chart .wa-hit{fill:transparent;stroke:none;cursor:crosshair}.wa-chart .wa-hit:focus{fill:var(--primary-color,#03a9f4);opacity:.3;outline:none}
.wa-inspector{min-height:36px;padding:4px 0;overflow-wrap:anywhere}
.wa-legend{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0}.wa-swatch{display:inline-block;width:16px;height:3px;background:var(--primary-color,#03a9f4);vertical-align:middle;margin-right:6px}.wa-swatch.band{height:10px;opacity:.25}
.wa-current{margin-bottom:12px}.wa-quality{margin-top:12px}.wa-setting-actions{margin-top:16px}
`;

class WeatherAnalysisCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this.page='temperature';this._sensors=[];this._windSensors=[];this._illuminanceSensors=[];this._active={};this._settings={};this._request=0;this._busy=false;}
  static getConfigElement(){return document.createElement('weather-analysis-card-editor');}
  static getStubConfig(){return {card_id:crypto.randomUUID(),title:'Temperaturanalyse',period:'day'};}
  setConfig(config){
    if(!config || typeof config!=='object')throw new Error('Bitte eine Kartenkonfiguration angeben.');
    this.config={title:'Temperaturanalyse',period:'day',...config};
    this.config.card_id ||= this.config.entity || 'default';
    this.period=PERIODS.some(([id])=>id===this.config.period)?this.config.period:'day';
    this._day=this.config.period==='yesterday'?shiftDay(dateKey(new Date(),this._hass?.config?.time_zone||'Europe/Berlin'),-1):null;
    this._ready=false;this._data=null;this._settings={};this._active={};this._request++;
    if(this._hass)this._initialize();else this.render();
  }
  set hass(hass){
    this._hass=hass;
    if(!this.config)return;
    if(!this._ready){this._initialize();return;}
    const entity=this.activeEntity;
    const state=hass.states[entity];const signature=state?.state+'|'+state?.last_updated;
    if(this._signature!==signature){this._signature=signature;this._schedule();}
  }
  get settings(){
    const s={...this.config,...this._settings};
    s.entities ||= s.entity?[s.entity]:[];
    if(s.title==='Wetteranalyse'||s.title==='Weather Analysis')s.title='Temperaturanalyse';
    return s;
  }
  get view(){return ['wind','illuminance'].includes(this.page)?this.page:'temperature';}
  get unit(){return {temperature:'°C',wind:'km/h',illuminance:'lx'}[this.view];}
  get activeEntity(){return (this._active[this.view]??(this.view==='wind'?this.settings.wind_entity:this.view==='illuminance'?this.settings.illuminance_entity:this.settings.entity))||'';}
  get availableSensors(){return this.view==='wind'?this._windSensors:this.view==='illuminance'?this._illuminanceSensors:this._sensors;}
  connectedCallback(){
    this._unbind ||= bindUI(this.shadowRoot,event=>this._action(event));
    this._change ||= event=>this._onChange(event);
    this.shadowRoot.addEventListener('change',this._change);
    this._inspect ||= event=>{const hit=event.target.closest?.('[data-point]');if(hit)this._inspectPoint(Number(hit.dataset.point));};
    this.shadowRoot.addEventListener('pointerover',this._inspect);this.shadowRoot.addEventListener('focusin',this._inspect);
    this._timer ||= setInterval(()=>{if(this.page!=='settings')this._fetch();},60000);
    if(this._ready)this._fetch();else if(this._hass&&this.config)this._initialize();
  }
  disconnectedCallback(){
    this._unbind?.();this._unbind=null;clearInterval(this._timer);this._timer=null;clearTimeout(this._debounce);
    this.shadowRoot.removeEventListener('change',this._change);this.shadowRoot.removeEventListener('pointerover',this._inspect);this.shadowRoot.removeEventListener('focusin',this._inspect);
  }
  getCardSize(){return 12;}
  getGridOptions(){return {columns:12,rows:'auto',min_columns:6};}
  _schedule(){clearTimeout(this._debounce);this._debounce=setTimeout(()=>{if(this.isConnected&&this.page!=='settings')this._fetch();},1200);}
  async _initialize(){
    if(this._initializing||!this._hass||!this.config)return;
    this._initializing=true;
    try {
      const result=await this._hass.callWS({type:'weather_analysis/sensors',card_id:this.config.card_id});
      this._sensors=result.sensors;this._windSensors=result.wind_sensors||[];this._illuminanceSensors=result.illuminance_sensors||[];this._settings=result.settings||{};this._admin=result.admin;this.timezone=result.timezone;
      this._ready=true;this._error=null;this.render();await this._fetch();
    }catch(error){this._error='Temperaturanalyse ist noch nicht eingerichtet oder konnte nicht geladen werden. Bitte die Integration einmal unter Geräte & Dienste hinzufügen. '+(error.message||'');this.render();}
    finally{this._initializing=false;}
  }
  _dates(){if(this.period==='day'){const day=this._day||dateKey(new Date(),this.timezone||'Europe/Berlin');return [day,day];}return this.period==='custom'?(this._custom||periodDates('today',this.timezone||'Europe/Berlin')):periodDates(this.period,this.timezone||'Europe/Berlin');}
  async _fetch(){
    if(!this._ready||!this.activeEntity||!this._hass)return;
    const request=++this._request;const [start_date,end_date]=this._dates();const entity=this.activeEntity;
    this._busy=true;
    if(!this._data)this.render();
    try {
      const data=await this._hass.callWS({type:'weather_analysis/analyse',entity_id:entity,
        start_date,end_date});
      if(request!==this._request)return;
      this._data=data;this._error=null;
    }catch(error){if(request===this._request)this._error=error.message||String(error);}
    finally{if(request===this._request){this._busy=false;if(this.page!=='settings')this.render();}}
  }
  async _action({action,data}){
    if(action==='navigate'){
      const oldView=this.view;this.page=data.page;this._error=null;
      if(this.view!==oldView||!['settings','help'].includes(this.page)){this._request++;this._data=null;this._busy=false;}
      this.render();if(!['settings','help'].includes(this.page))await this._fetch();return;
    }
    if(action==='period'){this._request++;this._busy=false;this.period=data.period;this._data=null;this._error=null;this.render();if(this.period!=='custom')this._fetch();return;}
    if(action==='reload'){await this._initialize();return;}
    if(['previous-day','next-day','today'].includes(action)){
      const today=dateKey(new Date(),this.timezone||'Europe/Berlin');
      const target=action==='today'?today:shiftDay(this._dates()[0],action==='previous-day'?-1:1);
      if(target>today)return;this._day=target;this._request++;this._data=null;this._busy=false;this._error=null;this.render();await this._fetch();return;
    }
    if(action==='import-history'&&this._admin&&!this._importing){
      this._importing=true;const slot=this.shadowRoot.getElementById('wa-settings-error');const button=this.shadowRoot.querySelector('[data-action="import-history"]');if(button)button.disabled=true;
      try{const result=await this._hass.callWS({type:'weather_analysis/import_history',card_id:this.config.card_id});if(slot)slot.innerHTML=notice(result.failed.length?'Historie teilweise übernommen. Details stehen im HA-Protokoll.':`Historie für ${result.count} Sensoren übernommen.`,{error:result.failed.length>0});}
      catch(error){if(slot)slot.innerHTML=notice(error.message||String(error),{error:true});}
      finally{this._importing=false;if(button)button.disabled=false;}return;
    }
    if(action==='custom-apply'){
      const start=this.shadowRoot.getElementById('wa-from').value,end=this.shadowRoot.getElementById('wa-to').value;
      if(!start||!end||start>end){this._error='Bitte einen gültigen Zeitraum auswählen.';this.render();return;}
      this._custom=[start,end];this._data=null;this._fetch();return;
    }
    if(action==='cancel-settings'){this.page='temperature';this._request++;this._busy=false;this._data=null;this._error=null;this.render();await this._fetch();return;}
    if(action==='save-settings'&&this._admin){
      const get=id=>this.shadowRoot.getElementById(id).value;
      const entities=[...this.shadowRoot.querySelectorAll('#wa-sensors input[type="checkbox"]:checked')].map(x=>x.value);
      const settings={entities,entity:entities.includes(this.settings.entity)?this.settings.entity:entities[0]||'',wind_entity:get('wa-wind-sensor'),illuminance_entity:get('wa-illuminance-sensor'),title:get('wa-title')};
      try {
        const previous=this._settings;
        let saved;try{saved=await this._persistSettings(settings);}catch(error){this._settings=previous;throw error;}
        this._settings=saved;this._active={};this._request++;this._data=null;this._error=null;this.page='temperature';await this._fetch();
      }catch(error){this._error=error.message||String(error);const slot=this.shadowRoot.getElementById('wa-settings-error');if(slot)slot.innerHTML=notice(this._error,{error:true});}
    }
  }
  _onChange(event){
    if(event.target.id==='wa-active-sensor'){this._active.temperature=event.target.value;this._request++;this._data=null;this._busy=false;this._error=null;this.render();this._fetch();return;}
    if(event.target.id==='wa-from'||event.target.id==='wa-to')this._custom=[this.shadowRoot.getElementById('wa-from').value,this.shadowRoot.getElementById('wa-to').value];
  }
  async _persistSettings(settings){
    const cardId=this.config.card_id;
    const revision=(this._saveRevision||0)+1;this._saveRevision=revision;
    this._settings=settings;
    this._saveQueue=(this._saveQueue||Promise.resolve()).catch(()=>{}).then(()=>this._hass.callWS({type:'weather_analysis/save_card',card_id:cardId,...settings}));
    const saved=await this._saveQueue;
    if(revision===this._saveRevision)this._settings=saved;
    return saved;
  }
  _sensorPicker(){
    if(this.view!=='temperature'||this.settings.entities.length<2)return '';
    return selectField({id:'wa-active-sensor',label:'Thermometer',value:this.activeEntity,
      options:this._sensors.filter(s=>this.settings.entities.includes(s.entity_id)).map(s=>({value:s.entity_id,label:s.name}))});
  }
  _formatTime(seconds,full=false){return seconds==null?'Uhrzeit nicht gespeichert':new Intl.DateTimeFormat('de-DE',{timeZone:this.timezone,day:full?'2-digit':undefined,month:full?'2-digit':undefined,year:full?'numeric':undefined,hour:'2-digit',minute:'2-digit'}).format(new Date(seconds*1000));}
  _extremeDescription(summary,kind){return summary[kind+'_at']!=null?this._formatTime(summary[kind+'_at'],this.period!=='day'):'Uhrzeit nicht gespeichert';}
  _tile(id,label,value,unit='',description='',state='neutral'){return accountTile({id:'wa-'+id,label,value,unit,description,state});}
  _periodControls(){
    const [start,end]=this._dates();
    return `<div class="wa-periods" role="group" aria-label="Auswertungszeitraum">${PERIODS.map(([id,label])=>filterButton({label,action:'period',selected:this.period===id,data:{period:id}})).join('')}</div>
      ${this.period==='day'?dateNavigation({label:this._dateLabel(start),previousLabel:'Vorheriger Tag',nextLabel:'Nächster Tag',previousAction:'previous-day',nextAction:'next-day',nextDisabled:start>=dateKey(new Date(),this.timezone||'Europe/Berlin')}):''}
      ${this.period==='custom'?`<div class="wa-date-fields">${field({id:'wa-from',label:'Von',type:'date',value:start})}${field({id:'wa-to',label:'Bis',type:'date',value:end,min:start})}</div><div class="toolbar">${button({label:'Anzeigen',action:'custom-apply',variant:'primary'})}</div>`:''}
      <p class="hint wa-range">${esc(this._dateLabel(start))}${start!==end?' – '+esc(this._dateLabel(end)):''}${this._data?.partial?' · bisher':''}</p>`;
  }
  _dateLabel(key){return new Date(key+'T12:00:00Z').toLocaleDateString('de-DE',{timeZone:'UTC',day:'2-digit',month:'2-digit',year:'numeric'});}
  _chart(){
    const d=this._data,points=d.chart;
    if(!points.length)return notice('Für diesen Zeitraum sind noch keine Messwerte vorhanden.');
    const W=640,H=240,L=48,R=18,T=18,B=34;
    let low=Math.min(...points.map(p=>p.min??p.mean)),high=Math.max(...points.map(p=>p.max??p.mean));
    const pad=Math.max(1,(high-low)*.15);low-=pad;high+=pad;
    const x=t=>L+(t-d.start)/Math.max(1,d.end-d.start)*(W-L-R), y=v=>T+(high-v)/(high-low)*(H-T-B);
    const groups=[];let group=[];const interval=d.chart_daily?86400:3600;
    for(const p of points){if(group.length&&p.start-group.at(-1).start>interval*1.6){groups.push(group);group=[];}group.push(p);}if(group.length)groups.push(group);
    const paths=groups.map(g=>{
      const line=g.map((p,i)=>`${i?'L':'M'}${x(p.start).toFixed(2)},${y(p.mean).toFixed(2)}`).join(' ');
      const band=[...g.map(p=>[x(p.start),y(p.max??p.mean)]),...g.toReversed().map(p=>[x(p.start),y(p.min??p.mean)])].map(([a,b],i)=>`${i?'L':'M'}${a.toFixed(2)},${b.toFixed(2)}`).join(' ')+' Z';
      return `<path class="wa-band" d="${band}"/><path class="wa-line" d="${line}"/>`;
    }).join('');
    return `<svg class="wa-chart" viewBox="0 0 ${W} ${H}" role="group" aria-label="${this.view==='wind'?'Windverlauf in Kilometer pro Stunde':this.view==='illuminance'?'Helligkeitsverlauf in Lux':'Temperaturverlauf in Grad Celsius'}"><title>${this.view==='wind'?'Windverlauf':this.view==='illuminance'?'Helligkeitsverlauf':'Temperaturverlauf'}</title><desc>Linie: Durchschnitt. Band: Minimum bis Maximum. Messpunkte lassen sich mit Tab auswählen.</desc>
      ${Array.from({length:5},(_,i)=>{const value=low+(high-low)*i/4;return `<path class="wa-grid" d="M${L},${y(value)} H${W-R}"/><text text-anchor="end" x="${L-8}" y="${y(value)+4}">${num(value,0)}${this.view==='temperature'?'°':''}</text>`;}).join('')}
      ${paths}${points.map((p,i)=>`<circle class="wa-point" cx="${x(p.start)}" cy="${y(p.mean)}" r="${points.length===1?4:2}"/><circle class="wa-hit" data-point="${i}" tabindex="0" role="img" aria-label="${esc(this._pointText(p))}" cx="${x(p.start)}" cy="${y(p.mean)}" r="9"><title>${esc(this._pointText(p))}</title></circle>`).join('')}
      ${[0,.5,1].map((fraction,i)=>`<text x="${L+fraction*(W-L-R)}" y="${H-7}" text-anchor="${i===0?'start':i===2?'end':'middle'}">${esc(new Intl.DateTimeFormat('de-DE',{timeZone:this.timezone,...(d.chart_daily?{day:'2-digit',month:'2-digit'}:{hour:'2-digit',minute:'2-digit'})}).format(new Date((d.start+fraction*(d.end-d.start))*1000)))}</text>`).join('')}</svg>
      <div class="wa-legend hint"><span><i class="wa-swatch"></i>Durchschnitt</span><span><i class="wa-swatch band"></i>Minimum / Maximum</span></div><p class="hint wa-inspector" id="wa-inspector" aria-live="polite">${esc(d.chart_daily?'Tageswerte · Messpunkt für Details auswählen':'Stundenwerte · Messpunkt für Details auswählen')}</p>`;
  }
  _pointText(p){return `${this._formatTime(p.start,true)} · Ø ${num(p.mean)} ${this.unit} · Min ${num(p.min)} ${this.unit} · Max ${num(p.max)} ${this.unit}`;}
  _inspectPoint(index){const point=this._data?.chart[index],slot=this.shadowRoot.getElementById('wa-inspector');if(point&&slot)slot.textContent=this._pointText(point);}
  _overview(){
    const d=this._data,s=d.summary;
    return `<div class="wa-current">${accountTiles({label:this.view==='wind'?'Aktueller Wind':this.view==='illuminance'?'Aktuelle Helligkeit':'Aktuelle Temperatur',content:
      this._tile('current','Aktuell',num(d.current),this.unit,d.current==null?'Sensor nicht verfügbar':`Messung ${this._formatTime(d.last_updated)}`,'active')+
      this._tile('trend','Veränderung in 1 Stunde',delta(d.trends.hour,this.unit),'',d.trends.hour==null?'Noch keine Vergleichsdaten':d.trends.hour>.2?'Steigend':d.trends.hour<-.2?'Fallend':'Nahezu konstant')})}</div>
      ${this._chart()}
      ${accountTiles({label:this.view==='wind'?'Windkennzahlen':this.view==='illuminance'?'Helligkeitskennzahlen':'Temperaturkennzahlen',content:
      this._tile('min','Minimum',num(s.min),this.unit,this._extremeDescription(s,'min'))+
      this._tile('max','Maximum',num(s.max),this.unit,this._extremeDescription(s,'max'))+
      this._tile('mean',d.partial?'Durchschnitt bisher':'Durchschnitt',(s.estimated?'≈ ':'')+num(s.mean),this.unit,'Zeitlich gewichtet')+
      this._tile('range',this.view==='temperature'?'Temperaturspanne':'Spanne',num(s.range),this.unit,'Maximum minus Minimum')})}
      ${section({id:'wa-trends',title:'Weitere Vergleiche',expanded:false,content:
        row({title:'Veränderung in 3 Stunden',trailing:esc(delta(d.trends.three_hours,this.unit))})+
        row({title:'Gestern zur gleichen Uhrzeit',trailing:esc(delta(d.trends.yesterday,this.unit))})})}`;
  }
  _statistics(){
    const d=this._data,s=d.summary,wind=this.view==='wind',temperature=this.view==='temperature',known=s.exact_seconds>0;
    const threshold=(id,label,key)=>row({title:label,description:known?`Erfasst für ${num(s.duration_coverage*100,0)} % des Zeitraums`:'Keine Detailhistorie für diesen Zeitraum',trailing:esc(known?num(s[key])+' h':'—')});
    return section({id:'wa-statistics',title:'Weitere Kennzahlen',expanded:false,content:
      (temperature?section({id:'wa-thresholds',title:'Grenzwertdauern',content:threshold('frost','Unter 0 °C','frost_hours')+threshold('warm','Ab 25 °C','warm_hours')+threshold('hot','Ab 30 °C','hot_hours')})+
      section({id:'wa-days',title:'Besondere Tage',expanded:false,content:row({title:'Frosttage · Minimum unter 0 °C',trailing:String(s.frost_days)})+row({title:'Warme Tage · Maximum ab 25 °C',trailing:String(s.warm_days)})+row({title:'Heiße Tage · Maximum ab 30 °C',trailing:String(s.hot_days)})+notice('Gezählt werden Tage mit nachgewiesener Grenzwertüberschreitung. Fehlende Tage gelten nicht als frostfrei.')}):'')+
      section({id:'wa-compare',title:'Zeitraumvergleich',content:Object.entries(d.comparisons).map(([key,value])=>row({title:key==='year'?'Gleicher Zeitraum im Vorjahr':'Vorheriger gleich langer Zeitraum',description:value.mean==null?'Keine Vergleichsdaten':`Ø ${num(value.mean)} ${this.unit} · Datenintervalle ${num(value.coverage*100,0)} %`,trailing:esc(delta(value.delta,this.unit))})).join('')})+
      section({id:'wa-records',title:'Rekorde seit Aufzeichnung',content:['min','max'].map(kind=>{const r=d.records[kind];return row({title:wind?(kind==='min'?'Niedrigster Windwert':'Höchster Windwert'):this.view==='illuminance'?(kind==='min'?'Niedrigster Helligkeitswert':'Höchster Helligkeitswert'):(kind==='min'?'Kältester Messwert':'Wärmster Messwert'),description:r?.at?this._formatTime(r.at,true):'Datum in älteren Langzeitstatistiken nicht gespeichert',trailing:esc(r?num(r.value)+' '+this.unit:'—')});}).join('')})+
      section({id:'wa-months',title:'Monatsübersicht im gewählten Zeitraum',expanded:false,content:this._monthlyTable(s.days)})+
      section({id:'wa-measurements',title:'Tageswerte',expanded:false,content:statisticsTable({label:'Tägliche Messwerte',columns:[{label:'Tag'},{label:'Min '+this.unit,align:'right'},{label:'Ø '+this.unit,align:'right'},{label:'Max '+this.unit,align:'right'}],rows:s.days.map(r=>[this._dateLabel(r.date),num(r.min),num(r.mean),num(r.max)])})})});
  }
  _monthlyTable(days){
    const months=new Map();for(const d of days){const key=d.date.slice(0,7);const m=months.get(key)||{seconds:0,sum:0,min:Infinity,max:-Infinity};m.seconds+=d.seconds;m.sum+=d.mean*d.seconds;m.min=Math.min(m.min,d.min);m.max=Math.max(m.max,d.max);months.set(key,m);}
    return statisticsTable({label:'Monatliche Messwerte',columns:[{label:'Monat'},{label:'Min '+this.unit,align:'right'},{label:'Ø '+this.unit,align:'right'},{label:'Max '+this.unit,align:'right'}],rows:[...months].map(([key,m])=>[key.slice(5)+'.'+key.slice(0,4),num(m.min),num(m.sum/m.seconds),num(m.max)])});
  }
  _settingsView(){
    const s=this.settings;
    return `${section({id:'wa-card-settings',title:'Karte einrichten',content:
      '<div id="wa-settings-error"></div>'+
      field({id:'wa-title',label:'Anzeigename',value:s.title,maxLength:100,disabled:!this._admin})+
      multiSelect({id:'wa-sensors',label:'Thermometer',values:s.entities,items:this._sensors.map(x=>({value:x.entity_id,label:x.name,description:x.entity_id})),disabled:!this._admin})+
      '<p class="hint">Ausgewählte Thermometer werden auch bei geschlossener Karte aufgezeichnet. In der Temperaturansicht kannst du direkt zwischen deinen Thermometern wechseln.</p>'+
      selectField({id:'wa-wind-sensor',label:'Windsensor',value:s.wind_entity||'',options:[{value:'',label:'Kein Windsensor ausgewählt'},...this._windSensors.map(x=>({value:x.entity_id,label:x.name}))],disabled:!this._admin})+
      selectField({id:'wa-illuminance-sensor',label:'Helligkeitssensor',value:s.illuminance_entity||'',options:[{value:'',label:'Kein Helligkeitssensor ausgewählt'},...this._illuminanceSensors.map(x=>({value:x.entity_id,label:x.name}))],disabled:!this._admin})})}
      ${section({id:'wa-history-settings',title:'Historie',content:'<p class="hint">Vorhandene Historie wird automatisch übernommen. Nach erneutem Import bleiben bereits gesicherte Werte erhalten. Geänderte Sensoren zuerst speichern.</p>'+(this._admin?button({label:'Historie übernehmen',action:'import-history',disabled:!this.settings.entities.length&&!this.settings.wind_entity&&!this.settings.illuminance_entity}):'')})}
      <div class="toolbar wa-setting-actions">${this._admin?button({label:'Speichern',action:'save-settings',variant:'primary'}):''}${button({label:'Zurück',action:'cancel-settings'})}</div>
      ${versionInfo({frontend:VERSION,backend:this._data?.version||VERSION,ui:UI_VERSION,label:'Temperaturanalyse'})}`;
  }
  _help(){return section({id:'wa-help',title:'So funktioniert die Temperaturanalyse',content:
    '<p>Temperatur, Wind und Helligkeit stammen direkt von deinen gewählten HA-Sensoren. Bereits bei der ersten Auswahl werden vorhandene Detailhistorie und Langzeitstatistik ausgewertet. Anschließend werden Stundenwerte und Extremwerte auch bei geschlossener Karte gespeichert.</p>'+
    row({title:'Sensoren auswählen',description:'Die Integration wird einmal eingerichtet. Thermometer, Windsensor und Helligkeitssensor wählst du ausschließlich in den Einstellungen der Karte. Mehrere Karten erhalten eigene Einstellungen über ihre Karten-ID.'})+
    row({title:'Datenqualität',description:'≈ kennzeichnet Mittelwerte aus verdichteten HA-Statistiken. Grenzwertdauern und genaue Extremzeiten stammen aus vorhandener Detailhistorie und eigener Aufzeichnung. Fehlende Detaildaten werden nicht erfunden.'})+
    row({title:'Messlücken',description:'Unavailable/unknown und bekannte HA-Ausfallzeiten bleiben Lücken. Vergleiche sind nur bei ähnlicher Datenabdeckung aussagekräftig.'})+
    row({title:'Wind',description:'Windgeschwindigkeit wird einheitlich in km/h angezeigt. Unterstützt werden auch m/s, mph, Knoten und ft/s. Der höchste Sensorwert ist keine separat gemessene Windböe.'})+
    row({title:'Zeitraum und Zeitzone',description:'Tag, Woche, Monat und Jahr reichen jeweils bis jetzt. Tagesgrenzen und Uhrzeiten folgen der HA-Zeitzone. Freie Zeiträume dürfen höchstens ein Jahr umfassen.'})});}
  render(){
    if(!this.config)return;
    const title=this.settings.title||'Temperaturanalyse';
    let body;
    if(this.page==='settings')body=this._settingsView();
    else if(this.page==='help')body=this._help();
    else body=this._sensorPicker()+
      (!this.activeEntity?notice('Bitte den Sensor in den Einstellungen der Karte auswählen.')+(this._admin?button({label:'Sensoren auswählen',action:'navigate',data:{page:'settings'}}):''):
      this._periodControls()+(this._data?this._overview()+this._statistics():notice(this._busy?'Vorhandene Historie und Messwerte werden geladen …':'Zeitraum auswählen und anzeigen.')));
    const quality=this._data&&!['settings','help'].includes(this.page)?notice(`Datenintervalle: ${num(this._data.summary.coverage*100,0)} %${this._data.summary.estimated?' · teilweise aus HA-Langzeitstatistik (Messabdeckung unbekannt)':''}. Detailabdeckung: ${num(this._data.summary.duration_coverage*100,0)} % des Zeitraums.`):'';
    const collapsed=new Map([...this.shadowRoot.querySelectorAll('[data-ui="collapse"]')].map(el=>[el.getAttribute('aria-controls'),el.getAttribute('aria-expanded')]));
    this.shadowRoot.innerHTML=`<style>${UI_CSS}${CSS}</style><ha-card>${navigation({label:'Temperaturanalyse',items:[{id:'temperature',label:'Temperatur'},{id:'wind',label:'Wind'},{id:'illuminance',label:'Helligkeit'}],active:this.page,settings:true,help:true})}<main><div class="wa-title"><div><h3>${esc(title)}</h3><small>${esc(this._data?.name||this.availableSensors.find(s=>s.entity_id===this.activeEntity)?.name||'Messwerte aus deinen Sensoren')}</small></div>${button({label:'Aktualisieren',action:'reload',compact:true,disabled:this._busy})}</div>${this._error&&this.page!=='settings'?notice(this._error,{error:true}):''}${body}<div class="wa-quality">${quality}</div></main></ha-card>`;
    for(const [id,expanded] of collapsed){const content=this.shadowRoot.getElementById(id);const control=[...this.shadowRoot.querySelectorAll('[data-ui="collapse"]')].find(el=>el.getAttribute('aria-controls')===id);if(content&&control){content.hidden=expanded==='false';control.setAttribute('aria-expanded',expanded);control.querySelector('.chevron')?.classList.toggle('expanded',expanded==='true');}}
  }
}

class WeatherAnalysisCardEditor extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});}
  setConfig(config){this.config={card_id:crypto.randomUUID(),period:'day',title:'Temperaturanalyse',...config};this.render();}
  set hass(hass){this._hass=hass;this.render();}
  render(){if(!this.config)return;const c=this.config;
    this.shadowRoot.innerHTML=`<style>${UI_CSS}</style>${field({id:'title',label:'Anzeigename',value:c.title})}${selectField({id:'period',label:'Startansicht',value:c.period,options:PERIODS.filter(([id])=>id!=='custom').map(([value,label])=>({value,label}))})}${field({id:'card_id',label:'Karten-ID',value:c.card_id,hint:'Für unabhängige Einstellungen eine eigene ID verwenden.'})}`;
    this.shadowRoot.onchange=event=>{const key=event.target.id;if(!['title','period','card_id'].includes(key))return;this.config={...this.config,[key]:event.target.value};this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));};
  }
}
if(!customElements.get('weather-analysis-card'))customElements.define('weather-analysis-card',WeatherAnalysisCard);
if(!customElements.get('weather-analysis-card-editor'))customElements.define('weather-analysis-card-editor',WeatherAnalysisCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==='weather-analysis-card'))window.customCards.push({type:'weather-analysis-card',name:'Temperaturanalyse',description:'Temperatur, Wind und Helligkeit mit vorhandener Historie und aufklappbaren Kennzahlen',icon:'mdi:thermometer',preview:true});
