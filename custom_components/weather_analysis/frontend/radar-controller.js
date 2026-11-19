import {radarMap,updateRadarMap,notice,panelHeader,escapeHtml as esc} from './family-ui/1.13.0/family-ui.js';

/** App-owned location, data and playback, with the shared radar UI. */
export const RadarController=Base=>class extends Base {
  _clearRadar(){this._stopRadar();this._radar=null;this._radarError=null;this._radarFrameError='';this._radarBaseError='';this._radarImages=new Map();this._radarCache=new Map();this._radarBase='';this._radarLegend='';this._radarImage='';this._radarFrameBusy=false;this._radarSelection=(this._radarSelection||0)+1;}
  _stopRadar(){clearTimeout(this._radarTimer);this._radarTimer=null;this._radarPlaying=false;}
  _radarConnect(){
    this._radarInput ||= event=>{if(event.target.matches('.fui-radar input[type="range"]')){this._stopRadar();this._showRadarFrame(Number(event.target.value));}};
    this.shadowRoot.addEventListener('input',this._radarInput);
  }
  _radarDisconnect(){this._request++;this._busy=false;this._clearRadar();this.shadowRoot.removeEventListener('input',this._radarInput);}
  _radarOptions(){return {id:'wa-radar',frames:this._radar?.frames||[],index:this._radarIndex||0,baseImage:this._radarBase,radarImage:this._radarImage,legendImage:this._radarLegend,playing:this._radarPlaying,busy:this._radarFrameBusy,error:this._radarFrameError||this._radarBaseError||'',now:this._radar?.now,zoom:this._radarZoom??1};}
  _paintRadar(){const root=this.shadowRoot.querySelector('#wa-radar');if(root)updateRadarMap(root,this._radarOptions());}
  _refreshRadarIfDue(now=Date.now()/1000){
    if(this.page==='radar'&&!this._busy&&!this._radarPlaying&&(!this._radar||now-this._radar.now>=300))return this._fetchRadar();
  }
  _radarKey(index){const frame=this._radar.frames[index];return this._radar.context+'|'+frame.time+'|'+frame.reference;}
  async _fetchRadar(){
    if(!this._ready||!this._hass||this._busy)return;
    const request=++this._request;this._busy=true;this._stopRadar();this._radarError=null;
    this.render();
    try{
      const result=await this._hass.callWS({type:'weather_analysis/radar',zoom:this._radarZoom??1,...(this._browserCoordinates||{})});
      if(request!==this._request||this.page!=='radar'||!this.isConnected)return;
      const previous=this._radar,selected=previous?.frames?.[this._radarIndex||0];
      const followLatest=selected?.kind==='observation'&&selected.time===previous.latest;
      const same=previous?.status==='ok'&&result.radar?.status==='ok'&&previous.context===result.radar.context;
      if(!same)this._clearRadar();else {this._radarImages=new Map();this._radarSelection=(this._radarSelection||0)+1;}
      this._location=result.location;this._radarCredits=result.credits;this._radar=result.radar;this._radarError=result.radar_error;
      this._locationError=!result.location.position_available&&result.location.via!=='home_wifi'?'Kein GPS-Standort verfügbar. Regenradar für Böhl-Iggelheim.':null;
      if(result.location.via==='home_wifi')this._pauseGPSForHomeWifi();this._gpsSignature=this._positionSignature();
      this._busy=false;this.render();
      if(this._radar?.status!=='ok')return;
      const token=this._radar.token;
      const current=()=>this.page==='radar'&&token===this._radar?.token&&this.isConnected;
      const asset=async(kind,assign)=>{try{const r=await this._hass.callWS({type:'weather_analysis/radar_image',token,kind,background:kind==='legend'});if(current()){this[assign]=r.image;this._paintRadar();}}catch(error){if(current()&&kind==='base'){this._radarBaseError='Kartengrundlage nicht verfügbar. Bitte aktualisieren.';this._paintRadar();}}};
      if(!this._radarBase)asset('base','_radarBase');
      const latest=Math.max(0,this._radar.frames.findLastIndex(f=>f.kind==='observation'));
      const retained=same&&!followLatest&&selected?this._radar.frames.findIndex(f=>f.time===selected.time):-1;
      const chosen=retained>=0?retained:latest;
      await this._showRadarFrame(chosen);
      if(!current())return;
      if(!this._radarLegend)asset('legend','_radarLegend');
      // Fetch neighbours first; displayed frames have reserved server capacity.
      const order=this._radar.frames.map((_,i)=>i).sort((a,b)=>Math.abs(a-chosen)-Math.abs(b-chosen));let next=0;
      const preload=async()=>{while(current()&&next<order.length){const index=order[next++];try{await this._radarFrame(index,true);}catch{} }};
      preload();preload();
    }catch(error){if(request===this._request){this._clearRadar();this._radarError=error.message||'Regenradar konnte nicht geladen werden.';}}
    finally{if(request===this._request){this._busy=false;this.render();}}
  }
  _radarFrame(index,background=false){
    const token=this._radar.token,key=this._radarKey(index),cache=this._radarCache||=new Map();
    if(cache.has(key)){const image=cache.get(key);cache.delete(key);cache.set(key,image);return Promise.resolve(image);}
    this._radarImages ||= new Map();
    if(!this._radarImages.has(index)){
      const images=this._radarImages;
      images.set(index,this._hass.callWS({type:'weather_analysis/radar_image',token,kind:'frame',index,background}).then(r=>{cache.set(key,r.image);while(cache.size>96)cache.delete(cache.keys().next().value);return r.image;}).catch(error=>{images.delete(index);throw error;}));
    }
    return this._radarImages.get(index);
  }
  async _showRadarFrame(index){
    if(this.page!=='radar'||this._radar?.status!=='ok')return;
    index=Math.max(0,Math.min(this._radar.frames.length-1,Math.round(index)));
    const selection=this._radarSelection=(this._radarSelection||0)+1,token=this._radar.token;
    const current=()=>selection===this._radarSelection&&token===this._radar?.token&&this.page==='radar'&&this.isConnected;
    const cached=this._radarCache?.get(this._radarKey(index));
    if(cached){this._radarIndex=index;this._radarFrameBusy=false;this._radarFrameError='';this._radarImage=cached;this._paintRadar();return;}
    this._radarIndex=index;this._radarFrameBusy=true;this._radarFrameError='';this._radarImage='';this._paintRadar();
    try{const image=await this._radarFrame(index);if(current())this._radarImage=image;}
    catch(error){if(current()){this._radarFrameError=error.message||'Radarbild nicht verfügbar.';this._stopRadar();}}
    finally{if(current()){this._radarFrameBusy=false;this._paintRadar();}}
  }
  async _radarAction(action){
    if(action==='radar-play'){
      if(this._radarPlaying){this._stopRadar();this._paintRadar();return;}
      this._radarPlaying=true;this._paintRadar();
      const token=this._radar?.token;
      const tick=async index=>{if(!this._radarPlaying||this.page!=='radar'||token!==this._radar?.token)return;
        await this._showRadarFrame(index);
        if(!this._radarPlaying||token!==this._radar?.token)return;
        if(index>=this._radar.frames.length-1){this._stopRadar();this._paintRadar();return;}
        this._radarTimer=setTimeout(()=>tick(index+1),700);
      };tick(0);return;
    }
    this._stopRadar();
    if(action==='radar-zoom-in'||action==='radar-zoom-out'){
      this._radarZoom=Math.max(0,Math.min(3,(this._radarZoom??1)+(action==='radar-zoom-in'?1:-1)));this._clearRadar();await this._fetchRadar();return;
    }
    const index=action==='radar-now'?Math.max(0,this._radar.frames.findLastIndex(f=>f.kind==='observation')):(this._radarIndex||0)+(action==='radar-previous'?-1:1);
    await this._showRadarFrame(index);
  }
  _radarView(){
    const title=this._location?.name||'Standort wird ermittelt …';
    let content=this._radarError?notice(this._radarError,{error:true}):this._radar?.status==='outside'?notice('Für diesen Standort außerhalb des DWD-Radargebiets stehen keine Radar- und Vorhersagebilder bereit.'):this._radar?.status==='ok'?radarMap(this._radarOptions()):notice('Regenradar wird geladen …');
    if(this._radar?.status==='ok'){
      const latest=new Intl.DateTimeFormat('de-DE',{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(this._radar.latest*1000));
      content+=notice('Letzte DWD-Messung: '+latest+' Uhr. Spätere Bilder sind Vorhersagen. Randbereiche des Radargebiets können ohne Daten sein.');
    }
    return panelHeader({title,menu:false,reload:false,save:false})+(this._locationError?notice(this._locationError):'')+content+`<p class="hint wa-forecast-source">Radar und Nowcast: <a href="${esc(this._radarCredits?.dwd||'#')}" target="_blank" rel="noopener noreferrer">DWD</a> · Karte: © <a href="${esc(this._radarCredits?.bkg||'#')}" target="_blank" rel="noopener noreferrer">BKG</a> ${new Date().getFullYear()} · <a href="${esc(this._radarCredits?.license||'#')}" target="_blank" rel="noopener noreferrer">dl-de/by-2-0</a> · <a href="${esc(this._radarCredits?.sources||'#')}" target="_blank" rel="noopener noreferrer">Datenquellen</a></p>`;
  }
};
