(function(){
const apps=window.ROYAL_APPS||[];const host=document.getElementById("catalog");const search=document.getElementById("search");const fam=document.getElementById("family-filter");
const families=[...new Set(apps.map(a=>a.family))];fam.innerHTML='<option value="">All 12 families</option>'+families.map(f=>`<option>${f}</option>`).join("");
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function draw(){let q=search.value.toLowerCase(),f=fam.value;let list=apps.filter(a=>(!f||a.family===f)&&[a.name,a.family,a.tag,a.desc].join(" ").toLowerCase().includes(q));host.innerHTML=list.map((a,i)=>`<a class="card" href="./${esc(a.id)}/"><div class="row"><div class="icon">${String(i+1).padStart(2,"0")}</div><span class="pill">${esc(a.family)}</span></div><h3>${esc(a.name)}</h3><div class="muted">${esc(a.tag)}</div><p>${esc(a.desc)}</p><div class="row"><span class="muted">Open app ↗</span><span class="pill">Frontend demo</span></div></a>`).join("");document.getElementById("count").textContent=list.length+" apps shown";}
search.addEventListener("input",draw);fam.addEventListener("change",draw);draw();
})();
