// Explore page: client-side filtering and sorting over data/trials.json
(function(){
  var tbl=document.getElementById('tbl'); if(!tbl) return;
  var tb=tbl.querySelector('tbody'), cnt=document.getElementById('count'), rows=[], key='st', dir=-1;
  var $=function(id){return document.getElementById(id)};
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function render(){
    var q=$('q').value.toLowerCase(), d=$('fd').value, g=$('fg').value, m=$('fm').value, p=$('fp').value, a=$('fa').checked;
    var f=rows.filter(function(r){
      return (!a||r.a)&&(!d||r.d.indexOf(d)>=0)&&(!g||r.g===g)&&(!m||r.m===m)&&(!p||r.p===p)&&
        (!q||(r.t+' '+r.sp+' '+r.n).toLowerCase().indexOf(q)>=0)});
    f.sort(function(x,y){var u=x[key],v=y[key];if(u==null||u==='')return 1;if(v==null||v==='')return -1;return (u>v?1:u<v?-1:0)*dir});
    cnt.textContent=f.length.toLocaleString()+' trials'+(f.length>500?' (showing first 500)':'');
    tb.innerHTML=f.slice(0,500).map(function(r){return '<tr><td><a href="trials/'+r.n+'.html">'+esc(r.t)+'</a><div class="meta">'+r.n+' · '+esc(r.sp)+(r.r?' · results posted':'')+'</div></td><td>'+esc(r.d)+'</td><td>'+esc(r.p)+'</td><td>'+esc(r.m)+'<div class="meta">'+esc(r.g)+'</div></td><td>'+esc(r.s)+'</td><td class="num">'+(r.e==null?'':r.e.toLocaleString())+'</td><td>'+esc(r.pc)+'</td></tr>'}).join('');
  }
  ['q','fd','fg','fm','fp','fa'].forEach(function(id){$(id).addEventListener('input',render);$(id).addEventListener('change',render)});
  tbl.querySelectorAll('th').forEach(function(th){th.addEventListener('click',function(){var k=th.dataset.k;dir=(key===k)?-dir:1;key=k;render()})});
  fetch('data/trials.json').then(function(r){return r.json()}).then(function(j){rows=j;render()});
})();
