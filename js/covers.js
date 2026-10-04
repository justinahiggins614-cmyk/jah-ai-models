/* ==== JAH deterministic AI identity-cover engine — jah-ai-models ====
   Zero storage, pure client-side SVG. (id, name, type) -> AI identity cover:
   abstract robot/face sigil in the AI's theme colors + name + stamp + 11-digit number.
   Names/numbers come ONLY from the page's canon data (ai-catalog.json lineage) —
   this engine never invents them; callers pass them in.
   Type -> theme color: system=cyan, persona=purple, sl=gold, domain=green.
   AICover.svg({id,name,type,stamp,phone,wide}) -> inline SVG string.
   AICover.thumb({id,name,type})                -> lazy placeholder <span>.
   AICover.lazy(scopeEl)                        -> IntersectionObserver fill for [data-cov]. */
(function(){
"use strict";
function xmur3(str){var h=1779033703^str.length;for(var i=0;i<str.length;i++){h=Math.imul(h^str.charCodeAt(i),3432918353);h=h<<13|h>>>19;}return function(){h=Math.imul(h^h>>>16,2246822507);h=Math.imul(h^h>>>13,3266489909);return (h^=h>>>16)>>>0;};}
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function wrap(t,n){var w=String(t||"Unnamed AI").split(/\s+/),L=[],c="",i;for(i=0;i<w.length;i++){if((c+" "+w[i]).trim().length>n){if(c)L.push(c);c=w[i];}else c=(c+" "+w[i]).trim();}if(c)L.push(c);return L.slice(0,2);}
var THEMES={
  system:["#0a1420","#060b12","#00f0ff","#9d7bff"],
  sig:   ["#0a1420","#060b12","#00f0ff","#9d7bff"],
  persona:["#1a1024","#0c0714","#c98aff","#ff7ab8"],
  sl:    ["#1f1808","#0f0b04","#ffd166","#ff9f43"],
  domain:["#0f1f14","#070f08","#7CFC00","#ffd166"]
};
function themeFor(t){return THEMES[t]||THEMES.system;}
/* ---- sigils, centered at (cx,cy), radius r ---- */
function sigilSystem(cx,cy,r,c1,c2){
  var s="",i;for(i=0;i<6;i++){var a=i*Math.PI/3;s+='<line x1="'+cx+'" y1="'+cy+'" x2="'+(cx+r*Math.cos(a)).toFixed(1)+'" y2="'+(cy+r*Math.sin(a)).toFixed(1)+'" stroke="'+c1+'" stroke-width="2.5" opacity="0.7"/>';
    s+='<circle cx="'+(cx+r*Math.cos(a)).toFixed(1)+'" cy="'+(cy+r*Math.sin(a)).toFixed(1)+'" r="'+(r*0.14)+'" fill="'+c2+'"/>';}
  s+='<polygon points="'+hexPts(cx,cy,r*0.55)+'" fill="none" stroke="'+c1+'" stroke-width="3"/>';
  s+='<circle cx="'+cx+'" cy="'+cy+'" r="'+(r*0.2)+'" fill="'+c1+'"/>';
  return s;
}
function hexPts(cx,cy,r){var p=[],k;for(k=0;k<6;k++){var a=Math.PI/3*k-Math.PI/6;p.push((cx+r*Math.cos(a)).toFixed(1)+","+(cy+r*Math.sin(a)).toFixed(1));}return p.join(" ");}
function sigilPersona(cx,cy,r,c1,c2){
  return '<ellipse cx="'+cx+'" cy="'+cy+'" rx="'+(r*0.72)+'" ry="'+(r*0.9)+'" fill="none" stroke="'+c1+'" stroke-width="3.5"/>'
  +'<ellipse cx="'+(cx-r*0.28)+'" cy="'+(cy-r*0.15)+'" rx="'+(r*0.16)+'" ry="'+(r*0.22)+'" fill="'+c1+'"/>'
  +'<ellipse cx="'+(cx+r*0.28)+'" cy="'+(cy-r*0.15)+'" rx="'+(r*0.16)+'" ry="'+(r*0.22)+'" fill="'+c1+'"/>'
  +'<path d="M'+(cx-r*0.34)+','+(cy+r*0.3)+' Q '+cx+','+(cy+r*0.62)+' '+(cx+r*0.34)+','+(cy+r*0.3)+'" stroke="'+c2+'" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
  +'<circle cx="'+cx+'" cy="'+(cy-r*1.05)+'" r="'+(r*0.1)+'" fill="'+c2+'"/>';
}
function sigilSL(cx,cy,r,c1,c2){
  return '<polygon points="'+cx+','+(cy-r)+' '+(cx+r*0.7)+','+cy+' '+cx+','+(cy+r)+' '+(cx-r*0.7)+','+cy+'" fill="none" stroke="'+c1+'" stroke-width="3.5"/>'
  +'<polygon points="'+cx+','+(cy-r*0.55)+' '+(cx+r*0.38)+','+cy+' '+cx+','+(cy+r*0.55)+' '+(cx-r*0.38)+','+cy+'" fill="'+c2+'" opacity="0.85"/>'
  +'<line x1="'+(cx-r)+'" y1="'+cy+'" x2="'+(cx+r)+'" y2="'+cy+'" stroke="'+c1+'" stroke-width="2" opacity="0.6"/>';
}
function sigilDomain(cx,cy,r,c1,c2){
  return '<path d="M'+cx+','+(cy-r)+' L '+(cx+r*0.8)+','+(cy-r*0.55)+' L '+(cx+r*0.8)+','+(cy+r*0.25)+' Q '+(cx+r*0.8)+','+(cy+r*0.8)+' '+cx+','+(cy+r)+' Q '+(cx-r*0.8)+','+(cy+r*0.8)+' '+(cx-r*0.8)+','+(cy+r*0.25)+' L '+(cx-r*0.8)+','+(cy-r*0.55)+' Z" fill="none" stroke="'+c1+'" stroke-width="3.5"/>'
  +'<circle cx="'+cx+'" cy="'+(cy-r*0.1)+'" r="'+(r*0.32)+'" fill="none" stroke="'+c2+'" stroke-width="3"/>'
  +'<circle cx="'+cx+'" cy="'+(cy-r*0.1)+'" r="'+(r*0.12)+'" fill="'+c2+'"/>';
}
function sigilFor(type){return type==="persona"?sigilPersona:type==="sl"?sigilSL:(type==="domain"?sigilDomain:sigilSystem);}
function svg(o){
  o=o||{};var id=String(o.id||"?"),name=o.name||"Unnamed AI",type=o.type||"system";
  var th=themeFor(type),h=xmur3(id+"::cov")();
  var W=o.wide?560:300,H=o.wide?220:300;
  var s='<svg viewBox="0 0 '+W+' '+H+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Identity cover for '+esc(name)+'">';
  s+='<defs><linearGradient id="aibg'+(h%999983)+'" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="'+th[0]+'"/><stop offset="1" stop-color="'+th[1]+'"/></linearGradient>'
    +'<radialGradient id="aigl'+(h%999983)+'" cx="50%" cy="50%" r="60%"><stop offset="0" stop-color="'+th[2]+'" stop-opacity="0.22"/><stop offset="1" stop-color="'+th[2]+'" stop-opacity="0"/></radialGradient></defs>';
  s+='<rect width="'+W+'" height="'+H+'" fill="url(#aibg'+(h%999983)+')"/>';
  var cx=o.wide?100:W/2,cy=o.wide?H/2:H*0.36,rr=o.wide?62:64;
  s+='<circle cx="'+cx+'" cy="'+cy+'" r="'+(rr*1.35)+'" fill="url(#aigl'+(h%999983)+')"/>';
  s+='<circle cx="'+cx+'" cy="'+cy+'" r="'+(rr*1.12)+'" fill="none" stroke="'+th[2]+'" stroke-width="2" opacity="0.8"/>';
  s+='<circle cx="'+cx+'" cy="'+cy+'" r="'+(rr*1.12)+'" fill="none" stroke="'+th[2]+'" stroke-width="6" opacity="0.15"/>';
  s+=sigilFor(type)(cx,cy,rr,th[2],th[3]);
  var tx=o.wide?190:0,tw=o.wide?W-200:0;
  if(o.wide){
    var lines=wrap(name,22),ty2=H/2-34;
    lines.forEach(function(ln,i){s+='<text x="'+tx+'" y="'+(ty2+i*26)+'" font-family="Arial,Helvetica,sans-serif" font-weight="bold" font-size="23" fill="#f2ede2">'+esc(ln)+'</text>';});
    var yy=ty2+lines.length*26+6;
    s+='<text x="'+tx+'" y="'+yy+'" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="13.5" fill="'+th[2]+'">'+esc(o.stamp||id)+'</text>';
    if(o.phone)s+='<text x="'+tx+'" y="'+(yy+20)+'" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="13.5" fill="'+th[3]+'">'+esc(o.phone)+'</text>';
    s+='<text x="'+tx+'" y="'+(yy+40)+'" font-family="Arial,sans-serif" font-size="11.5" letter-spacing="2" fill="#9b958a">'+esc(type.toUpperCase())+' · SIGNATURE AI</text>';
  }else{
    var lines2=wrap(name,20),ty3=H*0.36+rr+34;
    lines2.forEach(function(ln,i){s+='<text x="'+(W/2)+'" y="'+(ty3+i*23)+'" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="bold" font-size="20" fill="#f2ede2">'+esc(ln)+'</text>';});
    var y2=ty3+lines2.length*23+4;
    s+='<text x="'+(W/2)+'" y="'+y2+'" text-anchor="middle" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="12.5" fill="'+th[2]+'">'+esc(o.stamp||id)+'</text>';
    if(o.phone)s+='<text x="'+(W/2)+'" y="'+(y2+19)+'" text-anchor="middle" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="12.5" fill="'+th[3]+'">'+esc(o.phone)+'</text>';
  }
  s+='</svg>';return s;
}
function thumb(o){
  return '<span class="covthumb aicov" data-cov="1" data-cov-id="'+esc(o.id||"")+'" data-cov-title="'+esc(o.name||"")+'" data-cov-type="'+esc(o.type||"system")+'" data-cov-stamp="'+esc(o.stamp||"")+'" data-cov-phone="'+esc(o.phone||"")+'"><span class="covph" aria-hidden="true">◍</span></span>';
}
function fill(el){
  if(!el||el.getAttribute("data-cov-done"))return;
  el.setAttribute("data-cov-done","1");
  try{el.innerHTML=svg({id:el.getAttribute("data-cov-id"),name:el.getAttribute("data-cov-title"),type:el.getAttribute("data-cov-type"),stamp:el.getAttribute("data-cov-stamp"),phone:el.getAttribute("data-cov-phone")});}
  catch(e){el.innerHTML='<span class="covph">◍</span>';}
}
function lazy(scope){
  var root=scope||document;
  var els=root.querySelectorAll?root.querySelectorAll('[data-cov="1"]:not([data-cov-done])'):[];
  if(!els.length)return;
  if(typeof IntersectionObserver==="undefined"){for(var i=0;i<els.length;i++)fill(els[i]);return;}
  if(!lazy._io){lazy._io=new IntersectionObserver(function(es){for(var j=0;j<es.length;j++){if(es[j].isIntersecting){fill(es[j].target);lazy._io.unobserve(es[j].target);}}},{rootMargin:"240px"});}
  for(var i=0;i<els.length;i++)lazy._io.observe(els[i]);
}
window.AICover={svg:svg,thumb:thumb,lazy:lazy,fill:fill};
})();
