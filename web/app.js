const MONTHS = ["", "Januari","Februari","Maart","April","Mei","Juni","Juli",
  "Augustus","September","Oktober","November","December"];
const MON3 = ["","JAN","FEB","MRT","APR","MEI","JUN","JUL","AUG","SEP","OKT","NOV","DEC"];

const state = { teams: [], teamId: null, program: [], squad: [], selRow: null };
const $ = (s, r=document) => r.querySelector(s);
const el = (t, c, h) => { const e=document.createElement(t); if(c)e.className=c; if(h!=null)e.innerHTML=h; return e; };

async function api(path, opts){ const r = await fetch(path, opts); return r.json(); }
function toast(msg){ const t=$("#toast"); t.textContent=msg; t.hidden=false; clearTimeout(t._t);
  t._t=setTimeout(()=>t.hidden=true, 2200); }

function tier(pop, klass){
  if(klass===22||klass===23) return {c:"#e879f9", bg:"rgba(232,121,249,.13)", l:"NK"};
  if(pop>=45) return {c:"#fbbf24", bg:"rgba(251,191,36,.14)", l:"WorldTour"};
  if(pop>=20) return {c:"#37e08b", bg:"rgba(55,224,139,.13)", l:"Pro"};
  if(pop>=8)  return {c:"#5b9dff", bg:"rgba(91,157,255,.13)", l:"Continental"};
  return {c:"#8b95a9", bg:"rgba(139,149,169,.12)", l:"Nationaal"};
}
function stars(pop){ const n=Math.max(1,Math.min(5,Math.round(pop/20)));
  let s='<span class="pop">'; for(let i=1;i<=5;i++) s+=`<i class="${i<=n?'on':''}">★</i>`; return s+"</span>"; }
function initials(name){ const p=name.trim().split(/\s+/); return ((p[0]||"")[0]||"")+((p[p.length-1]||"")[0]||""); }

/* ---------- bootstrap ---------- */
async function boot(){
  const b = await api("/api/bootstrap");
  // desktop mode exposes window.pywebview -> show the native Open button
  if(window.pywebview) $("#btnOpen").hidden=false;
  if(!b.loaded){
    $("#topmeta").innerHTML=`<span style="color:var(--mut2)">Geen career geladen — open een .cdb</span>`;
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
    `<span style="color:var(--mut2)">${(b.path||'').split('/').pop()}</span>`;
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
    const dc = t.avgAbility>=76?"#fbbf24":t.avgAbility>=73?"#37e08b":t.avgAbility>=68?"#5b9dff":"#8b95a9";
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
  $("#calendar").innerHTML='<div class="skeleton">Seizoen laden…</div>';
  const d = await api("/api/team?id="+id);
  state.program=d.program; state.squad=d.squad;
  const t = state.teams.find(x=>x.id===id);
  $("#boardTitle").textContent = d.name;
  const withR = d.program.filter(p=>p.roster.length).length;
  $("#boardSub").textContent = `1 januari · start van het seizoen — ${d.program.length} koersen op de kalender`;
  $("#seasonStats").innerHTML =
    `<div class="chipstat"><div class="v">${d.program.length}</div><div class="l">Koersen</div></div>`+
    `<div class="chipstat"><div class="v">${withR}</div><div class="l">Ingevuld</div></div>`+
    `<div class="chipstat"><div class="v">${t?t.avgAbility:'–'}</div><div class="l">Gem. niveau</div></div>`;
  renderTeamCard(t, d);
  renderCalendar();
  renderEditorEmpty();
}

function renderTeamCard(t, d){
  if(!t){ $("#teamCard").innerHTML=""; return; }
  $("#teamCard").innerHTML = `
    <div class="tc">
      <h3>${t.name}</h3>
      <div class="tc-sub">${d.squad.length} renners in selectie</div>
      <div class="tc-stats">
        <div class="tc-stat"><div class="v">${t.avgAbility}</div><div class="l">Gem. niveau</div></div>
        <div class="tc-stat"><div class="v">${t.topAbility}</div><div class="l">Kopman</div></div>
      </div>
      <div class="tc-top"><div class="badge">${initials(t.topRider)}</div>
        <div><div style="font-size:13px;font-weight:650">${t.topRider}</div>
        <div style="font-size:11px;color:var(--mut)">Beste renner</div></div></div>
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
      const sep=el("div","month-sep");
      sep.innerHTML=`<span class="mname">${MONTHS[p.month]||'—'}</span><span class="mline"></span>
        <span class="mcount">${byMonth[p.month].length} koersen</span>`;
      box.appendChild(sep);
    }
    box.appendChild(raceCard(p));
  });
}

function raceCard(p){
  const c=el("div","race"+(p.row===state.selRow?" sel":""));
  const tt=tier(p.popularity, p.klass);
  const av = p.roster.slice(0,5).map(r=>`<span class="av" title="${r.name}">${initials(r.name)}</span>`).join("");
  const more = p.roster.length>5?`<span class="av more">+${p.roster.length-5}</span>`:"";
  c.innerHTML=`
    <div class="date"><div class="d">${String(p.day).padStart(2,'0')}</div><div class="m">${MON3[p.month]||''}</div></div>
    <div class="main">
      <div class="rn">${p.name}</div>
      <div class="meta">
        <span class="jersey" style="color:${tt.c};background:${tt.bg}">${tt.l}</span>
        ${stars(p.popularity)}
        ${p.objectives?`<span class="objtag">★ ${p.objectives} doel${p.objectives>1?'en':''}</span>`:''}
        ${p.warn?`<span class="warntag">⚠ ${p.warn}</span>`:''}
      </div>
    </div>
    <div class="right">
      <div class="avatars">${av}${more}</div>
      <div class="rostercount ${p.roster.length?'':'empty'}">${p.roster.length?p.roster.length+' renners':'leeg'}</div>
    </div>`;
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
  const tt=tier(p.popularity, p.klass);
  const cap = 8;
  body.innerHTML=`
    <div class="eh">
      <div class="en">${p.name}</div>
      <div class="ed"><span>${String(p.day).padStart(2,'0')} ${MONTHS[p.month]}</span>·
        <span class="jersey" style="color:${tt.c};background:${tt.bg}">${tt.l}</span></div>
    </div>
    <div class="esec">
      <div class="esec-title"><h4>Selectie</h4><span class="cnt">${p.roster.length}/${cap}</span></div>
      <div id="rosterList"></div>
      <button class="btn ghost autofill" id="autofill">⚡ Automatisch aanvullen (specialiteit)</button>
    </div>
    <div class="esec">
      <div class="esec-title"><h4>Suggesties · beste fit</h4></div>
      <div id="sugList"></div>
    </div>`;
  const rl=$("#rosterList");
  if(!p.roster.length) rl.innerHTML=`<div style="color:var(--mut2);font-size:12px;padding:6px 2px">Nog geen renners geselecteerd.</div>`;
  p.roster.slice().sort((a,b)=>b.fit-a.fit).forEach((r,i)=>rl.appendChild(riderRow(r,p,true,i===0)));
  const sl=$("#sugList");
  suggestions.slice(0,12).forEach(s=>sl.appendChild(riderRow(s,p,false,false)));
  $("#autofill").onclick=()=>autofill(p);
}

function estFit(s,p){ // client-side fallback (server gives fit for current roster only)
  return s.fit!=null?s.fit:0;
}

function riderRow(r,p,inRoster,isLead){
  const row=el("div","rider"+(inRoster?"":" sug")+(r.busy?" busy":""));
  const fit=Math.round(r.fit||0);
  const star = inRoster ? `<button class="objbtn ${r.obj?'on':''}" title="Doelkoers voor deze renner">${r.obj?'★':'☆'}</button>` : '';
  const warn = inRoster && r.warn ? '<span class="wdot" title="Overlapt met andere koers">⚠</span>' : '';
  const fitcell = r.busy
    ? `<div class="fitwrap"><span class="busytag">bezet</span></div>`
    : `<div class="fitwrap"><div class="fitbar"><i style="width:${Math.min(100,fit)}%"></i></div>
        <div class="fitval">${fit} fit</div></div>`;
  row.innerHTML=`
    <div class="rr-name">
      <div class="nm">${r.name} ${isLead?'<span class="leadtag">KOPMAN</span>':''}${warn}</div>
      <div class="sp">${r.specialty}</div>
    </div>
    <span class="abil">${r.ability}</span>
    ${fitcell}
    ${star}
    <button class="rr-act ${inRoster?'rm':''}">${inRoster?'−':'+'}</button>`;
  if(inRoster) row.querySelector(".objbtn").onclick=(e)=>{ e.stopPropagation(); toggleObjective(p,r); };
  row.querySelector(".rr-act").onclick=(e)=>{ e.stopPropagation();
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
    `<div class="loadrow head"><span>Renner</span><span class="num">Dagen</span><span>Belasting</span><span class="num">Doelen</span><span class="confpill">⚠</span></div>`+
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

/* ---------- seizoen opzetten: rollen + horizontale jaarplanner ---------- */
const setup={phase:1, roles:{}, data:null};
$("#btnSetup").onclick=()=>{ if(state.teamId==null) return toast("Kies eerst een ploeg");
  setup.phase=1; setup.roles={}; setup.data=null;
  state.squad.forEach((s,i)=>setup.roles[s.id]= i<3?'leader':(i<7?'co':'dom'));
  $("#setupModal").hidden=false; renderSetup(); };
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
async function buildSeason(){
  const {leaders,coleaders}=setupRoleArrays();
  $("#setupActions").innerHTML=`<span style="color:var(--mut)">Bezig…</span>`;
  const d=await api("/api/season-setup",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,leaders,coleaders,seed:7})});
  setup.data=d;
  // client-editable per-captain race selection, seeded from the engine
  setup.captainRaces={};
  d.captains.forEach(c=>setup.captainRaces[c.id]=new Set(c.races.map(r=>r.race)));
  setup.phase=2; renderSetup();
}
const MON3B=["","JAN","FEB","MRT","APR","MEI","JUN","JUL","AUG","SEP","OKT","NOV","DEC"];
function captainDays(c){
  const sel=setup.captainRaces[c.id];
  return c.candidates.filter(r=>sel.has(r.race)).reduce((a,r)=>a+1,0);
}
function renderPlanner(){
  $("#setupPhaseLabel").textContent="Stap 2 · Horizontale jaarplanner — klik koersen aan/uit";
  $("#setupRoles").hidden=true; const box=$("#setupPlanner"); box.hidden=false;
  const d=setup.data;
  let html=`<div class="planlegend">
    <span><i class="rchip big" style="display:inline-block"></i> Grote doelkoers</span>
    <span><i class="rchip" style="display:inline-block"></i> Gekozen koers</span>
    <span><i class="rchip ghost" style="display:inline-block"></i> Beschikbaar (klik om toe te voegen)</span>
    <span><i class="rchip camp" style="display:inline-block"></i> Trainingskamp</span></div>`;
  html+=`<div class="planner"><div class="planner-months"><div class="mh corner">Renner</div>`;
  for(let m=1;m<=12;m++) html+=`<div class="mh">${MON3B[m]}</div>`;
  html+=`</div>`;
  d.captains.forEach(c=>{
    const cls=c.role==='Leider'?'leader':'co';
    const sel=setup.captainRaces[c.id];
    const nsel=c.candidates.filter(r=>sel.has(r.race)).length;
    const recon=new Set(c.recons||[]);
    html+=`<div class="planrow ${cls}"><div class="cap"><div class="cn">${c.name}</div>
      <div class="cmeta">${c.specialty} · <b>${nsel}</b> koersen</div>
      <div class="caprow"><span class="rolechip">${c.role.toUpperCase()}</span>
        <button class="capbtn" data-camp="${c.id}" title="Hoogtestage vóór grootste doel">🏔</button>
        <button class="capbtn ${recon.size?'on':''}" data-recon="${c.id}" title="Recon doelkoersen">👁</button>
      </div></div>`;
    // dynamic form: the 3 biggest chosen races become peak targets
    const peaks=new Set(c.candidates.filter(r=>sel.has(r.race)&&r.pop>=60)
      .sort((a,b)=>b.pop-a.pop).slice(0,3).map(r=>r.race));
    const byMonth={}; c.candidates.forEach(r=>(byMonth[r.month]=byMonth[r.month]||[]).push(r));
    for(let m=1;m<=12;m++){
      html+=`<div class="mcell">`;
      (byMonth[m]||[]).sort((a,b)=>a.day-b.day).forEach(r=>{
        const on=sel.has(r.race);
        const klass=on?(peaks.has(r.race)?'peak':(r.pop>=70?'big':'')):'ghost';
        const mark=(peaks.has(r.race)?'▲ ':'')+(recon.has(r.race)?'👁 ':'');
        html+=`<span class="rchip ${klass}" data-cap="${c.id}" data-race="${r.race}" title="${r.name} · fit ${Math.round(r.fit)}${peaks.has(r.race)?' · VORMPIEK':''}${recon.has(r.race)?' · RECON':''}${on?'':' — klik om toe te voegen'}">${mark}${String(r.day).padStart(2,'0')} ${r.name.slice(0,13)}</span>`;
      });
      (d.camps||[]).forEach(cp=>{ if(+String(cp.start).slice(4,6)===m)
        html+=`<span class="rchip camp" title="Trainingskamp ${cp.place}">🏔 ${cp.place.slice(0,12)}</span>`; });
      html+=`</div>`;
    }
    html+=`</div>`;
  });
  html+=`</div>`;
  box.innerHTML=html;
  box.querySelectorAll(".rchip[data-race]").forEach(ch=>ch.onclick=()=>{
    const cap=+ch.dataset.cap, race=+ch.dataset.race, sel=setup.captainRaces[cap];
    sel.has(race)?sel.delete(race):sel.add(race); renderPlanner();
  });
  box.querySelectorAll("[data-camp]").forEach(bt=>bt.onclick=()=>planAltitude(+bt.dataset.camp));
  box.querySelectorAll("[data-recon]").forEach(bt=>bt.onclick=()=>toggleRecon(+bt.dataset.recon));
  const total=d.captains.reduce((a,c)=>a+c.candidates.filter(r=>setup.captainRaces[c.id].has(r.race)).length,0);
  $("#setupInfo").innerHTML=`<b>${total}</b> doelkoersen · <span style="color:var(--grn)">▲ vormpiek</span> = automatisch rond de 3 grootste doelen · knechten auto op routeprofiel`;
  $("#setupActions").innerHTML=`<button class="btn ghost" id="setupBack">← Rollen</button>
    <button class="btn primary" id="setupApply">Toepassen &amp; opslaan in career</button>`;
  $("#setupBack").onclick=()=>{ setup.phase=1; renderSetup(); };
  $("#setupApply").onclick=applySeason;
}
function captainPeaks(c){
  const sel=setup.captainRaces[c.id];
  return c.candidates.filter(r=>sel.has(r.race)&&r.pop>=60).sort((a,b)=>b.pop-a.pop).slice(0,3);
}
async function planAltitude(capId){
  const c=setup.data.captains.find(x=>x.id===capId);
  const peaks=captainPeaks(c);
  if(!peaks.length) return toast("Kies eerst een grote doelkoers voor deze renner");
  const target=setup.data.year*10000+peaks[0].month*100+peaks[0].day;
  const r=await api("/api/plan-altitude",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,target})});
  if(!r.ok) return toast("Geen hoogtestage beschikbaar");
  const cm=await api(`/api/camps?team=${state.teamId}`); setup.data.camps=cm.booked;
  toast(`Hoogtestage ${r.camp.place} geboekt vóór ${peaks[0].name}`); renderPlanner();
}
async function toggleRecon(capId){
  const c=setup.data.captains.find(x=>x.id===capId);
  const peaks=captainPeaks(c).map(p=>p.race);
  const cur=new Set(c.recons||[]);
  const on=!peaks.every(r=>cur.has(r));   // if not all reconned -> turn on, else off
  for(const race of peaks){
    await api("/api/recon",{method:"POST",headers:{'Content-Type':'application/json'},
      body:JSON.stringify({rider:capId,race,on})});
  }
  c.recons = on ? [...new Set([...(c.recons||[]),...peaks])] : (c.recons||[]).filter(r=>!peaks.includes(r));
  toast(on?"Doelkoersen verkend (recon)":"Recon verwijderd"); renderPlanner();
}
async function applySeason(){
  const {leaders,coleaders}=setupRoleArrays();
  const captains={};
  Object.keys(setup.captainRaces).forEach(id=>captains[id]=[...setup.captainRaces[id]]);
  $("#setupActions").innerHTML=`<span style="color:var(--mut)">Opslaan…</span>`;
  const r=await api("/api/season-apply",{method:"POST",headers:{'Content-Type':'application/json'},
    body:JSON.stringify({team:state.teamId,leaders,coleaders,captains,save:true})});
  $("#setupModal").hidden=true; toast(`Seizoen opgeslagen · ${r.rosters} rosters`); refreshTeam();
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
  if(!booked.length){ box.innerHTML=`<div style="color:var(--mut2);font-size:12px;padding:8px 2px">Nog geen kampen geboekt.</div>`; return; }
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
  $("#genResult").innerHTML=`<div style="font-size:12px;color:var(--mut);margin-bottom:8px">${r.planned} koersen gepland</div>`+
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
    <div style="font-size:34px;font-weight:800;color:var(--gold)">${r.rosters}</div>
    <div style="color:var(--mut);font-size:12px">rosters gepland over ${r.teams} ploegen</div></div>`;
  toast(`Peloton gepland: ${r.teams} ploegen`); refreshTeam();
};

/* ---------- onboarding wizard ---------- */
const wiz={step:0, team:null};
const WIZ_STEPS=4;
function openWizard(){ wiz.step=0; wiz.team=null; $("#wizard").hidden=false; renderWizard(); }
function closeWizard(){ $("#wizard").hidden=true; if(wiz.team!=null) selectTeam(wiz.team);
  else if(state.teams.length) selectTeam(state.teams[0].id); }
function renderWizard(){
  $("#wizSteps").innerHTML=Array.from({length:WIZ_STEPS},(_,i)=>`<div class="s ${i<=wiz.step?'on':''}"></div>`).join("");
  const body=$("#wizBody");
  if(wiz.step===0){
    body.innerHTML=`<div class="wiz-hero">
      <div class="wiz-kicker">1 Januari · Seizoensstart</div>
      <h1>Welkom bij je nieuwe seizoen</h1>
      <p>We stellen samen een realistisch wielerseizoen samen — jouw ploeg én het hele peloton.
         In een paar stappen sta je klaar aan de start.</p></div>
      <div class="wiz-actions"><button class="wiz-skip" id="wizSkip">Overslaan</button>
        <div class="spacer"></div><button class="btn primary" id="wizNext">Beginnen →</button></div>`;
  }
  else if(wiz.step===1){
    body.innerHTML=`<div class="wiz-hero"><div class="wiz-kicker">Stap 1</div><h1>Kies je ploeg</h1>
      <p>Welke ploeg ga jij dit seizoen managen?</p></div>
      <input id="wizSearch" class="search" placeholder="Zoek ploeg…" autocomplete="off">
      <div class="wiz-teams" id="wizTeams"></div>
      <div class="wiz-actions"><button class="btn ghost" id="wizBack">← Terug</button>
        <div class="spacer"></div><button class="btn primary" id="wizNext" ${wiz.team==null?'disabled style="opacity:.4"':''}>Verder →</button></div>`;
    renderWizTeams(state.teams);
    $("#wizSearch").oninput=e=>renderWizTeams(state.teams.filter(t=>t.name.toLowerCase().includes(e.target.value.toLowerCase())));
  }
  else if(wiz.step===2){
    const tn=state.teams.find(t=>t.id===wiz.team);
    body.innerHTML=`<div class="wiz-hero"><div class="wiz-kicker">Stap 2</div><h1>Realistisch peloton</h1>
      <p>Genereer een dynamische kalender voor alle ploegen — gericht op de specialiteiten van
         hun renners. Elk seizoen is anders.</p></div>
      <div class="wiz-picked"><div class="badge">${tn?initials(tn.topRider):'?'}</div>
        <div><div style="font-weight:650">${tn?tn.name:''}</div>
        <div style="font-size:12px;color:var(--mut)">jouw ploeg</div></div></div>
      <div class="wiz-genbox" id="wizGenBox">
        <button class="btn gold" id="wizGen">✨ Genereer het seizoen (alle ploegen)</button>
        <div style="font-size:12px;color:var(--mut2);margin-top:10px">Optioneel — je kunt ook zelf plannen.</div>
      </div>
      <div class="wiz-actions"><button class="btn ghost" id="wizBack">← Terug</button>
        <div class="spacer"></div><button class="btn primary" id="wizNext">Verder →</button></div>`;
    $("#wizGen").onclick=async()=>{
      $("#wizGenBox").innerHTML='<div class="spinner"></div><div style="color:var(--mut);font-size:13px">Peloton plannen…</div>';
      const r=await api("/api/generate-all",{method:"POST",headers:{'Content-Type':'application/json'},
        body:JSON.stringify({seed:7,variety:.15})});
      $("#wizGenBox").innerHTML=`<div class="big">${r.rosters}</div>
        <div style="color:var(--mut);font-size:13px">rosters gepland over ${r.teams} ploegen ✓</div>`;
    };
  }
  else {
    const tn=state.teams.find(t=>t.id===wiz.team);
    body.innerHTML=`<div class="wiz-hero"><div class="wiz-kicker">Klaar</div><h1>Aan de start</h1>
      <p>Je seizoen staat klaar. Open koersen op de kalender, stel selecties samen op basis van
         fit, en markeer doelkoersen met een ster. Vergeet niet op te slaan.</p></div>
      <div class="wiz-actions"><div class="spacer"></div>
        <button class="btn primary" id="wizDone">Aan de slag met ${tn?tn.name:'je ploeg'} →</button></div>`;
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
  const nx=$("#wizNext"), bk=$("#wizBack"), sk=$("#wizSkip"), dn=$("#wizDone");
  if(nx) nx.onclick=()=>{ if(wiz.step===1&&wiz.team==null)return; wiz.step++; renderWizard(); };
  if(bk) bk.onclick=()=>{ wiz.step--; renderWizard(); };
  if(sk) sk.onclick=closeWizard;
  if(dn) dn.onclick=closeWizard;
}

/* ---------- save ---------- */
$("#btnSave").onclick=async()=>{ const r=await api("/api/save",{method:"POST",
  headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
  toast(r.ok?"Opgeslagen naar .cdb":"Opslaan mislukt"); };

boot();
