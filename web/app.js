const MONTHS = ["", "Januari","Februari","Maart","April","Mei","Juni","Juli",
  "Augustus","September","Oktober","November","December"];
const MON3 = ["","JAN","FEB","MRT","APR","MEI","JUN","JUL","AUG","SEP","OKT","NOV","DEC"];

const state = { teams: [], teamId: null, program: [], squad: [], selRow: null };
const $ = (s, r=document) => r.querySelector(s);
const el = (t, c, h) => { const e=document.createElement(t); if(c)e.className=c; if(h!=null)e.innerHTML=h; return e; };

async function api(path, opts){ const r = await fetch(path, opts); return r.json(); }
function toast(msg){ const t=$("#toast"); t.textContent=msg; t.hidden=false; clearTimeout(t._t);
  t._t=setTimeout(()=>t.hidden=true, 2200); }

/* The classification jerseys are this product's legend. A race's colour says what
   KIND of race it is — never decoration. */
const JERSEY={gc:"var(--maillot)",mtn:"var(--pois)",spr:"var(--vert)",
              cls:"var(--pave)",itt:"var(--azzurro)"};
const DISC_LABEL={gc:"RONDE",mtn:"BERG",spr:"SPRINT",cls:"KASSEIEN",itt:"TIJDRIT"};

/* The elevation sawtooth — the most recognisable drawing in cycling. */
function profileSvg(points, disc, w=44, h=15){
  if(!points || !points.length) points=[.1,.1,.1,.1,.1];
  const step=w/(points.length-1);
  const pts=points.map((v,i)=>`${(i*step).toFixed(1)},${(h-1-v*(h-2)).toFixed(1)}`).join(" ");
  return `<svg class="prof" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">
    <polyline points="${pts}" fill="none" stroke="${JERSEY[disc]||'var(--ink-3)'}"
      stroke-width="1.2" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
}
/* A roadbook abbreviates, it never truncates mid-word. Keep the word that
   identifies the race to someone who follows cycling. */
const RACE_SHORT={"tour de france":"Tour","giro d'italia":"Giro","vuelta":"Vuelta",
  "paris-roubaix":"Roubaix","paris\u2013roubaix":"Roubaix",
  "ronde van vlaanderen":"Vlaanderen","milaan-sanremo":"Sanremo",
  "milaan\u2013sanremo":"Sanremo","luik-bastenaken-luik":"Luik","il lombardia":"Lombardia"};
function shortRace(name){
  const k=name.toLowerCase().trim();
  if(RACE_SHORT[k]) return RACE_SHORT[k];
  for(const [key,val] of Object.entries(RACE_SHORT)) if(k.startsWith(key)) return val;
  const drop=/^(ronde van|tour of|tour de|giro di|vuelta a|grand prix|gp)\s+/i;
  const stripped=name.replace(drop,"");
  return (stripped||name).split(/[\s\u2013-]+/)[0];
}
function raceClass(pop, klass){
  if(klass===22||klass===23) return "NK";
  if(pop>=45) return "WORLDTOUR"; if(pop>=20) return "PRO";
  if(pop>=8) return "CONTINENTAL"; return "NATIONAAL";
}
function initials(name){ const p=name.trim().split(/\s+/); return ((p[0]||"")[0]||"")+((p[p.length-1]||"")[0]||""); }

/* ---------- bootstrap ---------- */
async function boot(){
  const b = await api("/api/bootstrap");
  // desktop mode exposes window.pywebview -> show the native Open button
  if(window.pywebview) $("#btnOpen").hidden=false;
  if(!b.loaded){
    $("#topmeta").innerHTML=`<span style="color:var(--ink-4)">Geen career geladen — open een .cdb</span>`;
    $("#boardTitle").textContent="Open een career";
    $("#boardSub").textContent="Kies een PCM .cdb-bestand om te beginnen.";
    $("#btnOpen").hidden=false;
    return;
  }
  state.teams = b.teams;
  $("#topmeta").innerHTML =
    `<span><b>${b.counts.riders.toLocaleString('nl')}</b> renners</span>`+
    `<span><b>${b.counts.races}</b> koersen</span>`+
    `<span><b>${b.counts.teams}</b> ploegen</span>`+
    `<span style="color:var(--ink-4)">${(b.path||'').split('/').pop()}</span>`;
  renderTeams(state.teams);
  openWizard();
}

$("#btnOpen").onclick=async()=>{
  if(window.pywebview && window.pywebview.api){
    const r=await window.pywebview.api.pick();
    if(r&&r.ok){ toast("Career geladen"); boot(); }
  } else {
    const path=prompt("Pad naar .cdb-bestand:");
    if(path){ const r=await api("/api/open",{method:"POST",headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path})}); if(r.ok){ toast("Career geladen"); boot(); } }
  }
};

function renderTeams(list){
  const box = $("#teamList"); box.innerHTML="";
  list.forEach(t=>{
    const row = el("div","teamrow"+(t.id===state.teamId?" active":""));
    const dc = t.avgAbility>=76?"var(--maillot)":t.avgAbility>=73?"var(--ink-2)"
             :t.avgAbility>=68?"var(--ink-3)":"var(--rule-2)";
    row.innerHTML = `<span class="dot" style="background:${dc}"></span>
      <span class="tn">${t.name}</span><span class="tr">${t.avgAbility}</span>`;
    row.onclick = ()=>selectTeam(t.id);
    box.appendChild(row);
  });
}

$("#teamSearch").addEventListener("input", e=>{
  const q = e.target.value.toLowerCase();
  renderTeams(state.teams.filter(t=>t.name.toLowerCase().includes(q)));
});

/* ---------- team + calendar ---------- */
async function selectTeam(id){
  state.teamId=id; state.selRow=null;
  renderTeams(state.teams.filter(t=>{
    const q=$("#teamSearch").value.toLowerCase(); return !q||t.name.toLowerCase().includes(q);}));
  $("#calendar").innerHTML='<div class="cal-month">Seizoen laden…</div>';
  const d = await api("/api/team?id="+id);
  state.program=d.program; state.squad=d.squad;
  const t = state.teams.find(x=>x.id===id);
  $("#boardTitle").textContent = d.name;
  const withR = d.program.filter(p=>p.roster.length).length;
  $("#boardSub").textContent = `1 januari · start van het seizoen — ${d.program.length} koersen op de kalender`;
  $("#seasonStats").innerHTML =
    `<div><div class="v">${d.program.length}</div><div class="k">Koersen</div></div>`+
    `<div><div class="v">${withR}</div><div class="k">Ingevuld</div></div>`+
    `<div><div class="v">${t?t.avgAbility:'–'}</div><div class="k">Niveau</div></div>`;
  renderTeamCard(t, d);
  renderCalendar();
  renderEditorEmpty();
}

function renderTeamCard(t, d){
  if(!t){ $("#teamCard").innerHTML=""; return; }
  $("#teamCard").innerHTML = `
    <div class="teamcard">
      <h3>${t.name}</h3>
      <div class="tc-meta">${d.squad.length} renners in selectie</div>
      <div class="tc-stats">
        <div><div class="v">${t.avgAbility}</div><div class="k">Gem. niveau</div></div>
        <div><div class="v">${t.topAbility}</div><div class="k">Kopman</div></div>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        <span class="dossard lead">1</span>
        <div><div style="font-family:var(--serif);font-size:14px">${t.topRider}</div>
        <div class="meta" style="margin-top:2px">Beste renner</div></div>
      </div>
    </div>`;
}

function renderCalendar(){
  const box=$("#calendar"); box.innerHTML="";
  let curMonth=null;
  const byMonth={};
  state.program.forEach(p=>{ (byMonth[p.month]=byMonth[p.month]||[]).push(p); });
  state.program.forEach(p=>{
    if(p.month!==curMonth){
      curMonth=p.month;
      const sep=el("div","cal-month");
      sep.textContent=`${MONTHS[p.month]||'—'} · ${byMonth[p.month].length} koersen`;
      box.appendChild(sep);
    }
    box.appendChild(raceCard(p));
  });
}

function raceCard(p){
  const c=el("div",`race-row ${p.disc||'gc'}`+(p.popularity>=70?" major":"")
    +(p.row===state.selRow?" active":""));
  const bits=[DISC_LABEL[p.disc]||"", p.stages>1?`${p.stages} etappes`:"eendagskoers"];
  if(p.objectives) bits.push(`${p.objectives} doel${p.objectives>1?'en':''}`);
  if(p.warn) bits.push(`${p.warn} conflict${p.warn>1?'en':''}`);
  c.innerHTML=`
    <div class="date">${String(p.day).padStart(2,'0')} ${MON3[p.month]||''}</div>
    ${profileSvg(p.profile, p.disc)}
    <div>
      <div class="rname">${p.name}</div>
      <div class="rmeta">${bits.filter(Boolean).join(" · ")}</div>
    </div>
    <div class="rclass">${raceClass(p.popularity,p.klass)}</div>
    <div class="rsel ${p.roster.length?'on':''}">${p.roster.length?p.roster.length+"/8":"—"}</div>`;
  c.onclick=()=>openEditor(p.row);
  return c;
}

/* ---------- roster editor ---------- */
function renderEditorEmpty(){ $("#editorEmpty").hidden=false; $("#editorBody").hidden=true; }

async function openEditor(row){
  state.selRow=row; renderCalendar();
  const p=state.program.find(x=>x.row===row);
  $("#editorEmpty").hidden=true;
  const body=$("#editorBody"); body.hidden=false;
  // per-race fit + scheduling conflicts for the whole squad
  const res = await api(`/api/fit?team=${state.teamId}&race=${p.race}`);
  const fitMap = res.fit; const busy = new Set(res.busy);
  state.fitMap = fitMap; state.busy = busy;
  p.roster.forEach(r=>r.fit = fitMap[r.id] ?? r.fit);
  const inRoster=new Set(p.roster.map(r=>r.id));
  const suggestions = state.squad
    .filter(s=>!inRoster.has(s.id))
    .map(s=>({...s, fit: fitMap[s.id] ?? 0, busy: busy.has(s.id)}))
    .sort((a,b)=>(a.busy-b.busy) || (b.fit-a.fit));
  const cap = 8;
  body.innerHTML=`
    <div class="ed-head">
      <h2>${p.name}</h2>
      ${profileSvg(p.profile, p.disc, 96, 22)}
      <span class="meta">${String(p.day).padStart(2,'0')} ${MONTHS[p.month]} ·
        ${DISC_LABEL[p.disc]||''} · ${raceClass(p.popularity,p.klass)}</span>
    </div>
    <div class="kicker" style="display:flex;justify-content:space-between;margin-bottom:8px">
      <span>Selectie</span><span>${p.roster.length}/${cap}</span></div>
    <div id="rosterList" class="ed-list"></div>
    <div class="ed-foot"><button class="btn" id="autofill" style="width:100%">Automatisch aanvullen op profiel</button></div>
    <div class="kicker" style="margin:22px 0 8px">Beschikbaar · beste fit</div>
    <div id="sugList" class="ed-list"></div>`;
  const rl=$("#rosterList");
  if(!p.roster.length) rl.innerHTML=`<div style="color:var(--ink-4);font-size:12px;padding:6px 2px">Nog geen renners geselecteerd.</div>`;
  p.roster.slice().sort((a,b)=>b.fit-a.fit).forEach((r,i)=>rl.appendChild(riderRow(r,p,true,i===0)));
  const sl=$("#sugList");
  suggestions.slice(0,12).forEach(s=>sl.appendChild(riderRow(s,p,false,false)));
  $("#autofill").onclick=()=>autofill(p);
}

function estFit(s,p){ // client-side fallback (server gives fit for current roster only)
  return s.fit!=null?s.fit:0;
}

function riderRow(r,p,inRoster,isLead){
  const row=el("div","ed-rider"+(inRoster?" picked":"")+(r.busy?" busy":""));
  const fit=Math.round(r.fit||0);
  const star = inRoster ? `<button class="capbtn ${r.obj?'on':''}" title="Doelkoers voor deze renner">DOEL</button>` : '';
  const warn = inRoster && r.warn ? '<span class="wdot" title="Overlapt met een andere koers">!</span>' : '';
  row.innerHTML=`
    ${inRoster?`<span class="dossard${isLead?' lead':''}">${isLead?1:''}</span>`:''}
    <div style="flex:1;min-width:0">
      <div class="nm">${r.name}</div>
      <div class="sp">${r.specialty}${r.busy?' · bezet':''}</div>
    </div>
    ${warn}
    <span class="fit">${r.busy?'—':fit}</span>
    ${star}
    <button class="capbtn">${inRoster?'−':'+'}</button>`;
  const btns=row.querySelectorAll(".capbtn");
  if(inRoster) btns[0].onclick=(e)=>{ e.stopPropagation(); toggleObjective(p,r); };
  btns[btns.length-1].onclick=(e)=>{ e.stopPropagation();
    inRoster?removeRider(p,r.id):addRider(p,r.id); };
  return row;
}

async function toggleObjective(p,r){
  const res=await api("/api/objective",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({rider:r.id,race:p.race})});
  r.obj=res.added; await refreshTeam(); toast(res.added?"Doelkoers ingesteld":"Doelkoers verwijderd");
}

async function commitRoster(p){
  await api("/api/roster",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({row:p.row,riders:p.roster.map(r=>r.id)})});
}
async function refreshTeam(){ const keep=state.selRow;
  const d=await api("/api/team?id="+state.teamId); state.program=d.program; state.squad=d.squad;
  renderCalendar(); if(keep!=null && state.program.find(x=>x.row===keep)) openEditor(keep); }

async function addRider(p,id){
  const s=state.squad.find(x=>x.id===id); if(!s) return;
  p.roster.push({id:s.id,name:s.name,ability:s.ability,specialty:s.specialty,fit:s.fit||0});
  await commitRoster(p); await refreshTeam(); toast("Renner toegevoegd");
}
async function removeRider(p,id){
  p.roster=p.roster.filter(r=>r.id!==id);
  await commitRoster(p); await refreshTeam(); toast("Renner verwijderd");
}
async function autofill(p){
  const cap=8; const have=new Set(p.roster.map(r=>r.id));
  const fm=state.fitMap||{}; const busy=state.busy||new Set();
  const add=state.squad.filter(s=>!have.has(s.id) && !busy.has(s.id))   // skip conflicting riders
    .sort((a,b)=>((fm[b.id]||0)*1.4+b.ability)-((fm[a.id]||0)*1.4+a.ability));
  for(const s of add){ if(p.roster.length>=cap) break;
    p.roster.push({id:s.id,name:s.name,ability:s.ability,specialty:s.specialty,fit:fm[s.id]||0}); }
  await commitRoster(p); await refreshTeam(); toast("Selectie aangevuld (fit, zonder conflicten)");
}

/* ---------- load / conflicts overview ---------- */
$("#btnLoad").onclick=async()=>{ if(state.teamId==null) return toast("Kies eerst een ploeg");
  $("#loadModal").hidden=false;
  $("#loadTable").innerHTML='<div class="skeleton">Belasting berekenen…</div>';
  const d=await api("/api/load?team="+state.teamId);
  const maxDays=Math.max(1,...d.riders.map(r=>r.racedays));
  $("#loadSummary").textContent=`${d.riders.length} renners · ${d.conflicts} planningsconflict${d.conflicts===1?'':'en'} in het seizoen.`;
  $("#loadTable").innerHTML=
    `<div class="loadrow head"><span>Renner</span><span class="num">Dagen</span><span>Belasting</span><span class="num">Doelen</span><span class="num">Conflicten</span></div>`+
    d.riders.map(r=>{
      const pct=Math.round(r.racedays/maxDays*100);
      const over=r.racedays>85;
      return `<div class="loadrow">
        <span class="lname">${r.name}<small>${r.specialty} · ${r.races} koersen</small></span>
        <span class="num">${r.racedays}</span>
        <span><div class="loadbar"><i class="${over?'over':''}" style="width:${pct}%"></i></div></span>
        <span class="num">${r.objectives||'–'}</span>
        <span class="confpill ${r.conflicts?'bad':'ok'}">${r.conflicts||'·'}</span>
      </div>`;
    }).join("");
};
$("#loadClose").onclick=()=>$("#loadModal").hidden=true;

/* ---------- fietsbalans ---------- */
$("#btnBikes").onclick=()=>{ if(state.teamId==null&&!state.teams.length) return toast("Geen career geladen");
  $("#bikesModal").hidden=false; loadBikes(); };
$("#bikesClose").onclick=()=>$("#bikesModal").hidden=true;
async function loadBikes(){
  const d=await api("/api/bikes"); renderBikes(d.frames);
}
function renderBikes(frames){
  const box=$("#bikeList");
  const attr=(f,key,cls)=>`<div class="bk-attr ${cls}"><div class="bk-lbl">${{aero:'Aero',light:'Gewicht',confort:'Comfort'}[key]}</div>
    <div class="bk-step"><button data-b="${f.base}" data-k="${key}" data-d="-1">−</button>
      <span class="bk-val">${f[key]}</span>
      <button data-b="${f.base}" data-k="${key}" data-d="1">+</button></div></div>`;
  box.innerHTML=frames.map(f=>`<div class="bikerow">
    <div class="bk-name">${f.label}<small>${f.base} · ${f.count} modellen</small></div>
    ${attr(f,'aero','aero')}${attr(f,'light','light')}${attr(f,'confort','confort')}</div>`).join("");
  box.querySelectorAll(".bk-step button").forEach(bt=>bt.onclick=()=>stepBike(frames,bt.dataset.b,bt.dataset.k,+bt.dataset.d));
}
async function stepBike(frames,base,key,delta){
  const f=frames.find(x=>x.base===base);
  const nv=Math.max(0,Math.min(3,f[key]+delta));
  if(nv===f[key]) return;
  f[key]=nv;
  const r=await api("/api/bike-set",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({base,aero:f.aero,light:f.light,confort:f.confort})});
  renderBikes(r.frames);
}
$("#bikeRebalance").onclick=async()=>{
  const r=await api("/api/bike-rebalance",{method:"POST",headers:{'Content-Type':'application/json'},body:"{}"});
  renderBikes(r.frames); toast("Aero ↔ berg gebalanceerd");
};
$("#bikeSave").onclick=async()=>{ const r=await api("/api/save",{method:"POST",
  headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
  toast(r.ok?"Fietsbalans opgeslagen naar .cdb":"Opslaan mislukt"); };

/* ---------- seizoen opzetten: rollen + horizontale jaarplanner ---------- */
const setup={phase:1, roles:{}, data:null};
function openSetup(){
  if(state.teamId==null) return toast("Kies eerst een ploeg");
  setup.phase=1; setup.roles={}; setup.data=null;
  state.squad.forEach((s,i)=>setup.roles[s.id]= i<3?'leader':(i<7?'co':'dom'));
  $("#setupModal").hidden=false; renderSetup();
}
$("#btnSetup").onclick=openSetup;
$("#setupClose").onclick=()=>$("#setupModal").hidden=true;

function roleCounts(){ const c={leader:0,co:0,dom:0}; Object.values(setup.roles).forEach(r=>c[r]++); return c; }
function renderSetup(){
  const team=state.teams.find(t=>t.id===state.teamId);
  $("#setupTitle").textContent="Seizoen opzetten — "+(team?team.name:"");
  if(setup.phase===1){ renderRoles(); }
  else { renderPlanner(); }
}
function renderRoles(){
  $("#setupPhaseLabel").textContent="Stap 1 · Rollen";
  $("#setupRoles").hidden=false; $("#setupPlanner").hidden=true;
  const box=$("#roleList"); box.innerHTML="";
  state.squad.forEach(s=>{
    const role=setup.roles[s.id]||'dom';
    const card=el("div","rolecard "+role);
    const label={leader:'KOPMAN',co:'CO-LEIDER',dom:'KNECHT'}[role];
    card.innerHTML=`<div class="rc-name"><div class="n">${s.name}</div><div class="s">${s.specialty}</div></div>
      <span class="rc-abil">${s.ability}</span><span class="rc-badge">${label}</span>`;
    card.onclick=()=>cycleRole(s.id);
    box.appendChild(card);
  });
  const c=roleCounts();
  $("#setupInfo").innerHTML=`<b>${c.leader}</b> kopmannen · <b>${c.co}</b> co-leiders · <b>${c.dom}</b> knechten`;
  $("#setupActions").innerHTML=`<button class="btn primary" id="setupBuild">Bouw seizoen →</button>`;
  $("#setupBuild").onclick=buildSeason;
}
function cycleRole(id){
  const cur=setup.roles[id]||'dom';
  const next={dom:'co',co:'leader',leader:'dom'}[cur];
  if(next==='leader' && roleCounts().leader>=3) { setup.roles[id]='dom'; toast("Max 3 kopmannen"); }
  else setup.roles[id]=next;
  renderRoles();
}
function setupRoleArrays(){
  return {leaders:Object.keys(setup.roles).filter(k=>setup.roles[k]==='leader').map(Number),
          coleaders:Object.keys(setup.roles).filter(k=>setup.roles[k]==='co').map(Number)};
}
const MON3B=["","JAN","FEB","MRT","APR","MEI","JUN","JUL","AUG","SEP","OKT","NOV","DEC"];
async function buildSeason(){
  const {leaders,coleaders}=setupRoleArrays();
  setup.roleArrays={leaders,coleaders};
  $("#setupActions").innerHTML=`<span style="color:var(--ink-3)">Bezig…</span>`;
  const s=await api("/api/season-setup",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,leaders,coleaders,seed:7})});
  setup.captainRaces={};
  s.captains.forEach(c=>setup.captainRaces[c.id]=new Set(c.races.map(r=>r.race)));
  setup.collapseDom=true;
  await refreshPreview();
  setup.phase=2; renderSetup();
}
async function refreshPreview(){
  const {leaders,coleaders}=setup.roleArrays;
  const captains={}; Object.keys(setup.captainRaces).forEach(id=>captains[id]=[...setup.captainRaces[id]]);
  setup.preview=await api("/api/season-preview",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,leaders,coleaders,captains})});
}
const ROLE_ORDER=[["Leider","Kopmannen","leader"],["Co-leider","Co-leiders","co"],["Knecht","Knechten","dom"]];
function renderPlanner(){
  $("#setupPhaseLabel").textContent="Stap 2 · Jaarplanner";
  $("#setupRoles").hidden=true; const box=$("#setupPlanner"); box.hidden=false;
  const d=setup.preview; const campMonth={};
  (d.camps||[]).forEach(cp=>campMonth[+String(cp.start).slice(4,6)]=cp);
  let html=`<div class="pl2-legend">
    <span><i style="background:var(--maillot)"></i>ronde</span>
    <span><i style="background:var(--pois)"></i>berg</span>
    <span><i style="background:var(--vert)"></i>sprint</span>
    <span><i style="background:var(--pave)"></i>kasseien</span>
    <span><i style="background:var(--azzurro)"></i>tijdrit</span>
    <span>▲ vormpiek</span>
    <span class="pl2-hint">Klik een cel bij een kopman of co-leider om koersen te kiezen.</span></div>`;
  html+=`<div class="pl2"><div class="pl2-head"><div class="pl2-name">Renner</div>`;
  for(let m=1;m<=12;m++) html+=`<div class="pl2-mh${campMonth[m]?' camp':''}">${MON3B[m]}${campMonth[m]?' ·':''}</div>`;
  html+=`</div>`;
  ROLE_ORDER.forEach(([role,label,cls])=>{
    const list=d.riders.filter(r=>r.role===role);
    if(!list.length) return;
    const collapsed=role==='Knecht'&&setup.collapseDom;
    html+=`<div class="pl2-sec ${cls}" data-sec="${role}"><span>${label}</span>
      <span class="pl2-seccount">${list.length}</span>${role==='Knecht'?`<span class="pl2-toggle">${collapsed?'tonen ▾':'verbergen ▴'}</span>`:''}</div>`;
    if(collapsed) return;
    list.forEach(r=>{
      const editable=r.role!=='Knecht';
      html+=`<div class="pl2-row ${cls}"><div class="pl2-name">
        <div class="pl2-rn"><span class="dossard${r.role==='Leider'?' lead':''}">${r.no}</span>${r.name}</div>
        <div class="pl2-rm">${r.specialty} · ${r.races.length}× · ${r.days}d</div>`;
      if(editable) html+=`<div class="pl2-acts">
        <button class="capbtn" data-camp="${r.id}" title="Boek een hoogtestage vóór zijn grootste doel">HOOG</button>
        <button class="capbtn ${r.races.some(x=>x.recon)?'on':''}" data-recon="${r.id}" title="Verken zijn doelkoersen">VERK</button></div>`;
      html+=`</div>`;
      const byMonth={}; r.races.forEach(x=>(byMonth[x.month]=byMonth[x.month]||[]).push(x));
      for(let m=1;m<=12;m++){
        html+=`<div class="pl2-cell${editable?' edit':''}" ${editable?`data-rid="${r.id}" data-month="${m}"`:''}>`;
        (byMonth[m]||[]).sort((a,b)=>a.day-b.day).forEach(x=>{
          const cl=[x.disc||'gc', x.leader?'lead':'', x.peak?'peak':''].filter(Boolean).join(' ');
          const tip=[x.name, DISC_LABEL[x.disc]||'', x.peak?'vormpiek':'', x.recon?'verkend':'']
            .filter(Boolean).join(' · ');
          html+=`<span class="chip2 ${cl}" title="${tip}">
            <span class="d">${String(x.day).padStart(2,'0')}</span>
            <span class="n">${shortRace(x.name)}${x.recon?' ·':''}</span></span>`;
        });
        if(campMonth[m]&&editable) html+=`<span class="chip2 itt" title="Hoogtestage ${campMonth[m].place}">
          <span class="d">HOOG</span><span class="n">${campMonth[m].place}</span></span>`;
        html+=`</div>`;
      }
      html+=`</div>`;
    });
  });
  html+=`</div>`;
  box.innerHTML=html;
  box.querySelector('[data-sec="Knecht"] .pl2-toggle')?.addEventListener('click',()=>{
    setup.collapseDom=!setup.collapseDom; renderPlanner(); });
  box.querySelectorAll(".pl2-cell.edit").forEach(c=>c.onclick=e=>openCell(+c.dataset.rid,+c.dataset.month,c));
  box.querySelectorAll("[data-camp]").forEach(bt=>bt.onclick=e=>{e.stopPropagation();planAltitude(+bt.dataset.camp);});
  box.querySelectorAll("[data-recon]").forEach(bt=>bt.onclick=e=>{e.stopPropagation();toggleRecon(+bt.dataset.recon);});
  $("#setupInfo").innerHTML=`<b>${d.planned}</b> koersen gepland · knechten automatisch op routeprofiel`;
  $("#setupActions").innerHTML=`<button class="btn ghost" id="setupBack">← Rollen</button>
    <button class="btn primary" id="setupApply">Toepassen &amp; opslaan</button>`;
  $("#setupBack").onclick=()=>{ setup.phase=1; renderSetup(); };
  $("#setupApply").onclick=applySeason;
}
function closePopover(){ document.getElementById("cellPop")?.remove(); }
function openCell(rid,month,anchor){
  closePopover();
  const r=setup.preview.riders.find(x=>x.id===rid);
  const sel=setup.captainRaces[rid];
  const cands=r.candidates.filter(c=>c.month===month).sort((a,b)=>b.pop-a.pop);
  const pop=document.createElement("div"); pop.id="cellPop"; pop.className="cellpop";
  const render=()=>{
    pop.innerHTML=`<div class="cp-head">${r.name} · ${MON3B[month]}</div>`+
      (cands.length?cands.map(c=>`<div class="cp-row ${sel.has(c.race)?'on':''}" data-r="${c.race}">
        <span class="cp-check">${sel.has(c.race)?'✓':''}</span>
        <span class="cp-nm">${String(c.day).padStart(2,'0')} ${c.name}</span>
        <span class="cp-fit">${Math.round(c.fit)}</span></div>`).join("")
        :`<div class="cp-empty">Geen passende koersen deze maand</div>`)+
      `<button class="btn primary cp-done" id="cpDone">Klaar</button>`;
    pop.querySelectorAll(".cp-row").forEach(row=>row.onclick=()=>{
      const rc=+row.dataset.r; sel.has(rc)?sel.delete(rc):sel.add(rc); render();
    });
    pop.querySelector("#cpDone").onclick=async()=>{ closePopover(); await refreshPreview(); renderPlanner(); };
  };
  render();
  document.body.appendChild(pop);
  const rc=anchor.getBoundingClientRect();
  pop.style.top=Math.min(window.innerHeight-pop.offsetHeight-12,rc.bottom+6)+"px";
  pop.style.left=Math.min(window.innerWidth-pop.offsetWidth-12,rc.left)+"px";
  setTimeout(()=>document.addEventListener("mousedown",outside),0);
  function outside(e){ if(!pop.contains(e.target)){ document.removeEventListener("mousedown",outside);
    closePopover(); refreshPreview().then(renderPlanner); } }
}
function riderBiggestTarget(r){
  const big=r.races.filter(x=>x.leader&&x.pop>=55).sort((a,b)=>b.pop-a.pop)[0];
  return big?setup.preview.year*10000+big.month*100+big.day:null;
}
async function planAltitude(rid){
  const r=setup.preview.riders.find(x=>x.id===rid);
  const target=riderBiggestTarget(r);
  if(!target) return toast("Kies eerst een grote doelkoers voor deze renner");
  const res=await api("/api/plan-altitude",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,target})});
  if(!res.ok) return toast("Geen hoogtestage beschikbaar");
  await refreshPreview(); renderPlanner(); toast(`Hoogtestage ${res.camp.place} geboekt`);
}
async function toggleRecon(rid){
  const r=setup.preview.riders.find(x=>x.id===rid);
  const targets=r.races.filter(x=>x.peak).map(x=>x.race);
  if(!targets.length) return toast("Geen vormpiek-koersen om te verkennen");
  const on=!r.races.filter(x=>x.peak).every(x=>x.recon);
  for(const race of targets) await api("/api/recon",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({rider:rid,race,on})});
  await refreshPreview(); renderPlanner(); toast(on?"Doelkoersen verkend (recon)":"Recon verwijderd");
}
async function applySeason(){
  const {leaders,coleaders}=setupRoleArrays();
  const captains={};
  Object.keys(setup.captainRaces).forEach(id=>captains[id]=[...setup.captainRaces[id]]);
  $("#setupActions").innerHTML=`<span style="color:var(--ink-3)">Jouw seizoen toepassen…</span>`;
  const r=await api("/api/season-apply",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,leaders,coleaders,captains,save:false})});
  // AI-teams op de achtergrond, zelfde logica (jouw ploeg wordt niet overschreven)
  $("#setupActions").innerHTML=`<span style="color:var(--ink-3)">Peloton (AI) genereren…</span>`;
  const a=await api("/api/generate-all",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({exclude:state.teamId,seed:7,save:true})});
  $("#setupModal").hidden=true;
  toast(`Seizoen opgeslagen · jij ${r.rosters} rosters · ${a.teams} AI-ploegen`); refreshTeam();
}

/* ---------- vorm & training ---------- */
$("#btnForm").onclick=()=>{ if(state.teamId==null) return toast("Kies eerst een ploeg");
  $("#formModal").hidden=false; loadForm(); };
$("#formClose").onclick=()=>$("#formModal").hidden=true;
document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>{
  document.querySelectorAll(".tab").forEach(x=>x.classList.remove("on")); t.classList.add("on");
  const which=t.dataset.tab;
  $("#tabVorm").hidden=which!=="vorm"; $("#tabKampen").hidden=which!=="kampen";
  if(which==="kampen") loadCamps();
});

async function loadForm(){
  $("#formList").innerHTML='<div class="skeleton">Vorm laden…</div>';
  const d=await api("/api/form?team="+state.teamId);
  state.year=d.year;
  $("#formList").innerHTML=`<div class="formrow head"><span>Renner</span><span>Frisheid</span><span>Vermoeidheid</span><span>Vorm</span></div>`;
  d.riders.forEach(r=>$("#formList").appendChild(formRow(r)));
}
function fbar(v,cls){
  return `<div class="fctl"><div class="fbar ${cls||''}"><i style="width:${Math.min(100,Math.round(v))}%"></i></div>
    <span class="fv">${Math.round(v)}</span></div>`;
}
function formRow(r){
  const row=el("div","formrow");
  row.innerHTML=`<div class="fname">${r.name}<small>${r.specialty} · niv. ${r.ability}</small></div>`+
    fbar(r.freshness)+fbar(r.fatigue,"fat")+fbar(r.fit);
  return row;
}
$("#bulkFresh").onclick=async()=>{ await api("/api/form-bulk",{method:"POST",headers:{'Content-Type':'application/json'},
  body:JSON.stringify({team:state.teamId,action:"fresh"})}); toast("Iedereen fris & hersteld"); loadForm(); };
$("#bulkPeak").onclick=async()=>{ await api("/api/form-bulk",{method:"POST",headers:{'Content-Type':'application/json'},
  body:JSON.stringify({team:state.teamId,action:"peak"})}); toast("Iedereen in piekvorm"); loadForm(); };

async function loadCamps(){
  const d=await api(`/api/camps?team=${state.teamId}`); state.year=d.year;
  const sel=$("#campSelect");
  sel.innerHTML=d.camps.map(c=>`<option value="${c.id}">${'★'.repeat(c.stars)} ${c.place}${c.altitude?' (hoogte)':''} · ${c.open}–${c.close}</option>`).join("");
  renderCampList(d.booked);
}
function renderCampList(booked){
  const box=$("#campList");
  if(!booked.length){ box.innerHTML=`<div style="color:var(--ink-4);font-size:12px;padding:8px 2px">Nog geen kampen geboekt.</div>`; return; }
  box.innerHTML=booked.map(c=>{
    const s=String(c.start), e=String(c.end);
    const fmt=x=>`${x.slice(6,8)}/${x.slice(4,6)}`;
    return `<div class="camprow"><span>${c.place}</span><span class="cdate">${fmt(s)} – ${fmt(e)}</span></div>`;
  }).join("");
}
function parseDM(v){ const m=(v||"").match(/(\d{1,2})\D+(\d{1,2})/); if(!m) return null;
  const dd=String(m[1]).padStart(2,'0'), mm=String(m[2]).padStart(2,'0'); return `${state.year}${mm}${dd}`; }
$("#campBook").onclick=async()=>{
  const stage=+$("#campSelect").value, start=parseDM($("#campStart").value), end=parseDM($("#campEnd").value);
  if(!start||!end) return toast("Vul start en eind in als dd/mm");
  await api("/api/book-camp",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,stage,start:+start,end:+end})});
  toast("Kamp geboekt"); loadCamps();
};

/* ---------- generator modal ---------- */
$("#btnGenerate").onclick=()=>{ if(state.teamId==null) return toast("Kies eerst een ploeg");
  $("#genModal").hidden=false; };
$("#genClose").onclick=()=>$("#genModal").hidden=true;
$("#genVariety").oninput=e=>$("#genVarietyVal").textContent=e.target.value+"%";
async function runGen(apply){
  const seed=+$("#genSeed").value, variety=+$("#genVariety").value/100;
  $("#genResult").innerHTML='<div class="skeleton">Genereren…</div>';
  const r=await api("/api/generate",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,seed,variety,apply})});
  $("#genResult").innerHTML=`<div style="font-size:12px;color:var(--ink-3);margin-bottom:8px">${r.planned} koersen gepland</div>`+
    r.preview.slice(0,40).map(e=>`<div class="genrow"><span class="gd">${String(e.day).padStart(2,'0')}/${String(e.month).padStart(2,'0')}</span>
      <span class="gnm">${e.name}</span><span class="gl">${e.leader}</span></div>`).join("");
  if(apply){ toast(`Kalender toegepast: ${r.planned} koersen`); $("#genModal").hidden=true; refreshTeam(); }
}
$("#genPreview").onclick=()=>runGen(false);
$("#genApply").onclick=()=>runGen(true);
$("#genAll").onclick=async()=>{
  const seed=+$("#genSeed").value, variety=+$("#genVariety").value/100;
  $("#genResult").innerHTML='<div class="skeleton">Heel het peloton plannen…</div>';
  const r=await api("/api/generate-all",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({seed,variety})});
  $("#genResult").innerHTML=`<div style="text-align:center;padding:10px">
    <div class="big">${r.rosters}</div>
    <div style="color:var(--ink-3);font-size:12px">rosters gepland over ${r.teams} ploegen</div></div>`;
  toast(`Peloton gepland: ${r.teams} ploegen`); refreshTeam();
};

/* ---------- onboarding wizard ---------- */
const wiz={step:0, team:null};
const WIZ_STEPS=2;
function openWizard(){ wiz.step=0; wiz.team=null; $("#wizard").hidden=false; renderWizard(); }
function closeWizard(){ $("#wizard").hidden=true; if(wiz.team!=null) selectTeam(wiz.team);
  else if(state.teams.length) selectTeam(state.teams[0].id); }
async function wizToSetup(){ if(wiz.team==null) return; $("#wizard").hidden=true;
  await selectTeam(wiz.team); openSetup(); }
function renderWizard(){
  $("#wizSteps").innerHTML=Array.from({length:WIZ_STEPS},(_,i)=>`<div class="s ${i<=wiz.step?'on':''}"></div>`).join("");
  const body=$("#wizBody");
  if(wiz.step===0){
    body.innerHTML=`<div class="wiz-hero">
      <div class="wiz-kicker">1 Januari · Seizoensstart</div>
      <h1>Bouw je seizoen</h1>
      <p>Kies je ploeg en bepaal je kopmannen en co-leiders. Vandaaruit bouwt de planner hun
         schema én de knechten op — automatisch op basis van route en logica.</p></div>
      <div class="wiz-actions"><button class="wiz-skip" id="wizSkip">Later</button>
        <div class="spacer"></div><button class="btn primary" id="wizNext">Kies je ploeg →</button></div>`;
  } else {
    body.innerHTML=`<div class="wiz-hero"><div class="wiz-kicker">Stap 1</div><h1>Kies je ploeg</h1>
      <p>Welke ploeg ga jij dit seizoen managen?</p></div>
      <input id="wizSearch" class="search" placeholder="Zoek ploeg…" autocomplete="off">
      <div class="wiz-teams" id="wizTeams"></div>
      <div class="wiz-actions"><button class="btn ghost" id="wizBack">← Terug</button>
        <div class="spacer"></div><button class="btn primary" id="wizNext" ${wiz.team==null?'disabled style="opacity:.4"':''}>Naar leiders &amp; co-leiders →</button></div>`;
    renderWizTeams(state.teams);
    $("#wizSearch").oninput=e=>renderWizTeams(state.teams.filter(t=>t.name.toLowerCase().includes(e.target.value.toLowerCase())));
  }
  wireWizard();
}
function renderWizTeams(list){
  const box=$("#wizTeams"); box.innerHTML="";
  list.slice(0,120).forEach(t=>{
    const dc=t.avgAbility>=76?"#fbbf24":t.avgAbility>=73?"#37e08b":t.avgAbility>=68?"#5b9dff":"#8b95a9";
    const row=el("div","teamrow"+(t.id===wiz.team?" active":""));
    row.innerHTML=`<span class="dot" style="background:${dc}"></span><span class="tn">${t.name}</span><span class="tr">${t.avgAbility}</span>`;
    row.onclick=()=>{ wiz.team=t.id; renderWizard(); };
    box.appendChild(row);
  });
}
function wireWizard(){
  const nx=$("#wizNext"), bk=$("#wizBack"), sk=$("#wizSkip");
  if(nx) nx.onclick=()=>{ if(wiz.step===0){ wiz.step=1; renderWizard(); } else { wizToSetup(); } };
  if(bk) bk.onclick=()=>{ wiz.step=0; renderWizard(); };
  if(sk) sk.onclick=closeWizard;
}

/* ---------- save ---------- */
$("#btnSave").onclick=async()=>{ const r=await api("/api/save",{method:"POST",
  headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
  toast(r.ok?"Opgeslagen naar .cdb":"Opslaan mislukt"); };

boot();
