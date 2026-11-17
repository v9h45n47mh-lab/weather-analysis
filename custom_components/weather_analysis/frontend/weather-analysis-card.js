import {UI_CSS, UI_VERSION, navigation, section, row, button, iconButton, selectField,
  field, notice, versionInfo, bindUI, escapeHtml as esc, accountTile, accountTiles,
  statisticsTable, filterButton} from './family-ui/1.7.0/family-ui.js';

const VERSION = '1.0.0';
const PERIODS = [['today','Heute'],['yesterday','Gestern'],['week','Woche'],['month','Monat'],['year','Jahr'],['custom','Zeitraum']];
const num = (value, digits=1) => value == null || !Number.isFinite(value) ? '—' : value.toLocaleString('de-DE',{minimumFractionDigits:digits, maximumFractionDigits:digits});
const delta = value => value == null ? '—' : `${value>0?'+':''}${num(value)} °C`;
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
  constructor(){super();this.attachShadow({mode:'open'});this.page='overview';this._sensors=[];this._settings={};this._request=0;this._busy=false;}
  static getConfigElement(){return document.createElement('weather-analysis-card-editor');}
  static getStubConfig(){return {card_id:crypto.randomUUID(),title:'Wetteranalyse',period:'today'};}
  setConfig(config){
    if(!config || typeof config!=='object')throw new Error('Bitte eine Kartenkonfiguration angeben.');
    this.config={title:'Wetteranalyse',period:'today',heating_base:20,heating_limit:15,...config};
    this.config.card_id ||= this.config.entity || 'default';
    this.period=PERIODS.some(([id])=>id===this.config.period)?this.config.period:'today';
    this._ready=false;this._data=null;this._settings={};
    if(this._hass)this._initialize();else this.render();
  }
  set hass(hass){
    this._hass=hass;
    if(!this.config)return;
    if(!this._ready){this._initialize();return;}
    const entity=this.settings.entity;
    const state=hass.states[entity];const signature=state?.state+'|'+state?.last_updated;
    if(this._signature!==signature){this._signature=signature;this._schedule();}
  }
  get settings(){return {...this.config,...this._settings};}
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
      this._sensors=result.sensors;this._settings=result.settings||{};this._admin=result.admin;this.timezone=result.timezone;
      if(!this.settings.entity&&this._sensors.length)this._settings.entity=this._sensors[0].entity_id;
      this._ready=true;this._error=null;this.render();await this._fetch();
    }catch(error){this._error='Weather Analysis ist noch nicht eingerichtet oder konnte nicht geladen werden. Bitte die Integration unter Geräte & Dienste hinzufügen. '+(error.message||'');this.render();}
    finally{this._initializing=false;}
  }
  _dates(){return this.period==='custom'?(this._custom||periodDates('today',this.timezone||'Europe/Berlin')):periodDates(this.period,this.timezone||'Europe/Berlin');}
  async _fetch(){
    if(!this._ready||!this.settings.entity||!this._hass)return;
    const request=++this._request;const [start_date,end_date]=this._dates();const settings=this.settings;
    this._busy=true;
    if(!this._data)this.render();
    try {
      const data=await this._hass.callWS({type:'weather_analysis/analyse',entity_id:settings.entity,
        start_date,end_date,heating_base:Number(settings.heating_base),heating_limit:Number(settings.heating_limit)});
      if(request!==this._request)return;
      this._data=data;this._error=null;
    }catch(error){if(request===this._request)this._error=error.message||String(error);}
    finally{if(request===this._request){this._busy=false;if(this.page!=='settings')this.render();}}
  }
  async _action({action,data}){
    if(action==='navigate'){this.page=data.page;this._error=null;this.render();return;}
    if(action==='period'){this.period=data.period;this._data=null;this._error=null;this.render();if(this.period!=='custom')this._fetch();return;}
    if(action==='reload'){if(this._ready)this._fetch();else this._initialize();return;}
    if(action==='custom-apply'){
      const start=this.shadowRoot.getElementById('wa-from').value,end=this.shadowRoot.getElementById('wa-to').value;
      if(!start||!end||start>end){this._error='Bitte einen gültigen Zeitraum auswählen.';this.render();return;}
      this._custom=[start,end];this._data=null;this._fetch();return;
    }
    if(action==='cancel-settings'){this.page='overview';this._error=null;this.render();return;}
    if(action==='save-settings'&&this._admin){
      const get=id=>this.shadowRoot.getElementById(id).value;
      const settings={entity:get('wa-sensor'),title:get('wa-title'),heating_base:Number(get('wa-base')),heating_limit:Number(get('wa-limit'))};
      try {
        const saved=await this._hass.callWS({type:'weather_analysis/save_card',card_id:this.config.card_id,...settings});
        this._settings=saved;this._data=null;this._error=null;this.page='overview';await this._fetch();
      }catch(error){this._error=error.message||String(error);const slot=this.shadowRoot.getElementById('wa-settings-error');if(slot)slot.innerHTML=notice(this._error,{error:true});}
    }
  }
  _onChange(event){if(event.target.id==='wa-from'||event.target.id==='wa-to')this._custom=[this.shadowRoot.getElementById('wa-from').value,this.shadowRoot.getElementById('wa-to').value];}
  _formatTime(seconds,full=false){return seconds==null?'Uhrzeit nicht gespeichert':new Intl.DateTimeFormat('de-DE',{timeZone:this.timezone,day:full?'2-digit':undefined,month:full?'2-digit':undefined,year:full?'numeric':undefined,hour:'2-digit',minute:'2-digit'}).format(new Date(seconds*1000));}
  _extremeDescription(summary,kind){return summary[kind+'_at']!=null?this._formatTime(summary[kind+'_at'],this.period!=='today'&&this.period!=='yesterday'):'Uhrzeit nicht gespeichert';}
  _tile(id,label,value,unit='',description='',state='neutral'){return accountTile({id:'wa-'+id,label,value,unit,description,state});}
  _periodControls(){
    const [start,end]=this._dates();
    return `<div class="wa-periods" role="group" aria-label="Auswertungszeitraum">${PERIODS.map(([id,label])=>filterButton({label,action:'period',selected:this.period===id,data:{period:id}})).join('')}</div>
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
    return `<svg class="wa-chart" viewBox="0 0 ${W} ${H}" role="group" aria-label="Temperaturverlauf in Grad Celsius"><title>Temperaturverlauf</title><desc>Linie: Durchschnitt. Band: Minimum bis Maximum. Messpunkte lassen sich mit Tab auswählen.</desc>
      ${Array.from({length:5},(_,i)=>{const value=low+(high-low)*i/4;return `<path class="wa-grid" d="M${L},${y(value)} H${W-R}"/><text text-anchor="end" x="${L-8}" y="${y(value)+4}">${num(value,0)}°</text>`;}).join('')}
      ${paths}${points.map((p,i)=>`<circle class="wa-point" cx="${x(p.start)}" cy="${y(p.mean)}" r="${points.length===1?4:2}"/><circle class="wa-hit" data-point="${i}" tabindex="0" role="img" aria-label="${esc(this._pointText(p))}" cx="${x(p.start)}" cy="${y(p.mean)}" r="9"><title>${esc(this._pointText(p))}</title></circle>`).join('')}
      ${[0,.5,1].map((fraction,i)=>`<text x="${L+fraction*(W-L-R)}" y="${H-7}" text-anchor="${i===0?'start':i===2?'end':'middle'}">${esc(new Intl.DateTimeFormat('de-DE',{timeZone:this.timezone,...(d.chart_daily?{day:'2-digit',month:'2-digit'}:{hour:'2-digit',minute:'2-digit'})}).format(new Date((d.start+fraction*(d.end-d.start))*1000)))}</text>`).join('')}</svg>
      <div class="wa-legend hint"><span><i class="wa-swatch"></i>Durchschnitt</span><span><i class="wa-swatch band"></i>Minimum / Maximum</span></div><p class="hint wa-inspector" id="wa-inspector" aria-live="polite">${esc(d.chart_daily?'Tageswerte · Messpunkt für Details auswählen':'Stundenwerte · Messpunkt für Details auswählen')}</p>`;
  }
  _pointText(p){return `${this._formatTime(p.start,true)} · Ø ${num(p.mean)} °C · Min ${num(p.min)} °C · Max ${num(p.max)} °C`;}
  _inspectPoint(index){const point=this._data?.chart[index],slot=this.shadowRoot.getElementById('wa-inspector');if(point&&slot)slot.textContent=this._pointText(point);}
  _overview(){
    const d=this._data,s=d.summary;
    return `<div class="wa-current">${accountTiles({label:'Aktuelle Temperatur',content:
      this._tile('current','Aktuell',num(d.current),'°C',d.current==null?'Sensor nicht verfügbar':`Messung ${this._formatTime(d.last_updated)}`,'active')+
      this._tile('trend','Veränderung in 1 Stunde',delta(d.trends.hour),'',d.trends.hour==null?'Noch keine Vergleichsdaten':d.trends.hour>.2?'Steigend':d.trends.hour<-.2?'Fallend':'Nahezu konstant')})}</div>
      ${this._chart()}
      ${accountTiles({label:'Temperaturkennzahlen',content:
      this._tile('min','Minimum',num(s.min),'°C',this._extremeDescription(s,'min'))+
      this._tile('max','Maximum',num(s.max),'°C',this._extremeDescription(s,'max'))+
      this._tile('mean',d.partial?'Durchschnitt bisher':'Durchschnitt',(s.estimated?'≈ ':'')+num(s.mean),'°C','Zeitlich gewichtet')+
      this._tile('range','Temperaturspanne',num(s.range),'°C','Maximum minus Minimum')})}
      ${section({id:'wa-trends',title:'Weitere Vergleiche',expanded:false,content:
        row({title:'Veränderung in 3 Stunden',trailing:esc(delta(d.trends.three_hours))})+
        row({title:'Gestern zur gleichen Uhrzeit',trailing:esc(delta(d.trends.yesterday))})})}`;
  }
  _statistics(){
    const d=this._data,s=d.summary;const known=s.exact_seconds>0;
    const threshold=(id,label,key)=>this._tile(id,label,known?num(s[key]):'—','h',known?`Erfasst für ${num(s.duration_coverage*100,0)} % des Zeitraums`:'Ab Einrichtung verfügbar');
    return `${accountTiles({label:'Grenzwertdauern',content:threshold('frost','Unter 0 °C','frost_hours')+threshold('warm','Ab 25 °C','warm_hours')+threshold('hot','Ab 30 °C','hot_hours')+
      this._tile('degree','Heizgradtage',num(s.heating_degree_days),'Kd',`${s.heating_days} vollständige Heiztage · ${num(this.settings.heating_base,0)}/${num(this.settings.heating_limit,0)} °C`)})}
      ${section({id:'wa-days',title:'Besondere Tage',content:row({title:'Frosttage · Minimum unter 0 °C',trailing:String(s.frost_days)})+row({title:'Warme Tage · Maximum ab 25 °C',trailing:String(s.warm_days)})+row({title:'Heiße Tage · Maximum ab 30 °C',trailing:String(s.hot_days)})+notice('Gezählt werden Tage mit nachgewiesener Grenzwertüberschreitung. Fehlende Tage gelten nicht als frostfrei.')})}
      ${section({id:'wa-compare',title:'Zeitraumvergleich',content:Object.entries(d.comparisons).map(([key,value])=>row({title:key==='year'?'Gleicher Zeitraum im Vorjahr':'Vorheriger gleich langer Zeitraum',description:value.mean==null?'Keine Vergleichsdaten':`Ø ${num(value.mean)} °C · Datenintervalle ${num(value.coverage*100,0)} %`,trailing:esc(delta(value.delta))})).join('')})}
      ${section({id:'wa-records',title:'Rekorde seit Aufzeichnung',content:['min','max'].map(kind=>{const r=d.records[kind];return row({title:kind==='min'?'Kältester Messwert':'Wärmster Messwert',description:r?.at?this._formatTime(r.at,true):'Datum in älteren Langzeitstatistiken nicht gespeichert',trailing:esc(r?num(r.value)+' °C':'—')});}).join('')})}
      ${section({id:'wa-months',title:'Monatsübersicht im gewählten Zeitraum',expanded:false,content:this._monthlyTable(s.days)})}
      ${section({id:'wa-measurements',title:'Tageswerte',expanded:false,content:statisticsTable({label:'Tägliche Temperaturwerte',columns:[{label:'Tag'},{label:'Min °C',align:'right'},{label:'Ø °C',align:'right'},{label:'Max °C',align:'right'}],rows:s.days.map(r=>[this._dateLabel(r.date),num(r.min),num(r.mean),num(r.max)])})})}`;
  }
  _monthlyTable(days){
    const months=new Map();for(const d of days){const key=d.date.slice(0,7);const m=months.get(key)||{seconds:0,sum:0,min:Infinity,max:-Infinity};m.seconds+=d.seconds;m.sum+=d.mean*d.seconds;m.min=Math.min(m.min,d.min);m.max=Math.max(m.max,d.max);months.set(key,m);}
    return statisticsTable({label:'Monatliche Temperaturwerte',columns:[{label:'Monat'},{label:'Min °C',align:'right'},{label:'Ø °C',align:'right'},{label:'Max °C',align:'right'}],rows:[...months].map(([key,m])=>[key.slice(5)+'.'+key.slice(0,4),num(m.min),num(m.sum/m.seconds),num(m.max)])});
  }
  _settingsView(){
    const s=this.settings;
    return `${section({id:'wa-card-settings',title:'Karte einrichten',content:
      `<div id="wa-settings-error"></div>${selectField({id:'wa-sensor',label:'Thermometer',value:s.entity,options:this._sensors.map(x=>({value:x.entity_id,label:x.name})),disabled:!this._admin})}
      ${field({id:'wa-title',label:'Anzeigename',value:s.title,maxLength:100,disabled:!this._admin})}
      <p class="hint">Weitere Thermometer unter Einstellungen → Geräte & Dienste → Integration hinzufügen → Weather Analysis einrichten.</p>`})}
      ${section({id:'wa-heating-settings',title:'Heizgradtage',content:`<div class="wa-date-fields">${field({id:'wa-base',label:'Raumtemperatur',value:s.heating_base,type:'number',min:0,max:40,step:.5,unit:'°C',disabled:!this._admin})}${field({id:'wa-limit',label:'Heizgrenze',value:s.heating_limit,type:'number',min:-20,max:30,step:.5,unit:'°C',disabled:!this._admin})}</div><p class="hint">Für vollständige Tage unterhalb der Heizgrenze wird Raumtemperatur minus Tagesmittel summiert.</p>`})}
      <div class="toolbar wa-setting-actions">${this._admin?button({label:'Speichern',action:'save-settings',variant:'primary',disabled:!this._sensors.length}):''}${button({label:'Zurück',action:'cancel-settings'})}</div>
      ${versionInfo({frontend:VERSION,backend:this._data?.version||VERSION,ui:UI_VERSION,label:'Weather Analysis'})}`;
  }
  _help(){return section({id:'wa-help',title:'So funktioniert die Wetteranalyse',content:
    `<p>Die Temperatur stammt direkt vom gewählten HA-Sensor. Ältere Werte werden aus seiner vorhandenen Langzeitstatistik gelesen. Die Integration ergänzt dauerhaft Stundenwerte, Grenzwertdauern und Uhrzeiten neuer Extremwerte – auch bei geschlossenem Dashboard.</p>
     ${row({title:'Datenqualität',description:'≈ kennzeichnet Mittelwerte mit verdichteten HA-Statistiken. Deren Intervalle verraten keine genaue Messabdeckung. Grenzwertstunden stammen ausschließlich aus der ergänzenden Aufzeichnung.'})}
     ${row({title:'Messlücken',description:'Unavailable/unknown, HA-Ausfälle und Zeiten vor Einrichtung werden nicht als gültige Messung fortgeschrieben. Vergleiche sind nur bei ähnlicher Datenabdeckung aussagekräftig.'})}
     ${row({title:'Zeitraum und Zeitzone',description:'Heute, Woche, Monat und Jahr reichen jeweils bis jetzt. Tagesgrenzen und Uhrzeiten verwenden die HA-Zeitzone. Freie Zeiträume dürfen höchstens ein Jahr umfassen.'})}
     ${row({title:'Mehrere Karten',description:'Neue Karten erhalten eine eigene Karten-ID. Kopierte Karten im Karteneditor mit einer anderen ID versehen, wenn sie eigene Einstellungen haben sollen.'})}
     ${row({title:'Sensorstandort',description:'Für Außentemperaturen möglichst einen schattigen, gut belüfteten Standort wählen. Direkte Sonne kann die Messung deutlich erhöhen.'})}`});}
  render(){
    if(!this.config)return;
    const title=this.settings.title||'Wetteranalyse';
    let body;
    if(this.page==='settings')body=this._settingsView();
    else if(this.page==='help')body=this._help();
    else if(!this._sensors.length)body=notice('Bitte zuerst unter Einstellungen → Geräte & Dienste die Integration Weather Analysis hinzufügen und dein Thermometer wählen.');
    else body=this._periodControls()+(this._data?(this.page==='statistics'?this._statistics():this._overview()):notice(this._busy?'Messwerte werden geladen …':'Zeitraum auswählen und anzeigen.'));
    const quality=this._data&&!['settings','help'].includes(this.page)?notice(`Datenintervalle: ${num(this._data.summary.coverage*100,0)} %${this._data.summary.estimated?' · teilweise aus HA-Langzeitstatistik (Messabdeckung unbekannt)':''}. Genaue Grenzwertdauern: ${num(this._data.summary.duration_coverage*100,0)} % des Zeitraums.`):'';
    const collapsed=new Map([...this.shadowRoot.querySelectorAll('[data-ui="collapse"]')].map(el=>[el.getAttribute('aria-controls'),el.getAttribute('aria-expanded')]));
    this.shadowRoot.innerHTML=`<style>${UI_CSS}${CSS}</style><ha-card>${navigation({label:'Wetteranalyse',items:[{id:'overview',label:'Verlauf'},{id:'statistics',label:'Statistik'}],active:this.page,settings:true,help:true})}<main><div class="wa-title"><div><h3>${esc(title)}</h3><small>${esc(this._data?.name||this._sensors.find(s=>s.entity_id===this.settings.entity)?.name||'Temperatur aus deinem Sensor')}</small></div>${button({label:'Aktualisieren',action:'reload',compact:true,disabled:this._busy})}</div>${this._error&&this.page!=='settings'?notice(this._error,{error:true}):''}${body}<div class="wa-quality">${quality}</div></main></ha-card>`;
    for(const [id,expanded] of collapsed){const content=this.shadowRoot.getElementById(id);const control=[...this.shadowRoot.querySelectorAll('[data-ui="collapse"]')].find(el=>el.getAttribute('aria-controls')===id);if(content&&control){content.hidden=expanded==='false';control.setAttribute('aria-expanded',expanded);control.querySelector('.chevron')?.classList.toggle('expanded',expanded==='true');}}
  }
}

class WeatherAnalysisCardEditor extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});}
  setConfig(config){this.config={card_id:crypto.randomUUID(),period:'today',title:'Wetteranalyse',...config};this.render();}
  set hass(hass){this._hass=hass;this.render();}
  render(){if(!this.config)return;const c=this.config;const sensors=Object.values(this._hass?.states||{}).filter(s=>s.entity_id.startsWith('sensor.')&&['°C','°F','K'].includes(s.attributes.unit_of_measurement));
    this.shadowRoot.innerHTML=`<style>${UI_CSS}</style>${field({id:'title',label:'Anzeigename',value:c.title})}${selectField({id:'entity',label:'Thermometer (muss in Weather Analysis eingerichtet sein)',value:c.entity||'',options:[{value:'',label:'In der Karte auswählen'},...sensors.map(s=>({value:s.entity_id,label:s.attributes.friendly_name||s.entity_id}))]})}${selectField({id:'period',label:'Startansicht',value:c.period,options:PERIODS.filter(([id])=>id!=='custom').map(([value,label])=>({value,label}))})}${field({id:'card_id',label:'Karten-ID',value:c.card_id,hint:'Für unabhängige Einstellungen eine eigene ID verwenden.'})}`;
    this.shadowRoot.onchange=event=>{const key=event.target.id;if(!['title','entity','period','card_id'].includes(key))return;this.config={...this.config,[key]:event.target.value};this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this.config},bubbles:true,composed:true}));};
  }
}
if(!customElements.get('weather-analysis-card'))customElements.define('weather-analysis-card',WeatherAnalysisCard);
if(!customElements.get('weather-analysis-card-editor'))customElements.define('weather-analysis-card-editor',WeatherAnalysisCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==='weather-analysis-card'))window.customCards.push({type:'weather-analysis-card',name:'Wetteranalyse',description:'Temperaturverlauf, Kennzahlen und Vergleiche deines Thermometers',preview:true});
