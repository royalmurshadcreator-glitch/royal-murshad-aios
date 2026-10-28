(function(){
const app=window.ROYAL_APP||{};
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function render(){
document.title=(app.name||"Royal Murshad")+" | Royal Murshad";
$("#app-name").textContent=app.name||"Royal App";$("#app-tag").textContent=app.tag||"AI business workspace";
$("#app-desc").textContent=app.desc||"";$("#family").textContent=app.family||"Royal Murshad Apps";
$("#feature-list").innerHTML=(app.features||[]).map(x=>`<div class="feature">${esc(x)}</div>`).join("");
$("#app-mark").textContent=(app.name||"R").replace("Royal ","").slice(0,1).toUpperCase();
$("#task-label").textContent="Describe a task for "+(app.name||"this app");
$("#task").placeholder="Example: Prepare a weekly summary, list required information, or draft the next action…";
$("#run").addEventListener("click",()=>{
 const task=$("#task").value.trim();
 if(!task){$("#result").textContent="Enter a task first.";return;}
 const now=new Date().toLocaleString();
 $("#result").textContent=`DEMO WORKSPACE · ${now}\n\nApp: ${app.name}\nTask received: ${task}\n\nThis frontend is generated and interactive, but it is not yet connected to a verified business endpoint. No real record was created, no message was sent, and no external action was performed.\n\nNext integration step: map this app to an approved backend endpoint, validate its request/response contract, then add execution and verification tests.`;
});
$("#copy-link").addEventListener("click",async()=>{try{await navigator.clipboard.writeText(location.href);$("#link-status").textContent="Current app link copied."}catch(e){$("#link-status").textContent=location.href}});
}
if($("#app-name"))render();
})();
