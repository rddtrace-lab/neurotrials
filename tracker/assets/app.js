// Explore page: client-side filtering and sorting over data/trials.json. Filter state is kept in the URL hash.
(function(){
  var tbl=document.getElementById('tbl'); if(!tbl) return;
  var tb=tbl.querySelector('tbody'), cnt=document.getElementById('count'), rows=[], key='st', dir=-1;
  var $=function(id){return document.getElementById(id)};
  var ids=['q','fd','fg','fm','fp','fa','fh'];
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function readHash(){
    var h=new URLSearchParams(location.hash.slice(1));
    ids.forEach(function(id){var el=$(id); if(!h.has(id)) return; if(el.type==='checkbox') el.checked=h.get(id)==='1'; else el.value=h.get(id)});
    if(h.has('sort')){key=h.get('sort'); dir=h.get('dir')==='1'?1:-1}
  }
  function writeHash(){
    var h=new URLSearchParams();
    ids.forEach(function(id){var el=$(id); if(el.type==='checkbox'){ if(el.checked!==el.defaultChecked) h.set(id,el.checked?'1':'0') } else if(el.value) h.set(id,el.value)});
    if(key!=='st'||dir!==-1){h.set('sort',key);h.set('dir',dir===1?'1':'-1')}
    var s=h.toString(); history.replaceState(null,'',s?'#'+s:location.pathname);
  }
  function mark(){tbl.querySelectorAll('th').forEach(function(th){th.setAttribute('aria-sort', th.dataset.k===key?(dir===1?'ascending':'descending'):'none')})}
  function render(){
    var q=$('q').value.toLowerCase(), d=$('fd').value, g=$('fg').value, m=$('fm').value, p=$('fp').value, a=$('fa').checked, hh=$('fh').checked;
    var f=rows.filter(function(r){
      return (!a||r.a)&&(!hh||!r.hv)&&(!d||r.d===d)&&(!g||r.g===g)&&(!m||r.m===m)&&(!p||r.p===p)&&
        (!q||(r.t+' '+r.sp+' '+r.n).toLowerCase().indexOf(q)>=0)});
    f.sort(function(x,y){var u=x[key],v=y[key];if(u==null||u==='')return 1;if(v==null||v==='')return -1;return (u>v?1:u<v?-1:0)*dir});
    cnt.textContent=f.length.toLocaleString()+' trials'+(f.length>500?' (showing first 500; narrow the filters or download the CSV)':'');
    tb.innerHTML=f.slice(0,500).map(function(r){
      var fl=(r.r?' · results posted':'')+(r.hv?' · healthy volunteers':'')+(r.x?' · completion date passed, status not updated':'');
      return '<tr><td><a href="trials/'+r.n+'.html">'+esc(r.t)+'</a><div class="meta">'+r.n+' · '+esc(r.sp)+fl+'</div></td><td>'+esc(r.d)+'</td><td>'+esc(r.p)+'</td><td>'+esc(r.m)+'<div class="meta">'+esc(r.g)+'</div></td><td>'+esc(r.s)+'</td><td class="num">'+(r.e==null?'':r.e.toLocaleString())+'</td><td>'+esc(r.st)+'</td><td>'+esc(r.pc)+'</td></tr>'}).join('');
    mark(); writeHash();
  }
  ids.forEach(function(id){$(id).addEventListener('input',render);$(id).addEventListener('change',render)});
  tbl.querySelectorAll('th').forEach(function(th){th.tabIndex=0;var go=function(){var k=th.dataset.k;dir=(key===k)?-dir:1;key=k;render()};
    th.addEventListener('click',go);th.addEventListener('keydown',function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();go()}})});
  readHash();
  fetch('data/trials.json').then(function(r){if(!r.ok) throw new Error(r.status);return r.json()}).then(function(j){rows=j;render()})
    .catch(function(){cnt.innerHTML='Could not load the trial data. <a href="data/trials.csv">Download the CSV</a> instead.'});
})();
// Dashboard: hover/focus tooltips on chart hit areas (data-tip = "title|line|line…"), built with textContent
(function(){
  var hits=document.querySelectorAll('.chart .hit'); if(!hits.length) return;
  var tip=document.createElement('div'); tip.className='viz-tip'; tip.hidden=true; document.body.appendChild(tip);
  function show(el,x,y){var parts=el.getAttribute('data-tip').split('|');tip.textContent='';
    var b=document.createElement('b');b.textContent=parts[0];tip.appendChild(b);
    parts.slice(1).forEach(function(p){var s=document.createElement('span');s.textContent=p;tip.appendChild(s)});
    tip.hidden=false;var w=tip.offsetWidth,h=tip.offsetHeight;
    tip.style.left=Math.min(x+14,window.innerWidth-w-8)+'px';tip.style.top=Math.max(8,y-h-10)+'px'}
  hits.forEach(function(el){
    el.addEventListener('pointermove',function(ev){show(el,ev.clientX,ev.clientY)});
    el.addEventListener('pointerleave',function(){tip.hidden=true});
    el.addEventListener('focus',function(){var r=el.getBoundingClientRect();show(el,r.left+r.width/2,r.top)});
    el.addEventListener('blur',function(){tip.hidden=true});
  });
})();
