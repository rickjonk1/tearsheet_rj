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
