(()=>{
  const state={words:[],text:'',speaking:false,offset:0,session:0,utterance:null,overlay:null,observer:null,rebuildTimer:null};
  const $=id=>document.getElementById(id);
  const norm=s=>(s||'').replace(/\s+/g,' ').trim();

  function ensureOverlay(){
    const stage=document.querySelector('.pageStage');
    if(!stage)return null;
    let overlay=stage.querySelector('.wordHighlightLayer');
    if(!overlay){
      overlay=document.createElement('div');
      overlay.className='wordHighlightLayer';
      Object.assign(overlay.style,{position:'absolute',inset:'0',pointerEvents:'none',overflow:'hidden',zIndex:'5'});
      stage.appendChild(overlay);
    }
    state.overlay=overlay;
    return overlay;
  }

  function clearHighlight(){
    if(state.overlay)state.overlay.replaceChildren();
    document.querySelectorAll('.spokenNow,.spokenSentence').forEach(el=>el.classList.remove('spokenNow','spokenSentence'));
  }

  function rectForRange(span,start,end){
    try{
      const node=[...span.childNodes].find(n=>n.nodeType===Node.TEXT_NODE);
      if(!node)return null;
      const len=node.textContent?.length||0;
      const a=Math.max(0,Math.min(start,len));
      const b=Math.max(a,Math.min(end,len));
      if(b<=a)return null;
      const range=document.createRange();
      range.setStart(node,a);range.setEnd(node,b);
      const rects=[...range.getClientRects()].filter(r=>r.width>1&&r.height>1);
      if(!rects.length)return null;
      return rects.reduce((acc,r)=>({left:Math.min(acc.left,r.left),top:Math.min(acc.top,r.top),right:Math.max(acc.right,r.right),bottom:Math.max(acc.bottom,r.bottom)}),{left:Infinity,top:Infinity,right:-Infinity,bottom:-Infinity});
    }catch{return null}
  }

  function drawWord(word){
    clearHighlight();
    const overlay=ensureOverlay();
    const stage=document.querySelector('.pageStage');
    if(!overlay||!stage||!word)return;
    const r=rectForRange(word.span,word.localStart,word.localEnd);
    if(!r)return;
    const sr=stage.getBoundingClientRect();
    const box=document.createElement('div');
    const padX=2,padY=1;
    Object.assign(box.style,{position:'absolute',left:`${r.left-sr.left-padX}px`,top:`${r.top-sr.top-padY}px`,width:`${r.right-r.left+padX*2}px`,height:`${r.bottom-r.top+padY*2}px`,background:'rgba(255,214,48,.58)',border:'1px solid rgba(210,160,0,.42)',borderRadius:'4px',boxSizing:'border-box'});
    overlay.appendChild(box);
  }

  function spatialKey(span){
    const r=span.getBoundingClientRect();
    return {x:r.left,y:r.top,w:r.width,h:r.height};
  }

  function sameVisualItem(a,b){
    const dx=Math.abs(a.x-b.x),dy=Math.abs(a.y-b.y),dw=Math.abs(a.w-b.w),dh=Math.abs(a.h-b.h);
    return dx<3&&dy<3&&dw<5&&dh<4;
  }

  function rebuildModel(){
    const layer=document.querySelector('.textLayer');
    if(!layer)return;
    const raw=[...layer.querySelectorAll('span')].map(span=>({span,text:norm(span.textContent),...spatialKey(span)})).filter(x=>x.text&&x.w>1&&x.h>1);
    const unique=[];
    for(const item of raw){
      const duplicate=unique.some(u=>u.text===item.text&&sameVisualItem(u,item));
      if(!duplicate)unique.push(item);
    }

    const medianH=unique.length?[...unique].map(x=>x.h).sort((a,b)=>a-b)[Math.floor(unique.length/2)]:12;
    const rowTol=Math.max(5,medianH*.7);
    unique.sort((a,b)=>{
      const ay=a.y+a.h/2,by=b.y+b.h/2;
      if(Math.abs(ay-by)>rowTol)return ay-by;
      return a.x-b.x;
    });

    const words=[];let text='';
    for(const item of unique){
      const source=item.span.textContent||'';
      const rx=/\S+/g;let m;
      while((m=rx.exec(source))){
        const token=m[0];
        if(text)text+=' ';
        const start=text.length;text+=token;
        words.push({start,end:text.length,span:item.span,localStart:m.index,localEnd:m.index+token.length,token,y:item.y,x:item.x});
      }
    }
    state.words=words;state.text=text;state.offset=0;
  }

  function wordAt(pos){
    if(!state.words.length)return null;
    let lo=0,hi=state.words.length-1;
    while(lo<=hi){const mid=(lo+hi)>>1,w=state.words[mid];if(pos<w.start)hi=mid-1;else if(pos>=w.end)lo=mid+1;else return w;}
    return state.words[Math.min(lo,state.words.length-1)]||null;
  }

  function setButton(active){const b=$('speak');if(b)b.textContent=active?'■ إيقاف':'▶ قراءة';}
  function stop(){
    state.session++;
    try{window.speechSynthesis?.cancel()}catch{}
    state.speaking=false;state.utterance=null;setButton(false);clearHighlight();
  }

  function speak(offset=0){
    if(!('speechSynthesis'in window)||!state.text)return;
    stop();
    const session=state.session;
    const start=Math.max(0,Math.min(offset,state.text.length));
    const raw=state.text.slice(start);const source=raw.trimStart();const lead=raw.length-source.length;
    if(!source){state.offset=0;return;}
    state.offset=start+lead;
    const u=new SpeechSynthesisUtterance(source);
    u.lang='en-US';
    const rate=parseFloat(($('rateBtn')?.textContent||'1').replace('x',''))||1;
    u.rate=rate;
    u.onstart=()=>{if(session!==state.session)return;state.speaking=true;setButton(true);drawWord(wordAt(state.offset));};
    u.onboundary=e=>{if(session!==state.session||typeof e.charIndex!=='number')return;state.offset=start+lead+e.charIndex;drawWord(wordAt(state.offset));};
    const finish=()=>{if(session!==state.session)return;state.speaking=false;state.utterance=null;state.offset=0;setButton(false);clearHighlight();try{speechSynthesis.cancel()}catch{}};
    u.onend=finish;u.onerror=finish;
    state.utterance=u;
    try{speechSynthesis.cancel();speechSynthesis.speak(u)}catch{finish()}
  }

  function scheduleRebuild(){clearTimeout(state.rebuildTimer);state.rebuildTimer=setTimeout(()=>{rebuildModel();clearHighlight()},80)}

  function bind(){
    const speakBtn=$('speak');
    if(speakBtn)speakBtn.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();state.speaking?stop():speak(state.offset||0)},true);
    const rateBtn=$('rateBtn');
    if(rateBtn)rateBtn.addEventListener('click',()=>{if(state.speaking)setTimeout(()=>speak(state.offset),0)},false);
    ['prev','next','back','replace'].forEach(id=>$(id)?.addEventListener('click',stop,true));
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop()});
    window.addEventListener('pagehide',stop);
    window.addEventListener('beforeunload',stop);

    const wrap=$('pdfWrap');
    if(wrap){
      state.observer=new MutationObserver(scheduleRebuild);
      state.observer.observe(wrap,{childList:true,subtree:true,characterData:true});
      scheduleRebuild();
    }
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
