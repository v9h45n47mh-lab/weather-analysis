import {UI_CSS, UI_VERSION, navigation, section, row, button, iconButton, selectField,
  field, notice, versionInfo, bindUI, escapeHtml as esc, accountTile, accountTiles,
  statisticsTable, filterButton, multiSelect, dateNavigation, orderHandle, weatherList} from './family-ui/1.12.0/family-ui.js';

const VERSION = '1.11.0';
const PERIODS = [['day','Tag'],['week','Woche'],['month','Monat'],['custom','Zeitraum']];
const SENSOR_TYPES={temperature:{list:'entities',single:'entity',source:'_sensors',id:'wa-sensors',label:'Thermometer',title:'Temperatur'},wind:{list:'wind_entities',single:'wind_entity',source:'_windSensors',id:'wa-wind-sensors',label:'Windsensoren',title:'Wind'},illuminance:{list:'illuminance_entities',single:'illuminance_entity',source:'_illuminanceSensors',id:'wa-illuminance-sensors',label:'Helligkeitssensoren',title:'Helligkeit'}};
const WEATHER_SENSOR_KINDS=['temperature','wind'];
const num = (value, digits=1) => value == null || !Number.isFinite(value) ? '—' : value.toLocaleString('de-DE',{minimumFractionDigits:digits, maximumFractionDigits:digits});
const dateKey = (date, timezone) => {
  const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date).map(p=>[p.type,p.value]));
  return `${p.year}-${p.month}-${p.day}`;
};
export function shiftDay(key, days) { const d=new Date(key+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10); }
export function shiftMonth(key, months) {const d=new Date(key.slice(0,7)+'-01T12:00:00Z');d.setUTCMonth(d.getUTCMonth()+months);return d.toISOString().slice(0,10);}
export function periodStart(period,key){if(period==='month')return key.slice(0,7)+'-01';if(period==='week'){const dow=new Date(key+'T12:00:00Z').getUTCDay();return shiftDay(key,-((dow+6)%7));}return key;}
export function calendarDates(period,key,today){const start=periodStart(period,key),next=period==='week'?shiftDay(start,7):shiftMonth(start,1);return [start,shiftDay(next,-1)];}
export function periodDates(period, timezone, now=new Date()) {
  const today=dateKey(now,timezone);
  if(period==='yesterday')return [shiftDay(today,-1),shiftDay(today,-1)];
  if(period==='day')return [today,today];
  if(period==='week')return [shiftDay(today,-7),today];
  return period==='month'?calendarDates('month',today,today):[today,today];
}

const CSS = `
.wa-title{display:flex;align-items:center;justify-content:flex-start;gap:8px;padding:8px 0}
.wa-header-controls{display:flex;align-items:center;justify-content:flex-start;gap:8px;min-width:0;max-width:100%;margin-right:auto}
.wa-sensor-select{flex:0 1 150px;width:150px;max-width:150px;min-width:80px}.wa-sensor-select .field{margin:0}.wa-sensor-select select{min-width:0;max-width:100%}
.wa-alias-list{display:grid;gap:8px}.wa-alias-item{display:grid;grid-template-columns:minmax(0,1fr) 40px;gap:8px;align-items:center}.wa-alias-list>*{min-width:0}
.wa-chart .wa-series-secondary .wa-line{stroke:var(--warning-color,#ff9800)}.wa-chart .wa-series-secondary .wa-band{fill:var(--warning-color,#ff9800);opacity:.08}
.wa-chart .wa-series-secondary .wa-point{fill:var(--warning-color,#ff9800)}.wa-swatch.secondary{background:var(--warning-color,#ff9800)}
.wa-periods{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px}
.wa-date-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.wa-date-fields .field{min-width:0}.wa-date-fields input{min-width:0;max-width:100%}
.wa-range{margin:12px 0}.wa-chart-wrap{position:relative}.wa-chart{width:100%;display:block;height:auto;overflow:visible;touch-action:pan-y}.wa-chart-surface{fill:transparent;cursor:crosshair}.wa-cursor{pointer-events:none}.wa-cursor[hidden]{display:none}.wa-crosshair{stroke:var(--secondary-text-color,#727272);stroke-width:1;stroke-dasharray:3 3}.wa-cursor-point{fill:var(--primary-color,#03a9f4);stroke:var(--ha-card-background,var(--card-background-color,#fff));stroke-width:2}.wa-cursor-point.secondary{fill:var(--warning-color,#ff9800)}.wa-chart-details{min-height:calc(42px + var(--wa-detail-rows,1)*24px);margin-bottom:8px}.wa-chart-tooltip{position:relative;pointer-events:none;width:100%;box-sizing:border-box;background:var(--ha-card-background,var(--card-background-color,#fff));border:1px solid var(--divider-color,#e0e0e0);border-radius:var(--ha-card-border-radius,12px);padding:8px;overflow-wrap:anywhere}.wa-chart-tooltip[hidden]{display:none}.wa-tooltip-values{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 12px;margin:4px 0 0}.wa-tooltip-values dt{min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.wa-tooltip-values dd{margin:0;white-space:nowrap}.wa-tooltip-time{display:block}
.wa-chart text{font:inherit;font-size:12px;fill:var(--secondary-text-color,#727272)}
.wa-chart .wa-grid{stroke:var(--divider-color,#e0e0e0);stroke-width:1;stroke-dasharray:3 4}
.wa-chart .wa-line{fill:none;stroke:var(--primary-color,#03a9f4);stroke-width:2.5;stroke-linejoin:round}
.wa-chart .wa-band{fill:var(--primary-color,#03a9f4);opacity:.13}
.wa-chart .wa-point{fill:var(--primary-color,#03a9f4);stroke:var(--ha-card-background,var(--card-background-color,#fff));stroke-width:2}
.wa-chart .wa-hit{fill:transparent;stroke:none;cursor:crosshair}.wa-chart .wa-hit:focus{fill:var(--primary-color,#03a9f4);opacity:.3;outline:none}
.wa-inspector{min-height:36px;padding:4px 0;overflow-wrap:anywhere}
.wa-legend{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0}.wa-swatch{display:inline-block;width:16px;height:3px;background:var(--primary-color,#03a9f4);vertical-align:middle;margin-right:6px}.wa-swatch.band{height:10px;opacity:.25}
.wa-chart .wa-average-line{fill:none;stroke:var(--primary-color,#03a9f4);stroke-width:1.5;stroke-dasharray:3 5;opacity:.75}.wa-chart .wa-average-label{fill:var(--primary-color,#03a9f4);stroke:var(--ha-card-background,var(--card-background-color,#fff));stroke-width:3;paint-order:stroke;stroke-linejoin:round}.wa-chart .wa-series-secondary .wa-average-line{stroke:var(--warning-color,#ff9800)}.wa-chart .wa-series-secondary .wa-average-label{fill:var(--warning-color,#ff9800)}
.wa-forecast-source{margin-top:12px}.wa-forecast-source a{color:var(--primary-color,#03a9f4)}
.wa-current{margin:8px 0 12px}.wa-quality{margin-top:12px}.wa-setting-actions{margin-top:16px}
`;

class WeatherAnalysisCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this.page='dashboard';this._sensors=[];this._windSensors=[];this._illuminanceSensors=[];this._active={};this._settings={};this._request=0;this._busy=false;this._sectionStates=new Map();this._comparisons={};}
  static getConfigElement(){return document.createElement('weather-analysis-card-editor');}
  static getStubConfig(){return {card_id:crypto.randomUUID(),title:'Weather Analysis',period:'day'};}
  setConfig(config){
    if(!config || typeof config!=='object')throw new Error('Bitte eine Kartenkonfiguration angeben.');
    const previousId=this.config?.card_id;
    this.config={title:'Weather Analysis',period:'day',...config};
    this.config.card_id ||= this.config.entity || 'default';
    if(previousId!==this.config.card_id){this._sectionStates.clear();this._renderedScope=null;this._comparisons={};}
    this._draftNames=null;this._draftOrder=null;this._settingsDraft=null;
    this.period=PERIODS.some(([id])=>id===this.config.period)?this.config.period:this.config.period==='year'?'month':'day';
    this._periodStarts={};
    this._day=this.config.period==='yesterday'?shiftDay(dateKey(new Date(),this._hass?.config?.time_zone||'Europe/Berlin'),-1):null;
    this._dashboard=null;this._forecast=null;this._forecastError=null;this._ready=false;this._data=null;this._comparisonData=null;this._comparisonError=null;this._settings={};this._active={};this._request++;
    if(this._hass)this._initialize();else this.render();
  }
  set hass(hass){
    this._hass=hass;
    if(!this.config)return;
    if(!this._ready){this._initialize();return;}
    const signature=(this.page==='dashboard'?WEATHER_SENSOR_KINDS.map(kind=>this._entityFor(kind)):[this.activeEntity,this.compareEntity]).filter(Boolean).map(entity=>{const state=hass.states[entity];return entity+'|'+state?.state+'|'+state?.last_updated;}).join(';');
    if(this._signature!==signature){this._signature=signature;this._schedule();}
  }
  get settings(){
    const s={...this.config,...this._settings};
    for(const config of Object.values(SENSOR_TYPES)){s[config.list]??=s[config.single]?[s[config.single]]:[];}
    if(['Wetteranalyse','Temperaturanalyse'].includes(s.title))s.title='Weather Analysis';
    return s;
  }
  get view(){return ['wind','illuminance'].includes(this.page)?this.page:'temperature';}
  _num(value,digits=this.view==='illuminance'?0:1){return num(value,digits);}
  _delta(value,withUnit=true){return value==null?'—':`${value>0?'+':''}${this._num(value)}${withUnit?' '+this.unit:''}`;}
  get unit(){return {temperature:'°C',wind:'km/h',illuminance:'lx'}[this.view];}
  get sensorConfig(){return SENSOR_TYPES[this.view];}
  get selectedEntities(){return this.settings[this.sensorConfig.list];}
  _entityFor(kind){const config=SENSOR_TYPES[kind],entities=this.settings[config.list],chosen=this._active[kind]??this.settings[config.single];return entities.includes(chosen)?chosen:entities[0]||'';}
  get activeEntity(){return this._entityFor(this.view);}
  get comparison(){return this._comparisons[this.view]||=( {enabled:false,entity:''} );}
  get compareEntity(){if(!this.comparison.enabled)return '';const entity=this.comparison.entity;return this.selectedEntities.includes(entity)&&entity!==this.activeEntity?entity:this.selectedEntities.find(e=>e!==this.activeEntity)||'';}
  _sensorName(entity,fallback=''){return this.settings.sensor_names?.[entity]||[...this._sensors,...this._windSensors,...this._illuminanceSensors].find(s=>s.entity_id===entity)?.name||fallback||entity;}
  get availableSensors(){return this[this.sensorConfig.source];}
  connectedCallback(){
    this._unbind ||= bindUI(this.shadowRoot,event=>this._action(event));
    this._change ||= event=>this._onChange(event);
    this.shadowRoot.addEventListener('change',this._change);
    this._inspect ||= event=>{const hit=event.target.closest?.('[data-point]');if(hit)this._inspectPoint(Number(hit.dataset.point),Number(hit.dataset.series||0));};
    this.shadowRoot.addEventListener('pointerover',this._inspect);this.shadowRoot.addEventListener('focusin',this._inspect);
    this._chartMove||=event=>this._inspectChartPointer(event);
    this._chartDown||=event=>{const svg=event.target.closest?.('.wa-chart');if(!svg){this._hideChartCursor();return;}this._chartPointer=event.pointerId;svg.setPointerCapture?.(event.pointerId);this._inspectChartPointer(event);};
    this._chartEnd||=event=>{const svg=this.shadowRoot.querySelector('.wa-chart');if(svg?.hasPointerCapture?.(event.pointerId))svg.releasePointerCapture(event.pointerId);this._chartPointer=null;if(event.type==='pointercancel')this._hideChartCursor();};
    this._chartLeave||=event=>{if(event.target.matches?.('.wa-chart')&&event.pointerType!=='touch'&&this._chartPointer==null)this._hideChartCursor();};
    this.shadowRoot.addEventListener('pointermove',this._chartMove);this.shadowRoot.addEventListener('pointerdown',this._chartDown);
    this.shadowRoot.addEventListener('pointerup',this._chartEnd);this.shadowRoot.addEventListener('pointercancel',this._chartEnd);this.shadowRoot.addEventListener('pointerleave',this._chartLeave,true);
    this._periodKey ||= event=>{
      if(!['ArrowLeft','ArrowRight'].includes(event.key)||event.altKey||event.ctrlKey||event.metaKey||event.shiftKey||['settings','help','dashboard'].includes(this.page)||this.period==='custom'||event.target.closest?.('input,select,textarea,[contenteditable="true"]'))return;
      event.preventDefault();this._action({action:this.period==='day'?(event.key==='ArrowLeft'?'previous-day':'next-day'):(event.key==='ArrowLeft'?'previous-period':'next-period'),data:{}});
    };
    this.shadowRoot.addEventListener('keydown',this._periodKey);
    this._timer ||= setInterval(()=>{if(this.page!=='settings')this._fetch();},60000);
    if(this._ready)this._fetch();else if(this._hass&&this.config)this._initialize();
  }
  disconnectedCallback(){
    this._unbind?.();this._unbind=null;clearInterval(this._timer);this._timer=null;clearTimeout(this._debounce);
    this.shadowRoot.removeEventListener('keydown',this._periodKey);
    this.shadowRoot.removeEventListener('change',this._change);this.shadowRoot.removeEventListener('pointerover',this._inspect);this.shadowRoot.removeEventListener('focusin',this._inspect);
    this.shadowRoot.removeEventListener('pointermove',this._chartMove);this.shadowRoot.removeEventListener('pointerdown',this._chartDown);this.shadowRoot.removeEventListener('pointerup',this._chartEnd);this.shadowRoot.removeEventListener('pointercancel',this._chartEnd);this.shadowRoot.removeEventListener('pointerleave',this._chartLeave,true);
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
  _isRolling(period=this.period){return period==='week'?!this._periodStarts.week:false;}
  get _chartLimit(){return this._data?.display_end??this._data?.end;}
  _dates(now=new Date()){
    const today=dateKey(now,this.timezone||'Europe/Berlin');
    if(this._isRolling())return periodDates(this.period,this.timezone||'Europe/Berlin',now);
    if(this.period==='day'){const day=this._day||today;return [day,day];}
    if(['week','month'].includes(this.period))return calendarDates(this.period,this._periodStarts[this.period]||today,today);
    return this._custom||[today,today];
  }
  async _fetch(){
    if(this.page==='dashboard')return this._fetchDashboard();
    if(!this._ready||!this.activeEntity||!this._hass)return;
    const now=new Date(),request=++this._request,[start_date,end_date]=this._dates(now);
    const window=this._isRolling()?{window:this.period,as_of:now.getTime()/1000}:{};
    const entity=this.activeEntity,compare=this.compareEntity;
    this._busy=true;
    if(!this._data)this.render();
    try{
      const query=entity_id=>this._hass.callWS({type:'weather_analysis/analyse',entity_id,start_date,end_date,...window,...({day:900,week:3600,month:21600}[this.period]?{chart_interval:{day:900,week:3600,month:21600}[this.period]}:{})});
      const responses=await Promise.allSettled([query(entity),...(compare?[query(compare)]:[])]);
      if(request!==this._request)return;
      if(responses[0].status==='rejected')throw responses[0].reason;
      this._data=responses[0].value;this._error=null;
      this._comparisonData=responses[1]?.status==='fulfilled'?responses[1].value:null;
      this._comparisonError=responses[1]?.status==='rejected'?'Vergleichssensor: '+(responses[1].reason.message||String(responses[1].reason)):null;
    }catch(error){if(request===this._request){this._error=error.message||String(error);this._comparisonData=null;}}
    finally{if(request===this._request){this._busy=false;if(this.page!=='settings')this.render();}}
  }
  async _fetchDashboard(){
    if(!this._ready||!this._hass)return;
    const as_of=Math.floor(Date.now()/1000),request=++this._request;this._busy=true;this._error=null;this.render();
    const current=()=>request===this._request&&this.page==='dashboard';
    const sensors=this._hass.callWS({type:'weather_analysis/dashboard',as_of,...Object.fromEntries(WEATHER_SENSOR_KINDS.map(kind=>[kind+'_entity',this._entityFor(kind)]))}).then(result=>{if(current()){this._dashboard=result;this.render();}}).catch(error=>{if(current()){this._error=error.message||String(error);this.render();}});
    const prediction=this._hass.callWS({type:'weather_analysis/forecast',as_of}).then(result=>{if(current()){this._forecast=result.forecast;this._forecastError=result.forecast_error;this.render();}}).catch(error=>{if(current()){this._forecastError=error.message||String(error);this.render();}});
    await Promise.allSettled([sensors,prediction]);
    if(current()){this._busy=false;this.render();}
  }
  async _action({action,data,value}){
    if(action==='order-sensors'&&this._admin&&SENSOR_TYPES[data.kind]){
      const kind=data.kind,config=SENSOR_TYPES[kind];this._rememberAliasDraft();
      const selected=[...this.shadowRoot.querySelectorAll('#'+config.id+' input[type="checkbox"]:checked')].map(input=>input.value);
      const entities=this._orderedEntities(selected,kind),from=entities.indexOf(data.program),to=Math.max(0,Math.min(entities.length-1,from+Number(data.offset)));
      if(from<0||!Number.isInteger(to)||from===to)return;
      const [entity]=entities.splice(from,1);entities.splice(to,0,entity);this._draftOrder||={};this._draftOrder[kind]=entities;
      this.shadowRoot.getElementById('wa-alias-fields-'+kind).innerHTML=this._aliasFields(entities,kind);return;
    }
    if(action.startsWith('choose-sensors-')){const kind=action.slice('choose-sensors-'.length);if(SENSOR_TYPES[kind])this._refreshAliasFields(value,kind);return;}
    if(action==='compare-add'){if(this.selectedEntities.length<2)return;this.comparison.enabled=true;this.comparison.entity=this.selectedEntities.find(e=>e!==this.activeEntity);this._comparisonData=null;this._data=null;this.render();await this._fetch();return;}
    if(action==='compare-remove'){this.comparison.enabled=false;this.comparison.entity='';this._comparisonData=null;this._comparisonError=null;this._request++;this._busy=false;this.render();await this._fetch();return;}
    if(action==='navigate'){
      const oldView=this.view;if(data.page==='settings'&&this.page!=='settings'){this._draftNames={...this.settings.sensor_names};this._draftOrder=Object.fromEntries(Object.entries(SENSOR_TYPES).map(([kind,config])=>[kind,[...this.settings[config.list]]]));this._settingsDraft=null;}this.page=data.page;this._error=null;
      if(this.view!==oldView||!['settings','help'].includes(this.page)){this._request++;this._data=null;this._busy=false;}
      this.render();if(!['settings','help'].includes(this.page))await this._fetch();return;
    }
    if(action==='period'){this._request++;this._busy=false;this.period=data.period;this._data=null;this._error=null;this.render();if(this.period!=='custom')this._fetch();return;}
    if(action==='reload'){
      if(this.page==='settings'){
        this._rememberAliasDraft();
        this._settingsDraft={...this.settings,...this._readSettingsForm()};
      }
      this._refreshing=true;this.render();
      try{await this._initialize();}finally{this._refreshing=false;this.render();}return;
    }
    if(['previous-period','next-period','current-period'].includes(action)&&['week','month'].includes(this.period)){
      const today=dateKey(new Date(),this.timezone||'Europe/Berlin'),current=periodStart(this.period,today),start=this._periodStarts[this.period]||current;
      const direction=action==='previous-period'?-1:1;
      const target=action==='current-period'?current:this.period==='week'?shiftDay(start,direction*7):shiftMonth(start,direction);
      if(target>current)return;this._periodStarts[this.period]=action==='current-period'&&this.period==='week'?null:target;this._request++;this._data=null;this._busy=false;this._error=null;this.render();await this._fetch();return;
    }
    if(['previous-day','next-day','today'].includes(action)){
      const today=dateKey(new Date(),this.timezone||'Europe/Berlin');
      const target=action==='today'?null:shiftDay(this._day||today,action==='previous-day'?-1:1);
      if(target&&target>today)return;this._day=target;this._request++;this._data=null;this._busy=false;this._error=null;this.render();await this._fetch();return;
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
    if(action==='cancel-settings'){this._settingsDraft=null;this._draftOrder=null;this.page='temperature';this._request++;this._busy=false;this._data=null;this._error=null;this.render();await this._fetch();return;}
    if(action==='save-settings'&&this._admin){
      const settings=this._readSettingsForm();
      try {
        const previous=this._settings;
        let saved;try{saved=await this._persistSettings(settings);}catch(error){this._settings=previous;throw error;}
        this._settings=saved;this._draftNames=null;this._draftOrder=null;this._settingsDraft=null;this._active={};for(const [kind,config] of Object.entries(SENSOR_TYPES)){if(saved[config.list].length<2)this._comparisons[kind]={enabled:false,entity:''};}this._request++;this._data=null;this._error=null;this.page='temperature';await this._fetch();
      }catch(error){this._error=error.message||String(error);const slot=this.shadowRoot.getElementById('wa-settings-error');if(slot)slot.innerHTML=notice(this._error,{error:true});}
    }
  }
  _onChange(event){
    if(event.target.id==='wa-compare-sensor'){this.comparison.entity=event.target.value;this._comparisonData=null;this._request++;this._busy=false;this.render();this._fetch();return;}
    if(event.target.id==='wa-active-sensor'){const previous=this.activeEntity;this._active[this.view]=event.target.value;if(this.comparison.entity===event.target.value)this.comparison.entity=previous;this._comparisonData=null;this._request++;this._data=null;this._busy=false;this._error=null;this.render();this._fetch();return;}
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
  _readSettingsForm(){
    const settings={title:this.settings.title||'Weather Analysis'},selected=new Set();
    for(const [kind,config] of Object.entries(SENSOR_TYPES)){
      const entities=this._orderedEntities([...this.shadowRoot.querySelectorAll('#'+config.id+' input[type="checkbox"]:checked')].map(x=>x.value),kind);
      entities.forEach(entity=>selected.add(entity));settings[config.list]=entities;
      const primary=this._active[kind]??this.settings[config.single];settings[config.single]=entities.includes(primary)?primary:entities[0]||'';
    }
    settings.sensor_names=Object.fromEntries([...this.shadowRoot.querySelectorAll('[data-alias-entity]')].map(el=>[el.dataset.aliasEntity,el.querySelector('input').value.trim()]).filter(([entity,name])=>selected.has(entity)&&name));
    return settings;
  }
  _sensorPicker(){
    const entities=this.selectedEntities,options=entities.map(entity=>({value:entity,label:this._sensorName(entity)}));
    const primary=selectField({id:'wa-active-sensor',label:this.sensorConfig.label,hideLabel:true,value:this.activeEntity,
      options:options.length?options:[{value:'',label:'In Einstellungen auswählen'}],disabled:!options.length});
    const compare=this.comparison.enabled&&this.compareEntity;
    return `<div class="wa-header-controls"><div class="wa-sensor-select">${primary}</div>${compare?
      `<div class="wa-sensor-select">${selectField({id:'wa-compare-sensor',label:'Vergleichssensor',hideLabel:true,value:this.compareEntity,options:options.filter(o=>o.value!==this.activeEntity)})}</div>${iconButton({icon:'close',label:'Vergleich entfernen',action:'compare-remove'})}`:
      iconButton({icon:'add',label:'Zweiten Sensor vergleichen',action:'compare-add',disabled:entities.length<2})}</div>`;
  }
  _rememberAliasDraft(){
    this._draftNames||={...this.settings.sensor_names};
    for(const el of this.shadowRoot.querySelectorAll('[data-alias-entity]'))this._draftNames[el.dataset.aliasEntity]=el.querySelector('input').value;
  }
  _orderedEntities(entities,kind){
    const order=this._draftOrder?.[kind]||this.settings[SENSOR_TYPES[kind].list];
    return [...order.filter(entity=>entities.includes(entity)),...entities.filter(entity=>!order.includes(entity))];
  }
  _aliasFields(entities,kind){
    const names=this._draftNames||this.settings.sensor_names||{},source=this[SENSOR_TYPES[kind].source];
    return entities.length?entities.map((entity,index)=>`<div class="wa-alias-item fui-order-item" data-alias-entity="${esc(entity)}">${field({id:'wa-'+kind+'-alias-'+index,label:source.find(s=>s.entity_id===entity)?.name||entity,value:names[entity]||'',maxLength:100,hint:entity+' · leer = ursprünglicher Name',disabled:!this._admin})}${orderHandle({id:entity,index,count:entities.length,action:'order-sensors',group:kind,label:'Sensor verschieben',disabled:!this._admin,data:{kind}})}</div>`).join(''):notice('Zuerst relevante Sensoren auswählen.');
  }
  _refreshAliasFields(entities,kind){
    this._rememberAliasDraft();
    entities=this._orderedEntities(entities,kind);this._draftOrder||={};this._draftOrder[kind]=entities;
    const slot=this.shadowRoot.getElementById('wa-alias-fields-'+kind);
    if(slot)slot.innerHTML=this._aliasFields(entities,kind);
  }
  _sensorSettings(kind,s){
    const config=SENSOR_TYPES[kind],entities=this._orderedEntities(s[config.list]||[],kind);
    return section({id:'wa-select-'+kind,title:config.label,content:
      section({id:'wa-sensor-selection-'+kind,title:'Sensorauswahl',expanded:false,content:multiSelect({id:config.id,label:'Relevante '+config.label,action:'choose-sensors-'+kind,values:entities,items:this[config.source].map(sensor=>({value:sensor.entity_id,label:sensor.name,description:config.title+' · '+({temperature:'°C / °F / K',wind:'km/h / m/s',illuminance:'lx / Lux'}[kind])+' · '+sensor.entity_id})),disabled:!this._admin})})+
      section({id:'wa-names-'+kind,title:config.title,content:`<div id="wa-alias-fields-${kind}" class="wa-alias-list">${this._aliasFields(entities,kind)}</div>`})});
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
      ${this.period==='day'?dateNavigation({label:this._dateLabel(start),todayLabel:'Aktuell',previousLabel:'Vorheriger Tag',nextLabel:'Nächster Tag',previousAction:'previous-day',nextAction:'next-day',nextDisabled:this._isRolling()||start>=dateKey(new Date(),this.timezone||'Europe/Berlin')}):['week','month'].includes(this.period)?dateNavigation({label:this._isRolling()?'7 Tage + heute':this._periodLabel(start),previousLabel:this.period==='week'?'Vorherige Woche':'Vorheriger Monat',nextLabel:this.period==='week'?'Nächste Woche':'Nächster Monat',todayLabel:'Aktuell',todayAction:'current-period',nextDisabled:this._isRolling()||start>=periodStart(this.period,dateKey(new Date(),this.timezone||'Europe/Berlin'))}):''}
      ${this.period==='custom'?`<div class="wa-date-fields">${field({id:'wa-from',label:'Von',type:'date',value:start})}${field({id:'wa-to',label:'Bis',type:'date',value:end,min:start})}</div><div class="toolbar">${button({label:'Anzeigen',action:'custom-apply',variant:'primary'})}</div>`:''}
      <p class="hint wa-range">${esc(this._rangeLabel(start,end))}</p>`;
  }
  _rangeLabel(start,end){
    const range=this._dateLabel(start)+(start!==end?' – '+this._dateLabel(end):'');
    if(this.period==='day')return range+' · 00:00–23:59'+(this._data?.partial?' · bisher':'');
    return range+(this._isRolling()?' · bis jetzt':this._data?.partial?' · bisher':'');
  }
  _periodLabel(start){
    const d=new Date(start+'T12:00:00Z');
    if(this.period==='month')return d.toLocaleDateString('de-DE',{timeZone:'UTC',month:'long',year:'numeric'});
    d.setUTCDate(d.getUTCDate()+3);const year=d.getUTCFullYear(),week=Math.ceil(((d-new Date(year+'-01-01T12:00:00Z'))/86400000+1)/7);
    return `KW ${week} · ${year}`;
  }
  _resolutionLabel(interval=this._data?.chart_interval){return {900:'15-Minuten-Mittel',3600:'Stundenmittel',10800:'3-Stunden-Mittel',21600:'6-Stunden-Mittel',86400:'Tagesmittel'}[interval]||'Stundenmittel';}
  _dateLabel(key){return new Date(key+'T12:00:00Z').toLocaleDateString('de-DE',{timeZone:'UTC',day:'2-digit',month:'2-digit',year:'numeric'});}
  _chartSeries(){
    const series=[{data:this._data,entity:this.activeEntity}];
    if(this.compareEntity&&this._comparisonData?.entity_id===this.compareEntity)series.push({data:this._comparisonData,entity:this.compareEntity});
    return series;
  }
  _chart(){
    const d=this._data,end=this._chartLimit,series=this._chartSeries(),points=series.flatMap(s=>s.data.chart);
    if(!points.length)return notice('Für diesen Zeitraum sind noch keine Messwerte vorhanden.');
    const W=640,H=240,L=48,R=18,T=18,B=34;
    let low=Math.min(...points.map(p=>p.min??p.mean),...series.map(s=>s.data.summary.mean).filter(Number.isFinite)),high=Math.max(...points.map(p=>p.max??p.mean),...series.map(s=>s.data.summary.mean).filter(Number.isFinite));
    const pad=Math.max(1,(high-low)*.15);low-=pad;high+=pad;
    const x=t=>L+(t-d.start)/Math.max(1,end-d.start)*(W-L-R),y=v=>T+(high-v)/(high-low)*(H-T-B);
    this._chartGeometry={W,H,L,R,T,B,low,high};
    const plotted=series.map((series,seriesIndex)=>{
      const groups=[];let group=[];const interval=series.data.chart_interval||(series.data.chart_daily?86400:3600);
      for(const point of series.data.chart){if(group.length&&point.start>(group.at(-1).end??group.at(-1).start+interval)+1){groups.push(group);group=[];}group.push(point);}if(group.length)groups.push(group);
      const paths=groups.map(g=>{
        const line=g.map((p,i)=>`${i?'L':'M'}${x(p.start).toFixed(2)},${y(p.mean).toFixed(2)}`).join(' ');
        const band=[...g.map(p=>[x(p.start),y(p.max??p.mean)]),...g.toReversed().map(p=>[x(p.start),y(p.min??p.mean)])].map(([a,b],i)=>`${i?'L':'M'}${a.toFixed(2)},${b.toFixed(2)}`).join(' ')+' Z';
        return `<path class="wa-band" d="${band}"/><path class="wa-line" d="${line}"/>${g.length===1?`<circle class="wa-point" cx="${x(g[0].start)}" cy="${y(g[0].mean)}" r="4"/>`:""}`;
      }).join('');
      return `<g class="wa-series ${seriesIndex?'wa-series-secondary':'wa-series-primary'}" data-series-entity="${esc(series.entity)}">${paths}${series.data.chart.map((p,i)=>`<circle class="wa-hit" data-series="${seriesIndex}" data-point="${i}" tabindex="0" role="img" aria-label="${esc(this._pointText(p,series.entity))}" cx="${x(p.start)}" cy="${y(p.mean)}" r="9"><title>${esc(this._pointText(p,series.entity))}</title></circle>`).join('')}</g>`;
    }).join('');
    let previousMeanLabel=null;
    const averages=series.map((entry,index)=>{
      const mean=entry.data.summary.mean;if(!Number.isFinite(mean))return '';
      const at=y(mean);let labelY=Math.max(T+12,Math.min(H-B-4,at-6));
      if(previousMeanLabel!==null&&Math.abs(labelY-previousMeanLabel)<16)labelY=Math.min(H-B-4,previousMeanLabel+16);
      previousMeanLabel=labelY;
      return `<g class="${index?'wa-series-secondary':'wa-series-primary'}"><path class="wa-average-line" d="M${L},${at} H${W-R}"/><text class="wa-average-label" x="${W-R-4}" y="${labelY}" text-anchor="end"><title>Durchschnitt im gewählten Zeitraum · ${esc(this._sensorName(entry.entity))}</title>Ø ${esc(this._num(mean))} ${esc(this.unit)}</text></g>`;
    }).join('');
    return `<div class="wa-chart-wrap"><div class="wa-chart-details" style="--wa-detail-rows:${series.length}"><div class="wa-chart-tooltip" id="wa-chart-tooltip" role="tooltip" hidden></div><p class="hint" id="wa-chart-prompt">Maus oder Finger über den Verlauf bewegen, um die Werte zu sehen.</p></div><svg class="wa-chart" viewBox="0 0 ${W} ${H}" role="group" aria-label="${this.view==='wind'?'Windverlauf in Kilometer pro Stunde':this.view==='illuminance'?'Helligkeitsverlauf in Lux':'Temperaturverlauf in Grad Celsius'}"><title>${this.view==='wind'?'Windverlauf':this.view==='illuminance'?'Helligkeitsverlauf':'Temperaturverlauf'}</title><desc>${series.length>1?'Zwei durchgezogene Linien mit gemeinsamer Messwertskala und verschiedenen Farben.':'Linie: Durchschnitt. Band: Minimum bis Maximum.'} Maus oder Finger über den Verlauf bewegen, um Intervallwerte zu sehen. Messpunkte lassen sich mit Tab auswählen.</desc>
      ${Array.from({length:5},(_,i)=>{const value=low+(high-low)*i/4;return `<path class="wa-grid" d="M${L},${y(value)} H${W-R}"/><text text-anchor="end" x="${L-8}" y="${y(value)+4}">${this._num(value,0)}${this.view==='temperature'?'°':''}</text>`;}).join('')}
      ${plotted}${averages}
      <rect class="wa-chart-surface" x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}"/>
      <g class="wa-cursor" id="wa-cursor" hidden><path class="wa-crosshair" id="wa-crosshair"/>${series.map((entry,index)=>`<circle class="wa-cursor-point ${index?'secondary':''}" data-cursor-series="${index}" r="4" visibility="hidden"/>`).join('')}</g>
      ${[0,.5,1].map((fraction,i)=>`<text x="${L+fraction*(W-L-R)}" y="${H-7}" text-anchor="${i===0?'start':i===2?'end':'middle'}">${esc(new Intl.DateTimeFormat('de-DE',{timeZone:this.timezone,...(this.period!=='day'?{day:'2-digit',month:'2-digit'}:{hour:'2-digit',minute:'2-digit'})}).format(new Date((fraction===1?end-(this.period==='day'?60:1):d.start+fraction*(end-d.start))*1000)))}</text>`).join('')}</svg></div>
      <div class="wa-legend hint">${series.length>1?series.map((s,i)=>`<span><i class="wa-swatch ${i?'secondary':''}"></i>${esc(this._sensorName(s.entity))}</span>`).join(''):'<span><i class="wa-swatch"></i>Durchschnitt</span><span><i class="wa-swatch band"></i>Minimum / Maximum</span>'}</div><p class="hint wa-inspector" id="wa-inspector" aria-live="polite">${esc(this._resolutionLabel()+' · Maus oder Finger für Details bewegen'+(d.chart_fallback?' · ältere Abschnitte nur stündlich':''))}</p>`;
  }
  _pointText(p,entity=this.activeEntity){return `${this._sensorName(entity)} · ${this._formatTime(p.start,true)} · ${this._resolutionLabel(p.resolution||this._data?.chart_interval)} · Ø ${this._num(p.mean)} ${this.unit} · Min ${this._num(p.min)} ${this.unit} · Max ${this._num(p.max)} ${this.unit}`;}
  _inspectPoint(index,seriesIndex=0){
    const point=this._chartSeries()[seriesIndex]?.data?.chart[index];
    if(point)this._showChartCursor(point.start);
  }
  _inspectChartPointer(event){
    const svg=event.target.closest?.('.wa-chart');if(!svg||!this._data||!this._chartGeometry)return;
    const rect=svg.getBoundingClientRect(),g=this._chartGeometry;
    if(!rect.width||!rect.height)return;
    const x=(event.clientX-rect.left)/rect.width*g.W,y=(event.clientY-rect.top)/rect.height*g.H;
    if(this._chartPointer==null&&(x<g.L||x>g.W-g.R||y<g.T||y>g.H-g.B)){this._hideChartCursor();return;}
    const fraction=Math.max(0,Math.min(1,(x-g.L)/(g.W-g.L-g.R)));
    this._showChartCursor(this._data.start+fraction*(this._chartLimit-this._data.start));
  }
  _showChartCursor(time){
    const svg=this.shadowRoot.querySelector('.wa-chart'),tooltip=this.shadowRoot.getElementById('wa-chart-tooltip'),cursor=this.shadowRoot.getElementById('wa-cursor');
    if(!svg||!tooltip||!cursor||!this._data||!this._chartGeometry)return;
    const target=Math.max(this._data.start,Math.min(time,this._chartLimit-.001)),series=this._chartSeries();
    const readings=series.map(entry=>({...entry,point:entry.data.chart.find(point=>point.start<=target&&target<(point.end??point.start+(point.resolution||entry.data.chart_interval||(entry.data.chart_daily?86400:3600))))}));
    const at=readings.find(entry=>entry.point)?.point.start??target,g=this._chartGeometry;
    const x=g.L+(at-this._data.start)/Math.max(1,this._chartLimit-this._data.start)*(g.W-g.L-g.R);
    cursor.removeAttribute('hidden');this.shadowRoot.getElementById('wa-crosshair').setAttribute('d',`M${x},${g.T} V${g.H-g.B}`);
    for(const [index,entry] of readings.entries()){
      const dot=cursor.querySelector('[data-cursor-series="'+index+'"]');if(!dot)continue;
      if(!entry.point){dot.setAttribute('visibility','hidden');continue;}
      dot.removeAttribute('visibility');dot.setAttribute('cx',String(g.L+(entry.point.start-this._data.start)/Math.max(1,this._chartLimit-this._data.start)*(g.W-g.L-g.R)));dot.setAttribute('cy',String(g.T+(g.high-entry.point.mean)/(g.high-g.low)*(g.H-g.T-g.B)));
    }
    tooltip.innerHTML=`<strong class="wa-tooltip-time">${esc(this._formatTime(at,true))}</strong><dl class="wa-tooltip-values">`+readings.map((entry,index)=>`<dt title="${esc(this._sensorName(entry.entity))}"><i class="wa-swatch ${index?'secondary':''}"></i>${esc(this._sensorName(entry.entity))}</dt><dd data-value-entity="${esc(entry.entity)}"${entry.point?'':' title="Keine Messwerte in diesem Intervall"'}>${esc(entry.point?this._num(entry.point.mean)+' '+this.unit:'—')}</dd>`).join('')+'</dl>';
    tooltip.hidden=false;const prompt=this.shadowRoot.getElementById('wa-chart-prompt');if(prompt)prompt.hidden=true;
    const inspector=this.shadowRoot.getElementById('wa-inspector');
    if(inspector)inspector.textContent=readings.map(entry=>entry.point?this._pointText(entry.point,entry.entity):this._sensorName(entry.entity)+' · Keine Messwerte').join(' | ');
    this._cursorTime=at;
  }
  _hideChartCursor(){
    const tooltip=this.shadowRoot.getElementById('wa-chart-tooltip'),cursor=this.shadowRoot.getElementById('wa-cursor');
    if(tooltip)tooltip.hidden=true;if(cursor)cursor.setAttribute('hidden','');const prompt=this.shadowRoot.getElementById('wa-chart-prompt');if(prompt)prompt.hidden=false;
  }
  _comparisonSummary(){
    if(!this.compareEntity)return '';
    if(this._comparisonError)return notice(this._comparisonError,{error:true});
    if(!this._comparisonData)return notice('Für den Vergleichssensor sind noch keine Messwerte geladen.');
    const first=this._data,second=this._comparisonData;
    return section({id:'wa-sensor-comparison',title:'Sensorvergleich',expanded:true,content:statisticsTable({label:'Sensorvergleich',columns:[{label:'Kennzahl'},{label:this._sensorName(first.entity_id),align:'right'},{label:this._sensorName(second.entity_id),align:'right'}],rows:[
      ['Aktuell '+this.unit,this._num(first.current),this._num(second.current)],['Durchschnitt '+this.unit,(first.summary.estimated?'≈ ':'')+this._num(first.summary.mean),(second.summary.estimated?'≈ ':'')+this._num(second.summary.mean)],['Minimum '+this.unit,this._num(first.summary.min),this._num(second.summary.min)],['Maximum '+this.unit,this._num(first.summary.max),this._num(second.summary.max)],['Datenintervalle',this._num(first.summary.coverage*100,0)+' %',this._num(second.summary.coverage*100,0)+' %']
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
      section({id:'wa-records',title:'Rekorde seit Aufzeichnung',content:['min','max'].map(kind=>{const r=d.records[kind];return row({title:wind?(kind==='min'?'Niedrigster Windwert':'Höchster Windwert'):this.view==='illuminance'?(kind==='min'?'Niedrigster Helligkeitswert':'Höchster Helligkeitswert'):(kind==='min'?'Kältester Messwert':'Wärmster Messwert'),description:r?.at?this._formatTime(r.at,true):'Datum in älteren Langzeitstatistiken nicht gespeichert',trailing:esc(r?this._num(r.value)+' '+this.unit:'—')});}).join('')})});
  }
  _weatherPeriod(slot,kind,timezone){
    const time=timestamp=>new Intl.DateTimeFormat('de-DE',{timeZone:timezone,hour:'2-digit',minute:'2-digit'}).format(new Date(timestamp*1000));
    const end=time(slot.end)==='00:00'?'24:00':time(slot.end),actual=kind==='actual';
    const offsetTime=timestamp=>new Intl.DateTimeFormat('de-DE',{timeZone:timezone,hour:'2-digit',minute:'2-digit',timeZoneName:'shortOffset'}).format(new Date(timestamp*1000));
    const repeated=time(slot.start)===time(slot.end)&&slot.end>slot.start;
    const direction=Number.isFinite(slot.wind_direction)?['N','NO','O','SO','S','SW','W','NW'][Math.round(slot.wind_direction/45)%8]+' · ':'';
    const metrics=actual?[
      {icon:'wind',label:'Wind im Zeitraum',value:'Ø '+num(slot.wind_speed)+' km/h',detail:'Max. '+num(slot.wind_max)+' km/h'}
    ]:[
      {icon:'wind',label:'Wind bis',value:direction+num(slot.wind_speed,0)+' km/h',detail:'Böen '+num(slot.wind_gusts,0)+' km/h'},
      {icon:'rain',label:'Regenrisiko und Niederschlag',value:num(slot.precipitation_probability,0)+' % · '+(slot.partial?'ca. ':'')+num(slot.precipitation)+' mm'},
      {icon:'feels',label:'Gefühlte Temperatur',value:'Gefühlt '+num(slot.apparent_temperature)+' °C'},
      {icon:'humidity',label:'Luftfeuchtigkeit',value:num(slot.humidity,0)+' %'},
      {icon:'pressure',label:'Luftdruck auf Meereshöhe',value:num(slot.pressure,0)+' hPa'}
    ];
    return {time:(repeated?offsetTime(slot.start)+'–'+offsetTime(slot.end):time(slot.start)+'–'+end)+' Uhr',kind,start:slot.start,end:slot.end,
      detailsId:'wa-hours-'+kind+'-'+Math.floor(slot.period_start??slot.start),hours:(slot.hours||[]).map(hour=>this._weatherPeriod(hour,kind,timezone)),
      temperature:(actual&&slot.estimated?'≈ ':'')+num(slot.temperature)+' °C',temperatureLabel:actual?'Durchschnitt':'',
      range:'Min. '+num(slot.temperature_min)+'° · Max. '+num(slot.temperature_max)+'°',
      condition:actual?'':slot.condition,graphic:actual?{kind:'thermometer'}:{code:slot.weather_code,isDay:slot.is_day,windy:slot.wind_gusts>=40},metrics};
  }
  _dashboardView(){
    const d=this._dashboard,s=d?.sensors||{},temperature=s.temperature||{},wind=s.wind||{},f=this._forecast;
    const timezone=d?.timezone||this.timezone||'Europe/Berlin',today=d?.date||dateKey(new Date(),timezone);
    const sourceNames=WEATHER_SENSOR_KINDS.filter(kind=>s[kind]?.entity_id).map(kind=>SENSOR_TYPES[kind].title+': '+this._sensorName(s[kind].entity_id)).join(' · ');
    const current={id:'wa-weather-current',time:'Jetzt',kind:'actual',temperature:num(temperature.current)+' °C',
      range:'Min/Max heute '+num(temperature.min)+' / '+num(temperature.max)+' °C',graphic:{kind:'thermometer'},metrics:[
        {icon:'wind',label:'Wind aktuell',value:'Wind '+num(wind.current)+' km/h'}]};
    const measured=(d?.intervals||[]).map(slot=>this._weatherPeriod(slot,'actual',timezone));
    const forecastToday=f?.days?.find(day=>day.date===today);
    const actual=section({id:'wa-weather-actual',title:'Ist',expanded:false,content:measured.length?weatherList({label:'Ist · Heute',items:measured}):notice('Messwerte werden geladen …')});
    const now=section({id:'wa-weather-now',title:'Aktuell',content:d?weatherList({label:'Aktuell',items:[current]}):notice('Aktuelle Messwerte werden geladen …')});
    const prediction=forecastToday?.slots?.length?weatherList({label:'Vorhersage · Heute',items:forecastToday.slots.map(slot=>this._weatherPeriod(slot,'forecast',f.timezone))}):'';
    let future='';
    if(!f)future=notice(this._forecastError||'Wettervorhersage wird geladen …',{error:Boolean(this._forecastError)});
    else {
      const time=timestamp=>new Intl.DateTimeFormat('de-DE',{timeZone:f.timezone,hour:'2-digit',minute:'2-digit'}).format(new Date(timestamp*1000));
      future=(this._forecastError?notice(this._forecastError,{error:true}):'')+(f.stale?notice('Vorhersage konnte nicht aktualisiert werden. Angezeigt wird der letzte verfügbare Stand.'):'')+
        f.days.filter(day=>day.date!==today).map((day,index)=>section({id:'wa-forecast-'+(index+1),title:day.label,content:
          weatherList({label:day.label+' · Vorhersage',items:day.slots.map(slot=>this._weatherPeriod(slot,'forecast',f.timezone))})})).join('')+
        `<p class="hint wa-forecast-source">Wetterdaten: <a href="${esc(f.source_url)}" target="_blank" rel="noopener noreferrer">${esc(f.source)}</a> · Stand ${esc(time(f.updated_at))}</p>`;
    }
    const errors=Object.entries(d?.errors||{}).filter(([kind])=>WEATHER_SENSOR_KINDS.includes(kind)).map(([kind,message])=>SENSOR_TYPES[kind].title+': '+message).join(' · ');
    return (sourceNames?`<p class="hint wa-forecast-source">Messpunkte · ${esc(sourceNames)}</p>`:'')+(errors?notice(errors,{error:true}):'')+
      (!Object.keys(s).length&&this._admin?button({label:'Sensoren auswählen',action:'navigate',data:{page:'settings'}}):'')+
      section({id:'wa-forecast-0',title:'Heute',content:actual+now+prediction})+future;
  }
  _settingsView(){
    const s=this._settingsDraft||this.settings;
    return `${section({id:'wa-card-settings',title:'Karte einrichten',content:
      `<div id="wa-settings-error">${this._error?notice(this._error,{error:true}):''}</div>`+
      Object.keys(SENSOR_TYPES).map(kind=>this._sensorSettings(kind,s)).join('')})}
      ${section({id:'wa-history-settings',title:'Historie',content:'<p class="hint">Vorhandene Historie wird automatisch übernommen. Nach erneutem Import bleiben bereits gesicherte Werte erhalten. Geänderte Sensoren zuerst speichern.</p>'+(this._admin?button({label:'Historie übernehmen',action:'import-history',disabled:!Object.values(SENSOR_TYPES).some(config=>this.settings[config.list].length)}):'')})}
      <div class="toolbar wa-setting-actions">${this._admin?button({label:'Speichern',action:'save-settings',variant:'primary'}):''}${button({label:'Zurück',action:'cancel-settings'})}</div>
      ${versionInfo({frontend:VERSION,backend:this._data?.version||VERSION,ui:UI_VERSION,label:'Weather Analysis'})}`;
  }
  _help(){return section({id:'wa-help',title:'So funktioniert Weather Analysis',content:
    '<p>Temperatur, Wind und Helligkeit stammen direkt von deinen gewählten HA-Sensoren. Bereits bei der ersten Auswahl werden vorhandene Detailhistorie und Langzeitstatistik ausgewertet. Anschließend werden 15-Minuten-Werte, Stundenwerte und Extremwerte auch bei geschlossener Karte gespeichert.</p>'+
    row({title:'Sensoren auswählen und vergleichen',description:'Die Integration wird einmal eingerichtet. Sensoren aller drei Messarten wählst du ausschließlich in den Einstellungen der Karte. Ausgewählte Sensoren kannst du im jeweiligen Bereich für diese Karte umbenennen. Das Dropdown oben wechselt den Sensor; + fügt einen zweiten Sensor zum Vergleich hinzu. Mehrere Karten erhalten eigene Einstellungen über ihre Karten-ID.'})+
    row({title:'Wetter',description:'Ohne Kacheln zeigt die Übersicht die aktuell gewählten Sensoren und ihre gemessenen 3-Stunden-Mittelwerte in Blau. Der laufende Abschnitt endet mit dem gemeinsamen Abfragezeitpunkt; Forecast beginnt genau dort und erscheint schwarz auf hellem Grund. Aktuell steht zwischen Ist und Vorhersage und zeigt aktuelle Temperatur, Wind sowie Temperatur-Minimum und -Maximum von heute. Die Vorhersage für 67459 Böhl-Iggelheim kommt von Open-Meteo und wird alle 30 Minuten aktualisiert. Wetter ist der Startreiter. Die 3-Stunden-Zeiträume stehen untereinander. Ist ist anfangs zugeklappt, Aktuell geöffnet; beide Bereiche merken ihren Zustand. Wind steht bei allen Quellen in derselben Spalte. Jeder 3-Stunden-Zeitraum lässt sich am Faltpfeil in seine Stundenwerte aufklappen. Angebrochene Stunden enden beziehungsweise beginnen am Abfragezeitpunkt; fehlende Messwerte bleiben leer. Große Symbole veranschaulichen die Vorhersage. Temperatur und gefühlte Temperatur beziehen sich auf den Beginn des Abschnitts; Min/Max auf seinen gesamten Verlauf. Regenrisiko, Wind und Böen zeigen die stündlichen Höchstwerte, Niederschlag die Menge im Abschnitt. Luftfeuchte und Luftdruck ergänzen die Vorhersage.'})+
    row({title:'Datenqualität',description:'≈ kennzeichnet Mittelwerte aus verdichteten HA-Statistiken. Grenzwertdauern und genaue Extremzeiten stammen aus vorhandener Detailhistorie und eigener Aufzeichnung. Fehlende Detaildaten werden nicht erfunden.'})+
    row({title:'Messlücken',description:'Unavailable/unknown und bekannte HA-Ausfallzeiten bleiben Lücken. Vergleiche sind nur bei ähnlicher Datenabdeckung aussagekräftig.'})+
    row({title:'Wind',description:'Windgeschwindigkeit wird einheitlich in km/h angezeigt. Unterstützt werden auch m/s, mph, Knoten und ft/s. Der höchste Sensorwert ist keine separat gemessene Windböe.'})+
    row({title:'Zeitraum und Zeitzone',description:'Tag zeigt 15-Minuten-Mittel, Woche Stundenmittel und Monat 6-Stunden-Mittel. Aktuell zeigt bei Tag heute von 00:00 bis 23:59 Uhr und bei Woche heute plus die letzten sieben Tage. Die Pfeile wechseln zu vollständigen Kalendertagen oder Kalenderwochen (Montag bis Sonntag); vorwärts auf heute bleibt der volle Tag. Aktuell kehrt bei Tag zu heute und bei Woche zur rollierenden Wochensicht zurück. Monat bleibt der Kalendermonat. Zukünftige Abschnitte der Zeitachse enthalten keine Messwerte. Tagesgrenzen und Uhrzeiten folgen der HA-Zeitzone. Freie Zeiträume dürfen höchstens ein Jahr umfassen.'})});}
  render(){
    if(!this.config)return;
    this._rememberSections();
    let body;
    if(this.page==='dashboard')body=this._dashboardView();
    else if(this.page==='settings')body=this._settingsView();
    else if(this.page==='help')body=this._help();
    else body=(!this.activeEntity?notice('Bitte den Sensor in den Einstellungen der Karte auswählen.')+(this._admin?button({label:'Sensoren auswählen',action:'navigate',data:{page:'settings'}}):''):
      this._periodControls()+(this._data?this._overview()+this._statistics():notice(this._busy?'Vorhandene Historie und Messwerte werden geladen …':'Zeitraum auswählen und anzeigen.')));
    const quality=this._data&&!['settings','help','dashboard'].includes(this.page)?notice(`Datenintervalle: ${this._num(this._data.summary.coverage*100,0)} %${this._data.summary.estimated?' · teilweise aus HA-Langzeitstatistik (Messabdeckung unbekannt)':''}. Detailabdeckung: ${this._num(this._data.summary.duration_coverage*100,0)} % des Zeitraums.`):'';
    this._renderedScope=this.page;
    this.shadowRoot.innerHTML=`<style>${UI_CSS}${CSS}</style><ha-card>${navigation({label:'Weather Analysis',items:[{id:'dashboard',label:'Wetter'},{id:'temperature',label:'Temperatur'},{id:'wind',label:'Wind'},{id:'illuminance',label:'Helligkeit'}],active:this.page,settings:true,help:true,actions:[{icon:'refresh',label:'Aktualisieren',action:'reload',disabled:this._busy||this._refreshing}]})}<main>${!['settings','help','dashboard'].includes(this.page)?`<div class="wa-title">${this._sensorPicker()}</div>`:''}${this._error&&this.page!=='settings'?notice(this._error,{error:true}):''}${body}<div class="wa-quality">${quality}</div></main></ha-card>`;
    this._restoreSections();
  }
}

class WeatherAnalysisCardEditor extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});}
  setConfig(config){this.config={card_id:crypto.randomUUID(),period:'day',title:'Weather Analysis',...config};this.render();}
  set hass(hass){this._hass=hass;this.render();}
  render(){if(!this.config)return;const c=this.config;
    this.shadowRoot.innerHTML=`<style>${UI_CSS}</style>${selectField({id:'period',label:'Standardzeitraum',value:c.period,options:PERIODS.filter(([id])=>id!=='custom').map(([value,label])=>({value,label}))})}${field({id:'card_id',label:'Karten-ID',value:c.card_id,hint:'Für unabhängige Einstellungen eine eigene ID verwenden.'})}`;
    this.shadowRoot.onchange=event=>{const key=event.target.id;if(!['period','card_id'].includes(key))return;this.config={...this.config,[key]:event.target.value};this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));};
  }
}
if(!customElements.get('weather-analysis-card'))customElements.define('weather-analysis-card',WeatherAnalysisCard);
if(!customElements.get('weather-analysis-card-editor'))customElements.define('weather-analysis-card-editor',WeatherAnalysisCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==='weather-analysis-card'))window.customCards.push({type:'weather-analysis-card',name:'Weather Analysis',description:'Temperatur, Wind und Helligkeit mit vorhandener Historie und aufklappbaren Kennzahlen',icon:'mdi:thermometer',preview:true});
