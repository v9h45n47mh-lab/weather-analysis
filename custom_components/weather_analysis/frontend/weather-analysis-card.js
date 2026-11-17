import {UI_CSS, UI_VERSION, navigation, section, row, button, iconButton, selectField,
  field, notice, versionInfo, bindUI, escapeHtml as esc, accountTile, accountTiles,
  statisticsTable, filterButton, multiSelect, dateNavigation} from './family-ui/1.8.0/family-ui.js';

const VERSION = '1.3.0';
const PERIODS = [['day','Tag'],['week','Woche'],['month','Monat'],['year','Jahr'],['custom','Zeitraum']];
const num = (value, digits=1) => value == null || !Number.isFinite(value) ? '—' : value.toLocaleString('de-DE',{minimumFractionDigits:digits, maximumFractionDigits:digits});
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
.wa-title{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:8px 0}
.wa-header-controls{display:flex;align-items:center;justify-content:flex-end;gap:8px;min-width:0;max-width:100%;margin-left:auto}
.wa-sensor-select{flex:0 1 150px;width:150px;max-width:150px;min-width:80px}.wa-sensor-select .field{margin:0}.wa-sensor-select select{min-width:0;max-width:100%}
.wa-alias-list{display:grid;gap:8px}.wa-alias-list>*{min-width:0}
.wa-chart .wa-series-secondary .wa-line{stroke:var(--warning-color,#ff9800);stroke-dasharray:7 3}.wa-chart .wa-series-secondary .wa-band{fill:var(--warning-color,#ff9800);opacity:.08}
.wa-chart .wa-series-secondary .wa-point{fill:var(--warning-color,#ff9800)}.wa-swatch.secondary{background:var(--warning-color,#ff9800)}
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
.wa-chart .wa-average-line{fill:none;stroke:var(--primary-color,#03a9f4);stroke-width:1.5;stroke-dasharray:3 5;opacity:.75}.wa-chart .wa-average-label{fill:var(--primary-color,#03a9f4);stroke:var(--ha-card-background,var(--card-background-color,#fff));stroke-width:3;paint-order:stroke;stroke-linejoin:round}.wa-chart .wa-series-secondary .wa-average-line{stroke:var(--warning-color,#ff9800)}.wa-chart .wa-series-secondary .wa-average-label{fill:var(--warning-color,#ff9800)}
.wa-current{margin:8px 0 12px}.wa-quality{margin-top:12px}.wa-setting-actions{margin-top:16px}
`;

class WeatherAnalysisCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this.page='temperature';this._sensors=[];this._windSensors=[];this._illuminanceSensors=[];this._active={};this._settings={};this._request=0;this._busy=false;this._sectionStates=new Map();this._comparisonEnabled=false;}
  static getConfigElement(){return document.createElement('weather-analysis-card-editor');}
  static getStubConfig(){return {card_id:crypto.randomUUID(),title:'Weather Analysis',period:'day'};}
  setConfig(config){
    if(!config || typeof config!=='object')throw new Error('Bitte eine Kartenkonfiguration angeben.');
    const previousId=this.config?.card_id;
    this.config={title:'Weather Analysis',period:'day',...config};
    this.config.card_id ||= this.config.entity || 'default';
    if(previousId!==this.config.card_id){this._sectionStates.clear();this._renderedScope=null;this._comparisonEnabled=false;this._comparisonEntity='';}
    this._draftNames=null;this._settingsDraft=null;
    this.period=PERIODS.some(([id])=>id===this.config.period)?this.config.period:'day';
    this._day=this.config.period==='yesterday'?shiftDay(dateKey(new Date(),this._hass?.config?.time_zone||'Europe/Berlin'),-1):null;
    this._ready=false;this._data=null;this._comparisonData=null;this._comparisonError=null;this._settings={};this._active={};this._request++;
    if(this._hass)this._initialize();else this.render();
  }
  set hass(hass){
    this._hass=hass;
    if(!this.config)return;
    if(!this._ready){this._initialize();return;}
    const signature=[this.activeEntity,this.compareEntity].filter(Boolean).map(entity=>{const state=hass.states[entity];return entity+'|'+state?.state+'|'+state?.last_updated;}).join(';');
    if(this._signature!==signature){this._signature=signature;this._schedule();}
  }
  get settings(){
    const s={...this.config,...this._settings};
    s.entities ||= s.entity?[s.entity]:[];
    if(['Wetteranalyse','Temperaturanalyse'].includes(s.title))s.title='Weather Analysis';
    return s;
  }
  get view(){return ['wind','illuminance'].includes(this.page)?this.page:'temperature';}
  _num(value,digits=this.view==='illuminance'?0:1){return num(value,digits);}
  _delta(value,withUnit=true){return value==null?'—':`${value>0?'+':''}${this._num(value)}${withUnit?' '+this.unit:''}`;}
  get unit(){return {temperature:'°C',wind:'km/h',illuminance:'lx'}[this.view];}
  get activeEntity(){return (this._active[this.view]??(this.view==='wind'?this.settings.wind_entity:this.view==='illuminance'?this.settings.illuminance_entity:this.settings.entity))||'';}
  get compareEntity(){if(this.view!=='temperature'||!this._comparisonEnabled)return '';return this.settings.entities.includes(this._comparisonEntity)&&this._comparisonEntity!==this.activeEntity?this._comparisonEntity:this.settings.entities.find(e=>e!==this.activeEntity)||'';}
  _sensorName(entity,fallback=''){return this.settings.sensor_names?.[entity]||this._sensors.find(s=>s.entity_id===entity)?.name||this._windSensors.find(s=>s.entity_id===entity)?.name||this._illuminanceSensors.find(s=>s.entity_id===entity)?.name||fallback||entity;}
  get availableSensors(){return this.view==='wind'?this._windSensors:this.view==='illuminance'?this._illuminanceSensors:this._sensors;}
  connectedCallback(){
    this._unbind ||= bindUI(this.shadowRoot,event=>this._action(event));
    this._change ||= event=>this._onChange(event);
    this.shadowRoot.addEventListener('change',this._change);
    this._inspect ||= event=>{const hit=event.target.closest?.('[data-point]');if(hit)this._inspectPoint(Number(hit.dataset.point),Number(hit.dataset.series||0));};
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
    }catch(error){this._error='Weather Analysis ist noch nicht eingerichtet oder konnte nicht geladen werden. Bitte die Integration einmal unter Geräte & Dienste hinzufügen. '+(error.message||'');this.render();}
    finally{this._initializing=false;}
  }
  _dates(){if(this.period==='day'){const day=this._day||dateKey(new Date(),this.timezone||'Europe/Berlin');return [day,day];}return this.period==='custom'?(this._custom||periodDates('today',this.timezone||'Europe/Berlin')):periodDates(this.period,this.timezone||'Europe/Berlin');}
  async _fetch(){
    if(!this._ready||!this.activeEntity||!this._hass)return;
    const request=++this._request,[start_date,end_date]=this._dates();
    const entity=this.activeEntity,compare=this.compareEntity;
    this._busy=true;
    if(!this._data)this.render();
    try{
      const query=entity_id=>this._hass.callWS({type:'weather_analysis/analyse',entity_id,start_date,end_date});
      const responses=await Promise.allSettled([query(entity),...(compare?[query(compare)]:[])]);
      if(request!==this._request)return;
      if(responses[0].status==='rejected')throw responses[0].reason;
      this._data=responses[0].value;this._error=null;
      this._comparisonData=responses[1]?.status==='fulfilled'?responses[1].value:null;
      this._comparisonError=responses[1]?.status==='rejected'?'Vergleichssensor: '+(responses[1].reason.message||String(responses[1].reason)):null;
    }catch(error){if(request===this._request){this._error=error.message||String(error);this._comparisonData=null;}}
    finally{if(request===this._request){this._busy=false;if(this.page!=='settings')this.render();}}
  }
  async _action({action,data,value}){
    if(action==='choose-thermometers'){this._refreshAliasFields(value);return;}
    if(action==='compare-add'){if(this.settings.entities.length<2)return;this._comparisonEnabled=true;this._comparisonEntity=this.settings.entities.find(e=>e!==this.activeEntity);this._comparisonData=null;this._data=null;this.render();await this._fetch();return;}
    if(action==='compare-remove'){this._comparisonEnabled=false;this._comparisonEntity='';this._comparisonData=null;this._comparisonError=null;this._request++;this._busy=false;this.render();await this._fetch();return;}
    if(action==='navigate'){
      const oldView=this.view;if(data.page==='settings'&&this.page!=='settings'){this._draftNames={...this.settings.sensor_names};this._settingsDraft=null;}this.page=data.page;this._error=null;
      if(this.view!==oldView||!['settings','help'].includes(this.page)){this._request++;this._data=null;this._busy=false;}
      this.render();if(!['settings','help'].includes(this.page))await this._fetch();return;
    }
    if(action==='period'){this._request++;this._busy=false;this.period=data.period;this._data=null;this._error=null;this.render();if(this.period!=='custom')this._fetch();return;}
    if(action==='reload'){
      if(this.page==='settings'){
        this._rememberAliasDraft();
        this._settingsDraft={...this.settings,entities:[...this.shadowRoot.querySelectorAll('#wa-sensors input[type="checkbox"]:checked')].map(x=>x.value),sensor_names:{...this._draftNames},wind_entity:this.shadowRoot.getElementById('wa-wind-sensor').value,illuminance_entity:this.shadowRoot.getElementById('wa-illuminance-sensor').value};
      }
      this._refreshing=true;this.render();
      try{await this._initialize();}finally{this._refreshing=false;this.render();}return;
    }
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
    if(action==='cancel-settings'){this._settingsDraft=null;this.page='temperature';this._request++;this._busy=false;this._data=null;this._error=null;this.render();await this._fetch();return;}
    if(action==='save-settings'&&this._admin){
      const get=id=>this.shadowRoot.getElementById(id).value;
      const entities=[...this.shadowRoot.querySelectorAll('#wa-sensors input[type="checkbox"]:checked')].map(x=>x.value);
      const sensor_names=Object.fromEntries([...this.shadowRoot.querySelectorAll('[data-alias-entity]')].map(el=>[el.dataset.aliasEntity,el.querySelector('input').value.trim()]).filter(([entity,name])=>entities.includes(entity)&&name));
      const settings={entities,sensor_names,entity:entities.includes(this.settings.entity)?this.settings.entity:entities[0]||'',wind_entity:get('wa-wind-sensor'),illuminance_entity:get('wa-illuminance-sensor'),title:this.settings.title||'Weather Analysis'};
      try {
        const previous=this._settings;
        let saved;try{saved=await this._persistSettings(settings);}catch(error){this._settings=previous;throw error;}
        this._settings=saved;this._draftNames=null;this._settingsDraft=null;this._active={};if(saved.entities.length<2)this._comparisonEnabled=false;this._request++;this._data=null;this._error=null;this.page='temperature';await this._fetch();
      }catch(error){this._error=error.message||String(error);const slot=this.shadowRoot.getElementById('wa-settings-error');if(slot)slot.innerHTML=notice(this._error,{error:true});}
    }
  }
  _onChange(event){
    if(event.target.id==='wa-compare-sensor'){this._comparisonEntity=event.target.value;this._comparisonData=null;this._request++;this._busy=false;this.render();this._fetch();return;}
    if(event.target.id==='wa-active-sensor'){const previous=this.activeEntity;this._active.temperature=event.target.value;if(this._comparisonEntity===event.target.value)this._comparisonEntity=previous;this._comparisonData=null;this._request++;this._data=null;this._busy=false;this._error=null;this.render();this._fetch();return;}
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
    const entities=this.settings.entities;
    const options=entities.map(entity=>({value:entity,label:this._sensorName(entity)}));
    const primary=selectField({id:'wa-active-sensor',label:'Thermometer',hideLabel:true,value:this.activeEntity,
      options:options.length?options:[{value:'',label:'In Einstellungen auswählen'}],disabled:!options.length});
    const compare=this._comparisonEnabled&&this.compareEntity;
    return `<div class="wa-header-controls"><div class="wa-sensor-select">${primary}</div>${compare?
      `<div class="wa-sensor-select">${selectField({id:'wa-compare-sensor',label:'Vergleichssensor',hideLabel:true,value:this.compareEntity,options:options.filter(o=>o.value!==this.activeEntity)})}</div>${iconButton({icon:'close',label:'Vergleich entfernen',action:'compare-remove'})}`:
      iconButton({icon:'add',label:'Zweiten Sensor vergleichen',action:'compare-add',disabled:entities.length<2})}</div>`;
  }
  _rememberAliasDraft(){
    this._draftNames||={...this.settings.sensor_names};
    for(const el of this.shadowRoot.querySelectorAll('[data-alias-entity]'))this._draftNames[el.dataset.aliasEntity]=el.querySelector('input').value;
  }
  _aliasFields(entities){
    const names=this._draftNames||this.settings.sensor_names||{};
    return entities.length?entities.map((entity,index)=>`<div data-alias-entity="${esc(entity)}">${field({id:'wa-alias-'+index,label:this._sensors.find(s=>s.entity_id===entity)?.name||entity,value:names[entity]||'',maxLength:100,hint:entity+' · leer = ursprünglicher Name',disabled:!this._admin})}</div>`).join(''):notice('Zuerst relevante Thermometer auswählen.');
  }
  _refreshAliasFields(entities){
    this._rememberAliasDraft();
    const slot=this.shadowRoot.getElementById('wa-alias-fields');
    if(slot)slot.innerHTML=this._aliasFields(entities);
  }
  _rememberSections(){
    if(!this._renderedScope)return;
    for(const control of this.shadowRoot.querySelectorAll('[data-ui="collapse"]'))this._sectionStates.set(this._renderedScope+'|'+control.getAttribute('aria-controls'),control.getAttribute('aria-expanded'));
  }
  _restoreSections(){
    for(const control of this.shadowRoot.querySelectorAll('[data-ui="collapse"]')){
      const id=control.getAttribute('aria-controls'),expanded=this._sectionStates.get(this._renderedScope+'|'+id);
      if(expanded===undefined)continue;
      const content=this.shadowRoot.getElementById(id);
      if(content){content.hidden=expanded==='false';control.setAttribute('aria-expanded',expanded);control.querySelector('.chevron')?.classList.toggle('expanded',expanded==='true');}
    }
  }
  _formatTime(seconds,full=false){return seconds==null?'Uhrzeit nicht gespeichert':new Intl.DateTimeFormat('de-DE',{timeZone:this.timezone,day:full?'2-digit':undefined,month:full?'2-digit':undefined,year:full?'numeric':undefined,hour:'2-digit',minute:'2-digit'}).format(new Date(seconds*1000));}
  _extremeDescription(summary,kind){return summary[kind+'_at']!=null?this._formatTime(summary[kind+'_at'],this.period!=='day'):'Uhrzeit nicht gespeichert';}
  _periodControls(){
    const [start,end]=this._dates();
    return `<div class="wa-periods" role="group" aria-label="Auswertungszeitraum">${PERIODS.map(([id,label])=>filterButton({label,action:'period',selected:this.period===id,data:{period:id}})).join('')}</div>
      ${this.period==='day'?dateNavigation({label:this._dateLabel(start),previousLabel:'Vorheriger Tag',nextLabel:'Nächster Tag',previousAction:'previous-day',nextAction:'next-day',nextDisabled:start>=dateKey(new Date(),this.timezone||'Europe/Berlin')}):''}
      ${this.period==='custom'?`<div class="wa-date-fields">${field({id:'wa-from',label:'Von',type:'date',value:start})}${field({id:'wa-to',label:'Bis',type:'date',value:end,min:start})}</div><div class="toolbar">${button({label:'Anzeigen',action:'custom-apply',variant:'primary'})}</div>`:''}
      <p class="hint wa-range">${esc(this._dateLabel(start))}${start!==end?' – '+esc(this._dateLabel(end)):''}${this._data?.partial?' · bisher':''}</p>`;
  }
  _dateLabel(key){return new Date(key+'T12:00:00Z').toLocaleDateString('de-DE',{timeZone:'UTC',day:'2-digit',month:'2-digit',year:'numeric'});}
  _chartSeries(){
    const series=[{data:this._data,entity:this.activeEntity}];
    if(this.compareEntity&&this._comparisonData?.entity_id===this.compareEntity)series.push({data:this._comparisonData,entity:this.compareEntity});
    return series;
  }
  _chart(){
    const d=this._data,series=this._chartSeries(),points=series.flatMap(s=>s.data.chart);
    if(!points.length)return notice('Für diesen Zeitraum sind noch keine Messwerte vorhanden.');
    const W=640,H=240,L=48,R=18,T=18,B=34;
    let low=Math.min(...points.map(p=>p.min??p.mean),...series.map(s=>s.data.summary.mean).filter(Number.isFinite)),high=Math.max(...points.map(p=>p.max??p.mean),...series.map(s=>s.data.summary.mean).filter(Number.isFinite));
    const pad=Math.max(1,(high-low)*.15);low-=pad;high+=pad;
    const x=t=>L+(t-d.start)/Math.max(1,d.end-d.start)*(W-L-R),y=v=>T+(high-v)/(high-low)*(H-T-B);
    const plotted=series.map((series,seriesIndex)=>{
      const groups=[];let group=[];const interval=series.data.chart_daily?86400:3600;
      for(const point of series.data.chart){if(group.length&&point.start-group.at(-1).start>interval*1.6){groups.push(group);group=[];}group.push(point);}if(group.length)groups.push(group);
      const paths=groups.map(g=>{
        const line=g.map((p,i)=>`${i?'L':'M'}${x(p.start).toFixed(2)},${y(p.mean).toFixed(2)}`).join(' ');
        const band=[...g.map(p=>[x(p.start),y(p.max??p.mean)]),...g.toReversed().map(p=>[x(p.start),y(p.min??p.mean)])].map(([a,b],i)=>`${i?'L':'M'}${a.toFixed(2)},${b.toFixed(2)}`).join(' ')+' Z';
        return `<path class="wa-band" d="${band}"/><path class="wa-line" d="${line}"/>`;
      }).join('');
      return `<g class="wa-series ${seriesIndex?'wa-series-secondary':'wa-series-primary'}" data-series-entity="${esc(series.entity)}">${paths}${series.data.chart.map((p,i)=>`<circle class="wa-point" cx="${x(p.start)}" cy="${y(p.mean)}" r="${series.data.chart.length===1?4:2}"/><circle class="wa-hit" data-series="${seriesIndex}" data-point="${i}" tabindex="0" role="img" aria-label="${esc(this._pointText(p,series.entity))}" cx="${x(p.start)}" cy="${y(p.mean)}" r="9"><title>${esc(this._pointText(p,series.entity))}</title></circle>`).join('')}</g>`;
    }).join('');
    let previousMeanLabel=null;
    const averages=series.map((entry,index)=>{
      const mean=entry.data.summary.mean;if(!Number.isFinite(mean))return '';
      const at=y(mean);let labelY=Math.max(T+12,Math.min(H-B-4,at-6));
      if(previousMeanLabel!==null&&Math.abs(labelY-previousMeanLabel)<16)labelY=Math.min(H-B-4,previousMeanLabel+16);
      previousMeanLabel=labelY;
      return `<g class="${index?'wa-series-secondary':'wa-series-primary'}"><path class="wa-average-line" d="M${L},${at} H${W-R}"/><text class="wa-average-label" x="${W-R-4}" y="${labelY}" text-anchor="end"><title>Durchschnitt im gewählten Zeitraum · ${esc(this._sensorName(entry.entity))}</title>Ø ${esc(this._num(mean))} ${esc(this.unit)}</text></g>`;
    }).join('');
    return `<svg class="wa-chart" viewBox="0 0 ${W} ${H}" role="group" aria-label="${this.view==='wind'?'Windverlauf in Kilometer pro Stunde':this.view==='illuminance'?'Helligkeitsverlauf in Lux':'Temperaturverlauf in Grad Celsius'}"><title>${this.view==='wind'?'Windverlauf':this.view==='illuminance'?'Helligkeitsverlauf':'Temperaturverlauf'}</title><desc>${series.length>1?'Zwei Sensoren mit gemeinsamer Temperaturskala. Die zweite Linie ist zusätzlich gestrichelt.':'Linie: Durchschnitt. Band: Minimum bis Maximum.'} Messpunkte lassen sich mit Tab auswählen.</desc>
      ${Array.from({length:5},(_,i)=>{const value=low+(high-low)*i/4;return `<path class="wa-grid" d="M${L},${y(value)} H${W-R}"/><text text-anchor="end" x="${L-8}" y="${y(value)+4}">${this._num(value,0)}${this.view==='temperature'?'°':''}</text>`;}).join('')}
      ${plotted}${averages}
      ${[0,.5,1].map((fraction,i)=>`<text x="${L+fraction*(W-L-R)}" y="${H-7}" text-anchor="${i===0?'start':i===2?'end':'middle'}">${esc(new Intl.DateTimeFormat('de-DE',{timeZone:this.timezone,...(d.chart_daily?{day:'2-digit',month:'2-digit'}:{hour:'2-digit',minute:'2-digit'})}).format(new Date((d.start+fraction*(d.end-d.start))*1000)))}</text>`).join('')}</svg>
      <div class="wa-legend hint">${series.length>1?series.map((s,i)=>`<span><i class="wa-swatch ${i?'secondary':''}"></i>${esc(this._sensorName(s.entity))}</span>`).join(''):'<span><i class="wa-swatch"></i>Durchschnitt</span><span><i class="wa-swatch band"></i>Minimum / Maximum</span>'}</div><p class="hint wa-inspector" id="wa-inspector" aria-live="polite">${esc(d.chart_daily?'Tageswerte · Messpunkt für Details auswählen':'Stundenwerte · Messpunkt für Details auswählen')}</p>`;
  }
  _pointText(p,entity=this.activeEntity){return `${this._sensorName(entity)} · ${this._formatTime(p.start,true)} · Ø ${this._num(p.mean)} ${this.unit} · Min ${this._num(p.min)} ${this.unit} · Max ${this._num(p.max)} ${this.unit}`;}
  _inspectPoint(index,seriesIndex=0){const series=this._chartSeries()[seriesIndex],point=series?.data?.chart[index],slot=this.shadowRoot.getElementById('wa-inspector');if(point&&slot)slot.textContent=this._pointText(point,series.entity);}
  _comparisonSummary(){
    if(!this.compareEntity)return '';
    if(this._comparisonError)return notice(this._comparisonError,{error:true});
    if(!this._comparisonData)return notice('Für den Vergleichssensor sind noch keine Messwerte geladen.');
    const first=this._data,second=this._comparisonData;
    return section({id:'wa-sensor-comparison',title:'Sensorvergleich',expanded:true,content:statisticsTable({label:'Vergleich der Thermometer',columns:[{label:'Kennzahl'},{label:this._sensorName(first.entity_id),align:'right'},{label:this._sensorName(second.entity_id),align:'right'}],rows:[
      ['Aktuell °C',this._num(first.current),this._num(second.current)],['Durchschnitt °C',(first.summary.estimated?'≈ ':'')+this._num(first.summary.mean),(second.summary.estimated?'≈ ':'')+this._num(second.summary.mean)],['Minimum °C',this._num(first.summary.min),this._num(second.summary.min)],['Maximum °C',this._num(first.summary.max),this._num(second.summary.max)],['Datenintervalle',this._num(first.summary.coverage*100,0)+' %',this._num(second.summary.coverage*100,0)+' %']
    ]})})+notice('Weitere Kennzahlen beziehen sich auf '+this._sensorName(first.entity_id)+'.');
  }
  _overview(){
    const d=this._data,s=d.summary;
    return `<div class="wa-current">${accountTiles({label:'Aktuelle Messwerte und Extremwerte',content:
      accountTile({id:'wa-current',label:'Aktuell',state:'active',metrics:[
        {value:this._num(d.current),unit:this.unit,description:d.current==null?'Sensor nicht verfügbar':`Messung ${this._formatTime(d.last_updated)}`},
        {label:'Veränderung in 1 Std.',value:this._delta(d.trends.hour,false),unit:this.unit,description:d.trends.hour==null?'Noch keine Vergleichsdaten':d.trends.hour>.2?'Steigend':d.trends.hour<-.2?'Fallend':'Nahezu konstant'}
      ]})+
      accountTile({id:'wa-extrema',label:'Minimum / Maximum',metrics:[
        {label:'Minimum',value:this._num(s.min),unit:this.unit,description:this._extremeDescription(s,'min')},
        {label:'Maximum',value:this._num(s.max),unit:this.unit,description:this._extremeDescription(s,'max')}
      ]})})}</div>
      ${this._chart()}${this._comparisonSummary()}
      ${section({id:'wa-trends',title:'Weitere Vergleiche',expanded:false,content:
        row({title:'Veränderung in 3 Stunden',trailing:esc(this._delta(d.trends.three_hours))})+
        row({title:'Gestern zur gleichen Uhrzeit',trailing:esc(this._delta(d.trends.yesterday))})})}`;
  }
  _statistics(){
    const d=this._data,s=d.summary,wind=this.view==='wind',temperature=this.view==='temperature',known=s.exact_seconds>0;
    const threshold=(id,label,key)=>row({title:label,description:known?`Erfasst für ${this._num(s.duration_coverage*100,0)} % des Zeitraums`:'Keine Detailhistorie für diesen Zeitraum',trailing:esc(known?this._num(s[key])+' h':'—')});
    return section({id:'wa-statistics',title:'Weitere Kennzahlen',expanded:false,content:
      (temperature?section({id:'wa-thresholds',title:'Grenzwertdauern',content:threshold('frost','Unter 0 °C','frost_hours')+threshold('warm','Ab 25 °C','warm_hours')+threshold('hot','Ab 30 °C','hot_hours')})+
      section({id:'wa-days',title:'Besondere Tage',expanded:false,content:row({title:'Frosttage · Minimum unter 0 °C',trailing:String(s.frost_days)})+row({title:'Warme Tage · Maximum ab 25 °C',trailing:String(s.warm_days)})+row({title:'Heiße Tage · Maximum ab 30 °C',trailing:String(s.hot_days)})+notice('Gezählt werden Tage mit nachgewiesener Grenzwertüberschreitung. Fehlende Tage gelten nicht als frostfrei.')}):'')+
      section({id:'wa-compare',title:'Zeitraumvergleich',content:Object.entries(d.comparisons).map(([key,value])=>row({title:key==='year'?'Gleicher Zeitraum im Vorjahr':'Vorheriger gleich langer Zeitraum',description:value.mean==null?'Keine Vergleichsdaten':`Ø ${this._num(value.mean)} ${this.unit} · Datenintervalle ${this._num(value.coverage*100,0)} %`,trailing:esc(this._delta(value.delta))})).join('')})+
      section({id:'wa-records',title:'Rekorde seit Aufzeichnung',content:['min','max'].map(kind=>{const r=d.records[kind];return row({title:wind?(kind==='min'?'Niedrigster Windwert':'Höchster Windwert'):this.view==='illuminance'?(kind==='min'?'Niedrigster Helligkeitswert':'Höchster Helligkeitswert'):(kind==='min'?'Kältester Messwert':'Wärmster Messwert'),description:r?.at?this._formatTime(r.at,true):'Datum in älteren Langzeitstatistiken nicht gespeichert',trailing:esc(r?this._num(r.value)+' '+this.unit:'—')});}).join('')})+
      section({id:'wa-months',title:'Monatsübersicht im gewählten Zeitraum',expanded:false,content:this._monthlyTable(s.days)})+
      section({id:'wa-measurements',title:'Tageswerte',expanded:false,content:statisticsTable({label:'Tägliche Messwerte',columns:[{label:'Tag'},{label:'Min '+this.unit,align:'right'},{label:'Ø '+this.unit,align:'right'},{label:'Max '+this.unit,align:'right'}],rows:s.days.map(r=>[this._dateLabel(r.date),this._num(r.min),this._num(r.mean),this._num(r.max)])})})});
  }
  _monthlyTable(days){
    const months=new Map();for(const d of days){const key=d.date.slice(0,7);const m=months.get(key)||{seconds:0,sum:0,min:Infinity,max:-Infinity};m.seconds+=d.seconds;m.sum+=d.mean*d.seconds;m.min=Math.min(m.min,d.min);m.max=Math.max(m.max,d.max);months.set(key,m);}
    return statisticsTable({label:'Monatliche Messwerte',columns:[{label:'Monat'},{label:'Min '+this.unit,align:'right'},{label:'Ø '+this.unit,align:'right'},{label:'Max '+this.unit,align:'right'}],rows:[...months].map(([key,m])=>[key.slice(5)+'.'+key.slice(0,4),this._num(m.min),this._num(m.sum/m.seconds),this._num(m.max)])});
  }
  _settingsView(){
    const s=this._settingsDraft||this.settings;
    return `${section({id:'wa-card-settings',title:'Karte einrichten',content:
      `<div id="wa-settings-error">${this._error?notice(this._error,{error:true}):''}</div>`+
      multiSelect({id:'wa-sensors',label:'Relevante Thermometer',action:'choose-thermometers',values:s.entities,items:this._sensors.map(x=>({value:x.entity_id,label:x.name,description:x.entity_id})),disabled:!this._admin})+
      section({id:'wa-sensor-names',title:'Namen in dieser Karte',content:`<div id="wa-alias-fields" class="wa-alias-list">${this._aliasFields(s.entities)}</div>`})+
      '<p class="hint">Ausgewählte Thermometer werden auch bei geschlossener Karte aufgezeichnet. In der Temperaturansicht kannst du direkt zwischen deinen Thermometern wechseln.</p>'+
      selectField({id:'wa-wind-sensor',label:'Windsensor',value:s.wind_entity||'',options:[{value:'',label:'Kein Windsensor ausgewählt'},...this._windSensors.map(x=>({value:x.entity_id,label:x.name}))],disabled:!this._admin})+
      selectField({id:'wa-illuminance-sensor',label:'Helligkeitssensor',value:s.illuminance_entity||'',options:[{value:'',label:'Kein Helligkeitssensor ausgewählt'},...this._illuminanceSensors.map(x=>({value:x.entity_id,label:x.name}))],disabled:!this._admin})})}
      ${section({id:'wa-history-settings',title:'Historie',content:'<p class="hint">Vorhandene Historie wird automatisch übernommen. Nach erneutem Import bleiben bereits gesicherte Werte erhalten. Geänderte Sensoren zuerst speichern.</p>'+(this._admin?button({label:'Historie übernehmen',action:'import-history',disabled:!this.settings.entities.length&&!this.settings.wind_entity&&!this.settings.illuminance_entity}):'')})}
      <div class="toolbar wa-setting-actions">${this._admin?button({label:'Speichern',action:'save-settings',variant:'primary'}):''}${button({label:'Zurück',action:'cancel-settings'})}</div>
      ${versionInfo({frontend:VERSION,backend:this._data?.version||VERSION,ui:UI_VERSION,label:'Weather Analysis'})}`;
  }
  _help(){return section({id:'wa-help',title:'So funktioniert Weather Analysis',content:
    '<p>Temperatur, Wind und Helligkeit stammen direkt von deinen gewählten HA-Sensoren. Bereits bei der ersten Auswahl werden vorhandene Detailhistorie und Langzeitstatistik ausgewertet. Anschließend werden Stundenwerte und Extremwerte auch bei geschlossener Karte gespeichert.</p>'+
    row({title:'Sensoren auswählen und vergleichen',description:'Die Integration wird einmal eingerichtet. Thermometer, Windsensor und Helligkeitssensor wählst du ausschließlich in den Einstellungen der Karte. Ausgewählte Thermometer kannst du hier für diese Karte umbenennen. Das Dropdown oben wechselt den Sensor; + fügt einen zweiten Sensor zum Vergleich hinzu. Mehrere Karten erhalten eigene Einstellungen über ihre Karten-ID.'})+
    row({title:'Datenqualität',description:'≈ kennzeichnet Mittelwerte aus verdichteten HA-Statistiken. Grenzwertdauern und genaue Extremzeiten stammen aus vorhandener Detailhistorie und eigener Aufzeichnung. Fehlende Detaildaten werden nicht erfunden.'})+
    row({title:'Messlücken',description:'Unavailable/unknown und bekannte HA-Ausfallzeiten bleiben Lücken. Vergleiche sind nur bei ähnlicher Datenabdeckung aussagekräftig.'})+
    row({title:'Wind',description:'Windgeschwindigkeit wird einheitlich in km/h angezeigt. Unterstützt werden auch m/s, mph, Knoten und ft/s. Der höchste Sensorwert ist keine separat gemessene Windböe.'})+
    row({title:'Zeitraum und Zeitzone',description:'Tag, Woche, Monat und Jahr reichen jeweils bis jetzt. Tagesgrenzen und Uhrzeiten folgen der HA-Zeitzone. Freie Zeiträume dürfen höchstens ein Jahr umfassen.'})});}
  render(){
    if(!this.config)return;
    this._rememberSections();
    let body;
    if(this.page==='settings')body=this._settingsView();
    else if(this.page==='help')body=this._help();
    else body=(!this.activeEntity?notice('Bitte den Sensor in den Einstellungen der Karte auswählen.')+(this._admin?button({label:'Sensoren auswählen',action:'navigate',data:{page:'settings'}}):''):
      this._periodControls()+(this._data?this._overview()+this._statistics():notice(this._busy?'Vorhandene Historie und Messwerte werden geladen …':'Zeitraum auswählen und anzeigen.')));
    const quality=this._data&&!['settings','help'].includes(this.page)?notice(`Datenintervalle: ${this._num(this._data.summary.coverage*100,0)} %${this._data.summary.estimated?' · teilweise aus HA-Langzeitstatistik (Messabdeckung unbekannt)':''}. Detailabdeckung: ${this._num(this._data.summary.duration_coverage*100,0)} % des Zeitraums.`):'';
    this._renderedScope=this.page;
    this.shadowRoot.innerHTML=`<style>${UI_CSS}${CSS}</style><ha-card>${navigation({label:'Weather Analysis',items:[{id:'temperature',label:'Temperatur'},{id:'wind',label:'Wind'},{id:'illuminance',label:'Helligkeit'}],active:this.page,settings:true,help:true,actions:[{icon:'refresh',label:'Aktualisieren',action:'reload',disabled:this._busy||this._refreshing}]})}<main>${this.page==='temperature'?`<div class="wa-title">${this._sensorPicker()}</div>`:''}${this._error&&this.page!=='settings'?notice(this._error,{error:true}):''}${body}<div class="wa-quality">${quality}</div></main></ha-card>`;
    this._restoreSections();
  }
}

class WeatherAnalysisCardEditor extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});}
  setConfig(config){this.config={card_id:crypto.randomUUID(),period:'day',title:'Weather Analysis',...config};this.render();}
  set hass(hass){this._hass=hass;this.render();}
  render(){if(!this.config)return;const c=this.config;
    this.shadowRoot.innerHTML=`<style>${UI_CSS}</style>${selectField({id:'period',label:'Startansicht',value:c.period,options:PERIODS.filter(([id])=>id!=='custom').map(([value,label])=>({value,label}))})}${field({id:'card_id',label:'Karten-ID',value:c.card_id,hint:'Für unabhängige Einstellungen eine eigene ID verwenden.'})}`;
    this.shadowRoot.onchange=event=>{const key=event.target.id;if(!['period','card_id'].includes(key))return;this.config={...this.config,[key]:event.target.value};this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));};
  }
}
if(!customElements.get('weather-analysis-card'))customElements.define('weather-analysis-card',WeatherAnalysisCard);
if(!customElements.get('weather-analysis-card-editor'))customElements.define('weather-analysis-card-editor',WeatherAnalysisCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==='weather-analysis-card'))window.customCards.push({type:'weather-analysis-card',name:'Weather Analysis',description:'Temperatur, Wind und Helligkeit mit vorhandener Historie und aufklappbaren Kennzahlen',icon:'mdi:thermometer',preview:true});
