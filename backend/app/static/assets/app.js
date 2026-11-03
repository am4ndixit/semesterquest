/* Semester Quest — browser-native fallback UI. React/Vite source is in /frontend. */
const app = document.getElementById('app');
const API = '';
const state = {
  token: localStorage.getItem('sq_token') || '', user: null,
  theme: localStorage.getItem('sq_theme') || 'light', page: 'home',
  dashboard: null, worlds: [], selectedWorld: 'maths', selectedConcept: null,
  quiz: { questions: [], index: 0, selected: null, submitted: null, world: '' },
  py: { missions: [], mission: null, hint: 0, source: '', stdin: '', output: null },
  shell: { cwd: '/home/student', files: {}, git: {}, missions: [], output: '' },
  selectedTerminal: 'sh-01', materials: [], tasks: [], courses: [], gradeScale: null,
  tutorMessages: [], cards: [], cardIndex: 0, cardFlipped: false,
};

const esc = (v='') => String(v).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const nl = (v='') => esc(v).replace(/\n/g,'<br>');
const fmtDate = v => v ? new Date(v+'T00:00:00').toLocaleDateString(undefined,{month:'short',day:'numeric'}) : 'No date';

async function api(path, options={}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set('Authorization', 'Bearer '+state.token);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type','application/json');
  let res;
  try { res = await fetch(API+path, {...options, headers}); }
  catch (e) { throw new Error('Could not reach Semester Quest. Check that the server is running.'); }
  const data = (res.headers.get('content-type')||'').includes('application/json') ? await res.json() : await res.text();
  if (!res.ok) {
    if (res.status===401 && state.token) signOut(false);
    throw new Error(data?.detail || data?.message || `Request failed (${res.status})`);
  }
  return data;
}
function toast(message) {
  document.querySelector('.toast')?.remove();
  const el=document.createElement('div'); el.className='toast'; el.textContent=message; document.body.appendChild(el);
  setTimeout(()=>el.remove(),3200);
}
function applyTheme() {
  document.body.dataset.theme=state.theme;
  localStorage.setItem('sq_theme',state.theme);
}
function themeButton() {
  return `<button class="theme-btn" data-action="theme"><span class="theme-dot"></span>${state.theme==='light'?'Light mode':'Dark mode'}</button>`;
}
function brandMark() { return `<div class="brand-mark">SQ</div>`; }

function renderAuth(step='email', extra='') {
  applyTheme();
  const codeStep=step==='code';
  app.innerHTML=`<div class="auth-wrap">
    <div class="auth-theme">${themeButton()}</div>
    <section class="auth-card"><div class="auth-inner">
      <div class="brand-lockup">${brandMark()}<div><div class="brand-name">Semester Quest</div><div class="brand-sub">Your semester. Your adventure.</div></div></div>
      <div class="eyebrow">NEWTON SCHOOL OF TECHNOLOGY · PUNE</div>
      <h1>${codeStep?'Check your inbox':'Ready, explorer?'}</h1>
      <p>${codeStep?'Enter the 6-digit verification code sent to your ADYPU email.':'Sign in with your Pune ADYPU student email to open your learning worlds.'}</p>
      ${codeStep ? `<form id="verify-form"><input type="hidden" name="email" value="${esc(extra.email||'')}"/><div class="field"><label>6-digit verification code</label><input name="code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" placeholder="000000" required autofocus /></div>
        ${extra.dev_code?`<div class="notice"><strong>Development sign-in code:</strong> <span class="mono">${esc(extra.dev_code)}</span><br/>Email delivery is not configured. In production, configure SMTP and disable development codes.</div>`:''}
        <button class="btn full" type="submit">Verify & enter Home Base →</button><button class="btn ghost full" style="margin-top:10px" type="button" data-action="back-login">Use another email</button>
      </form>` : `<form id="login-form"><div class="field"><label>ADYPU student email</label><input type="email" name="email" placeholder="e26b07f0007@adypu.edu.in" autocomplete="username" required /></div>
        <div class="field"><label>Password</label><input type="password" name="password" placeholder="At least 8 characters" autocomplete="current-password" minlength="8" required /></div>
        <button class="btn full" type="submit">Continue with ADYPU email →</button>
        <div class="helper" style="margin-top:12px">Only addresses ending in <strong>@adypu.edu.in</strong> are accepted. A one-time code verifies mailbox access.</div>
      </form>`}
      <div class="auth-foot">A tiny bit of structure. A lot more curiosity. ✦</div>
    </div></section>
  </div>`;
}

const navGroups = [
  {label:'YOUR BASE',items:[['home','⌂','Home Base'],['atlas','✣','The Atlas'],['quiz','?','Quiz Arcade']]},
  {label:'PRACTICE LABS',items:[['python','{ }','Python Lab'],['terminal','⌘','Terminal Lab']]},
  {label:'YOUR LIBRARY',items:[['library','▤','My Library'],['tutor','✎','AI Study Buddy'],['flashcards','▧','Flashcards']]},
  {label:'YOUR PROGRESS',items:[['planner','☷','Study Planner'],['cgpa','∑','CGPA Studio']]},
];
function renderShell() {
  applyTheme();
  app.innerHTML=`<div class="shell">
    <aside class="sidebar" id="sidebar">
      <div class="side-brand">${brandMark()}<div><div class="brand-name">Semester Quest</div><div class="brand-sub">LEARN · PLAY · LEVEL UP</div></div></div>
      ${navGroups.map(g=>`<div class="nav-group"><div class="nav-label">${g.label}</div>${g.items.map(([id,ico,label])=>`<button class="nav-item ${state.page===id?'active':''}" data-page="${id}"><span class="nav-ico">${ico}</span>${label}</button>`).join('')}</div>`).join('')}
      <div class="side-spacer"></div>
      <div class="side-user"><div class="avatar">${esc((state.user?.name||'SQ').slice(0,2))}</div><div style="min-width:0;flex:1"><strong style="display:block;font-size:11px">${esc(state.user?.name||'Explorer')}</strong><div class="user-email">${esc(state.user?.email||'')}</div></div><button class="btn ghost tiny" data-action="logout" title="Sign out">↗</button></div>
    </aside>
    <main class="main">
      <header class="topbar"><div class="topbar-left"><button class="btn ghost tiny mobile-menu" data-action="menu">☰</button><div class="breadcrumb">Semester Quest <span class="muted">/</span> ${navGroups.flatMap(g=>g.items).find(x=>x[0]===state.page)?.[2]||'Home Base'}</div></div>
        <div class="topbar-right"><div class="streak-pill">✦ LEVEL ${Math.floor((state.user?.xp||0)/100)+1} · ${(state.user?.xp||0)} XP</div>${themeButton()}</div></header>
      <section class="content" id="page-content"><div class="empty">Opening your learning map…</div></section>
    </main>
  </div>`;
  loadPage();
}
function setContent(html) { const el=document.getElementById('page-content'); if(el) el.innerHTML=html; }
function pageHead(title,subtitle,kicker='YOUR LEARNING UNIVERSE',action='') {
  return `<div class="page-head"><div><div class="eyebrow">${kicker}</div><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
}

async function loadPage() {
  try {
    if(state.page==='home') return await renderHome();
    if(state.page==='atlas') return await renderAtlas();
    if(state.page==='quiz') return await renderQuiz();
    if(state.page==='python') return await renderPython();
    if(state.page==='terminal') return await renderTerminal();
    if(state.page==='library') return await renderLibrary();
    if(state.page==='tutor') return await renderTutor();
    if(state.page==='flashcards') return await renderFlashcards();
    if(state.page==='planner') return await renderPlanner();
    if(state.page==='cgpa') return await renderCgpa();
  } catch(e) { setContent(`<div class="notice">${esc(e.message)}</div>`); }
}

async function renderHome() {
  const d=await api('/api/dashboard'); state.dashboard=d; state.user=d.user;
  const quests=d.quests||[];
  setContent(`${pageHead(`Welcome back, ${esc(d.user.name||'explorer')}!`,'Your next small win is one click away.','HOME BASE')}
    <section class="hero"><div><div class="eyebrow">LEVEL ${d.level} · THE ADVENTURE CONTINUES</div><h2>Make this semester<br/>your playground.</h2><p>Learn a little, practise a little, and stack up XP as you go. Your three worlds are ready when you are.</p><button class="btn secondary" data-page="atlas">Explore the Atlas →</button></div><div class="hero-stat"><strong>${d.user.xp}</strong><span>Total experience points</span><div class="xp-row" style="color:#c7e2f6;margin-top:14px"><span>Level ${d.level}</span><span>${d.level_xp}/100 XP</span></div><div class="progress-track" style="background:#203f5d;border-color:#6b9cbe"><div class="progress-fill" style="width:${d.progress_percent}%;background:#addcff"></div></div></div></section>
    <div class="grid four" style="margin:20px 0"><div class="card stat-card"><div class="stat-icon">✦</div><div><div class="stat-value">${d.stats.correct_answers}</div><div class="stat-label">Correct answers</div></div></div><div class="card stat-card"><div class="stat-icon">▤</div><div><div class="stat-value">${d.stats.materials}</div><div class="stat-label">Class uploads</div></div></div><div class="card stat-card"><div class="stat-icon">▧</div><div><div class="stat-value">${d.stats.flashcards_due}</div><div class="stat-label">Cards due</div></div></div><div class="card stat-card"><div class="stat-icon">☷</div><div><div class="stat-value">${d.recent_tasks.filter(t=>!t.done).length}</div><div class="stat-label">Open tasks</div></div></div></div>
    <div class="card-head"><div class="card-title">Choose your world</div><button class="btn ghost tiny" data-page="atlas">View all →</button></div>
    <div class="grid three">${d.worlds.map((w,i)=>`<article class="card world-card"><div class="world-icon">${esc(w.icon)}</div><span class="chip">WORLD 0${i+1}</span><h3>${esc(w.title)}</h3><p>${esc(w.subtitle)}</p><div class="progress-track"><div class="progress-fill" style="width:${w.progress}%"></div></div><div class="world-bottom"><span>${w.done} / ${w.total_questions} questions mastered</span><button class="btn tiny secondary" data-action="world-quiz" data-world="${w.slug}">Play →</button></div></article>`).join('')}</div>
    <div class="grid two" style="margin-top:22px"><section class="card"><div class="card-head"><div class="card-title">Today's tiny quests</div><span class="chip blue">BONUS XP</span></div>${quests.map(q=>`<div class="list-row"><div class="quest-check ${q.done?'done':''}">${q.done?'✓':'·'}</div><div class="list-main" style="flex:1"><strong>${esc(q.title)}</strong><span>${q.done?'Already in the bag!':`+${q.xp} XP when complete`}</span></div><span class="chip">${q.done?'DONE':`+${q.xp} XP`}</span></div>`).join('')}</section>
    <section class="card"><div class="card-head"><div class="card-title">Your next steps</div><button class="btn ghost tiny" data-page="planner">Planner →</button></div>${d.recent_tasks.length?d.recent_tasks.slice(0,4).map(t=>`<div class="list-row"><div class="list-main" style="flex:1"><strong class="${t.done?'task-done':''}">${esc(t.title)}</strong><span>${esc(t.subject||'Personal')} · ${fmtDate(t.due_date)}</span></div><span class="chip">${esc(t.priority)}</span></div>`).join(''):'<div class="empty">Your study planner is clear. Add a task to make a plan.</div>'}</section></div>
    <section class="card" style="margin-top:22px"><div class="card-head"><div class="card-title">Badge shelf</div><span class="chip">${d.badges.filter(b=>b.earned).length} / ${d.badges.length} UNLOCKED</span></div><div class="badge-grid">${d.badges.map(b=>`<div class="badge-card ${b.earned?'earned':''}"><div class="badge-icon">${esc(b.icon)}</div><strong>${esc(b.title)}</strong><span>${esc(b.description)}</span></div>`).join('')}</div></section>`);
}

async function renderAtlas() {
  if(!state.worlds.length) state.worlds=await api('/api/worlds');
  const world=state.worlds.find(w=>w.slug===state.selectedWorld)||state.worlds[0];
  const progress=state.dashboard?.worlds?.find(w=>w.slug===world.slug)?.progress||0;
  setContent(`${pageHead('The Atlas','Pick a path, explore a concept, and learn at your own pace.','YOUR THREE WORLDS')}
    <div class="world-tabs">${state.worlds.map(w=>`<button class="tab-btn ${w.slug===world.slug?'active':''}" data-world-tab="${w.slug}">${esc(w.icon)} &nbsp;${esc(w.title)}</button>`).join('')}</div>
    <div class="card soft" style="margin-bottom:17px"><div class="card-head"><div><div class="eyebrow">${esc(world.subtitle)}</div><div class="card-title">${esc(world.title)}</div></div><span class="chip blue">STARTER CONCEPT MAP</span></div><p style="margin:0 0 11px">This is a starter map, not an official syllabus. Upload your faculty slides and notes in My Library to make your study sessions course-specific.</p><div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div><div class="xp-row"><span>Practice progress</span><span>${progress}%</span></div></div>
    <div class="concept-grid">${world.concepts.map((c,i)=>`<article class="concept" data-concept="${esc(c.id)}"><div class="eyebrow">NODE ${String(i+1).padStart(2,'0')} · ${esc(c.kind)}</div><h3>${esc(c.title)}</h3><p>${esc(c.description)}</p><div style="margin-top:12px"><span class="chip">OPEN CONCEPT ↗</span></div></article>`).join('')}</div>
    <div id="concept-detail" class="concept-detail" style="display:none"></div>`);
  document.querySelectorAll('[data-concept]').forEach(el=>el.addEventListener('click',()=>{
    const c=world.concepts.find(x=>x.id===el.dataset.concept); const panel=document.getElementById('concept-detail'); state.selectedConcept=c.id;
    panel.style.display='block'; panel.innerHTML=`<div class="card-head"><div><div class="eyebrow">CONCEPT NODE</div><div class="card-title">${esc(c.title)}</div></div><button class="btn tiny" data-action="concept-quiz" data-world="${world.slug}" data-topic="${esc(c.title)}">Practice this topic →</button></div><p>${esc(c.description)}</p><div class="notice">Faculty material: not linked yet. Upload class notes to My Library; the tutor will retrieve relevant text from your files.</div>`;
    panel.scrollIntoView({behavior:'smooth',block:'nearest'});
  }));
}

async function renderQuiz() {
  if(!state.quiz.questions.length || state.quiz.index>=state.quiz.questions.length) {
    state.quiz.questions=await api('/api/quiz/questions?limit=20'+(state.quiz.world?'&world='+encodeURIComponent(state.quiz.world):''));
    state.quiz.index=0; state.quiz.selected=null; state.quiz.submitted=null;
  }
  const q=state.quiz.questions[state.quiz.index];
  if(!q) { setContent(`${pageHead('Quiz Arcade','A quick challenge to check what is sticking.','PRACTICE MODE')}<div class="empty">No questions found for this filter yet. Try another world.</div><button class="btn" data-action="quiz-reset">Show all questions</button>`);return; }
  const submitted=state.quiz.submitted;
  setContent(`${pageHead('Quiz Arcade','One question at a time. Think it through, then lock in your answer.','PRACTICE MODE',`<button class="btn ghost tiny" data-action="quiz-reset">Reset quiz</button>`)}
    <div class="grid two"><section class="card"><div class="card-head"><span class="chip blue">${esc(q.world.toUpperCase())} · ${esc(q.difficulty)}</span><span class="muted small">QUESTION ${state.quiz.index+1} / ${state.quiz.questions.length}</span></div><div class="progress-track"><div class="progress-fill" style="width:${(state.quiz.index+1)/state.quiz.questions.length*100}%"></div></div><div class="question">${esc(q.prompt)}</div><div class="options">${q.options.map((op,i)=>`<button class="option ${state.quiz.selected===i?'selected':''} ${submitted&&i===submitted.correct_index?'correct':''} ${submitted&&state.quiz.selected===i&&!submitted.correct?'wrong':''}" data-option="${i}" ${submitted?'disabled':''}><span class="option-key">${String.fromCharCode(65+i)}</span><span>${esc(op)}</span></button>`).join('')}</div>
      ${submitted?`<div class="explanation"><strong>${submitted.correct?'Nice work! ✦':'Good try — learn from it.'}</strong><br/>${esc(submitted.explanation)}<div style="margin-top:9px" class="chip">+${submitted.xp} XP</div></div><button class="btn" style="margin-top:16px" data-action="quiz-next">${state.quiz.index===state.quiz.questions.length-1?'Finish round':'Next question'} →</button>`:`<button class="btn" style="margin-top:16px" data-action="quiz-submit" ${state.quiz.selected===null?'disabled':''}>Check answer</button>`}</section>
      <aside class="card soft"><div class="card-title">Tiny hint</div><p>Read the question twice. Identify exactly what it asks before choosing an option.</p><div class="notice">A correct answer earns +10 XP the first time you master it. Repeating a mastered question will still show the explanation, but won't farm XP.</div><div style="margin-top:14px"><button class="btn secondary" data-action="quiz-world" data-world="maths">Maths</button> <button class="btn secondary" data-action="quiz-world" data-world="sai">S&AI</button> <button class="btn secondary" data-action="quiz-world" data-world="psp">PSP</button></div></aside></div>`);
}

async function renderPython() {
  if(!state.py.missions.length) state.py.missions=await api('/api/python/missions');
  if(!state.py.mission) selectPythonMission(state.py.missions[0]);
  const m=state.py.missions.find(x=>x.id===state.py.mission)||state.py.missions[0];
  setContent(`${pageHead('Python Lab','Write code, run it in an isolated sandbox, and learn from the output.','BUILD WITH PYTHON')}
    <div class="lab-layout"><aside class="card"><div class="card-head"><div class="card-title">Mission board</div><span class="chip">${state.py.missions.length} LEVELS</span></div><div class="mission-list">${state.py.missions.map(x=>`<button class="mission-item ${x.id===m.id?'active':''}" data-py-mission="${x.id}"><strong>${esc(x.title)}</strong><span>${esc(x.topic)} · ${esc(x.difficulty)}</span></button>`).join('')}</div></aside>
    <section class="card"><div class="card-head"><div><div class="eyebrow">${esc(m.topic)} · ${esc(m.difficulty)}</div><div class="card-title">${esc(m.title)}</div></div><span class="chip blue">+25 XP</span></div><p>${esc(m.prompt)}</p><div class="notice">${esc(m.hints?.[state.py.hint]||'Try the mission first, then reveal a hint.')} <button class="btn ghost tiny" data-action="py-hint">${state.py.hint>=m.hints.length?'Hints shown':'Need a hint?'}</button></div>
      <div class="editor" style="margin-top:14px"><div class="editor-top"><span>main.py</span><span>PYTHON 3.13</span></div><textarea id="py-source" spellcheck="false" autocapitalize="off">${esc(state.py.source||m.starter||'')}</textarea><div class="editor-top"><span>stdin · one value per line</span><span>INPUT</span></div><textarea id="py-stdin" class="stdin" spellcheck="false" placeholder="Optional input for input()">${esc(state.py.stdin||'')}</textarea></div>
      <div style="display:flex;gap:9px;margin:13px 0"><button class="btn" data-action="py-run">▶ Run code</button><button class="btn secondary" data-action="py-check">Check mission</button><button class="btn ghost" data-action="py-reset">Reset</button></div>
      <div class="card-head"><div class="card-title">Output</div><span class="chip">SANDBOX</span></div><div class="output" id="py-output">${state.py.output?esc(state.py.output):'Run your code to see the output here.'}</div>
      <div class="notice" style="margin-top:13px">Safety note: code only runs inside Docker with no network, limited CPU/memory, and a read-only filesystem. Install Docker Desktop and run <span class="mono">docker pull python:3.13-alpine</span> to enable it. The app will not run code unsandboxed.</div>
    </section></div>`);
}
function selectPythonMission(m) { state.py.mission=m.id;state.py.hint=0;state.py.source=m.starter||'';state.py.stdin='';state.py.output=null; }

async function renderTerminal() {
  const shell=await api('/api/shell'); state.shell={...state.shell,...shell};
  const mission=state.shell.missions.find(x=>x.id===state.selectedTerminal)||state.shell.missions[0];
  const tree=Object.keys(state.shell.files||{}).filter(p=>p.startsWith('/home/student')).sort().map(p=>`${p.replace('/home/student','~')}${state.shell.files[p].type==='dir'?'/':''}`).join('\n');
  setContent(`${pageHead('Terminal Lab','A virtual Linux playground. Commands change this sandbox, never your computer.','COMMAND LINE QUESTS')}
    <div class="lab-layout"><aside class="card"><div class="card-head"><div class="card-title">Missions</div><span class="chip">6 QUESTS</span></div><div class="mission-list">${state.shell.missions.map(x=>`<button class="mission-item ${x.id===mission.id?'active':''}" data-sh-mission="${x.id}"><strong>${esc(x.title)}</strong><span>+${x.xp} XP · VIRTUAL SHELL</span></button>`).join('')}</div><button class="btn ghost tiny" style="margin-top:12px" data-action="shell-reset">Reset virtual files</button></aside>
    <section class="card"><div class="card-head"><div><div class="eyebrow">MISSION BRIEF</div><div class="card-title">${esc(mission.title)}</div></div><span class="chip blue">+${mission.xp} XP</span></div><p>${esc(mission.brief)}</p><div class="terminal-output" id="terminal-output">${state.shell.output?esc(state.shell.output):'Welcome to quest-shell 1.0\nType help to see available commands.\n\nstudent@quest:~$ '}</div><form id="terminal-form" class="terminal-line"><span class="mono small">student@quest:~$</span><input name="command" id="terminal-command" placeholder="try: ls -l" autocomplete="off" spellcheck="false"/><button class="btn tiny" type="submit">Run ↵</button></form>
      <div style="display:flex;gap:8px;margin-top:12px"><button class="btn secondary tiny" data-action="sh-check">Check mission</button><button class="btn ghost tiny" data-action="sh-help">Show help</button></div>
      <div class="grid two" style="margin-top:16px"><div class="card soft"><div class="card-title">File explorer</div><pre class="file-tree">${esc(tree||'~')}</pre></div><div class="card soft"><div class="card-title">Quick command ideas</div><div class="small muted" style="line-height:2">• <span class="mono">pwd</span> — current directory<br/>• <span class="mono">mkdir -p quest/src</span> — folders<br/>• <span class="mono">grep ERROR practice/log.txt</span><br/>• <span class="mono">git init</span> — start version control</div></div></div>
    </section></div>`);
}

async function renderLibrary() {
  state.materials=await api('/api/materials');
  setContent(`${pageHead('My Library','Upload lectures, notes and assignments. Your tutor can search their extracted text.','YOUR CLASS MATERIALS')}
    <div class="grid two"><section class="card"><div class="card-head"><div class="card-title">Add a class resource</div><span class="chip blue">MAX 20 MB</span></div><form id="upload-form"><div class="upload-box"><div style="font:700 27px var(--pixel);margin-bottom:8px">＋</div><strong>Choose a file to upload</strong><p class="small">PDF · DOCX · PPTX · TXT · MD · CSV · source code</p><input type="file" name="file" accept=".pdf,.docx,.pptx,.txt,.md,.csv,.json,.py,.java,.c,.cpp,.h,.html,.xml,.tex,.rst" required style="margin-top:10px"/></div><div class="inline-form" style="margin-top:13px"><div class="field"><label>Resource type</label><select name="kind"><option value="notes">Lecture notes</option><option value="slides">Slides</option><option value="assignment">Assignment</option><option value="paper">Question paper</option><option value="syllabus">Syllabus</option><option value="reference">Reference</option></select></div><div class="field"><label>Folder</label><input name="folder" value="My uploads"/></div></div><button class="btn full" style="margin-top:13px">Upload & extract text →</button></form></section>
    <section class="card"><div class="card-head"><div class="card-title">Your learning shelf</div><span class="chip">${state.materials.length} FILES</span></div>${state.materials.length?state.materials.map(x=>`<div class="material-row"><div class="file-icon">${esc(x.filename.split('.').pop().slice(0,4).toUpperCase())}</div><div style="flex:1;min-width:0"><strong style="display:block;font-size:12px;overflow:hidden;text-overflow:ellipsis">${esc(x.filename)}</strong><span class="muted small">${(x.size/1024).toFixed(1)} KB · ${x.pages||'Text'} ${x.pages?'pages':'content'} · ${x.has_text?'indexed':'no text'}</span></div><button class="btn tiny secondary" data-action="make-cards" data-id="${x.id}">Cards</button><button class="btn tiny ghost" data-action="delete-material" data-id="${x.id}">×</button></div>`).join(''):'<div class="empty">Your shelf is empty. Add your first lecture file to get started.</div>'}</section></div>
    <div class="notice" style="margin-top:17px">Uploads are private to your account. Text extraction supports PDF, DOCX, PPTX and common text/source formats. Scanned PDFs and image-only material need a text-based export.</div>`);
}

async function renderTutor() {
  if(!state.tutorMessages.length) state.tutorMessages=[{role:'assistant',text:'Hey explorer! Ask me about a concept or something from your lecture notes. I will clearly show when an answer is grounded in your uploaded files.'}];
  setContent(`${pageHead('AI Study Buddy','A calm place to ask questions and unpack tricky concepts.','ASK · LEARN · TRY AGAIN')}
    <section class="card"><div class="card-head"><div class="card-title">Your study chat</div><span class="chip blue">${state.materials.length||'—'} UPLOADED FILES</span></div><div class="chat-log" id="chat-log">${state.tutorMessages.map(m=>`<div class="chat-bubble ${m.role==='user'?'user':'assistant'}"><strong class="small">${m.role==='user'?'YOU':'STUDY BUDDY'}</strong><div>${nl(m.text)}</div>${(m.cites||[]).map(c=>`<div class="citation">From ${esc(c.filename)} · ${esc(c.text)}</div>`).join('')}</div>`).join('')}</div><form id="tutor-form" class="inline-form"><div class="field"><label>Your question</label><input name="message" placeholder="Explain recursion like I'm new to it…" required maxlength="3000"/></div><button class="btn">Ask →</button></form><div class="helper" style="margin-top:10px">Without an AI model configured, this is a grounded extractive tutor. Configure an OpenAI-compatible endpoint (Ollama, LM Studio, etc.) in .env for generated explanations.</div></section>`);
  const log=document.getElementById('chat-log'); if(log) log.scrollTop=log.scrollHeight;
}

async function renderFlashcards() {
  state.cards=await api('/api/flashcards?due_only=false');
  state.cardIndex=Math.min(state.cardIndex,Math.max(0,state.cards.length-1));
  const card=state.cards[state.cardIndex];
  setContent(`${pageHead('Flashcards','Quick recall sessions powered by spaced repetition.','REMEMBER MORE')}
    ${card?`<div class="grid two"><section class="card"><div class="card-head"><div class="card-title">Review deck</div><span class="chip">${state.cardIndex+1} / ${state.cards.length}</span></div><div class="flashcard" data-action="flip-card"><div><div class="eyebrow">${state.cardFlipped?'THE BACK':'THE FRONT'} · TAP TO FLIP</div><div class="fc-text">${esc(state.cardFlipped?card.back:card.front)}</div></div></div><div class="xp-row"><span>Interval: ${card.interval} days</span><span>Ease: ${card.ease.toFixed(2)}</span></div><div style="display:flex;justify-content:space-between;gap:8px;margin-top:13px;flex-wrap:wrap"><button class="btn ghost" data-action="card-prev">← Previous</button><button class="btn secondary" data-action="flip-card">${state.cardFlipped?'Show prompt':'Reveal answer'}</button><button class="btn ghost" data-action="card-next">Next →</button></div>${state.cardFlipped?`<div style="margin-top:16px"><div class="small muted" style="margin-bottom:8px">How well did you remember it? (SM-2 grade)</div><div style="display:flex;gap:6px;flex-wrap:wrap">${[0,1,2,3,4,5].map(n=>`<button class="btn tiny ${n>=3?'secondary':'ghost'}" data-action="card-grade" data-grade="${n}">${n} ${['Again','Again','Hard','Okay','Good','Easy'][n]}</button>`).join('')}</div></div>`:''}</section><aside class="card soft"><div class="card-title">How spaced repetition works</div><p>Review a card, then grade how well you recalled it. The next review date adjusts using the SM-2 interval and ease factor.</p><div class="notice">Cards generated from a lecture are drafts. Check the wording against your original notes before relying on them.</div><button class="btn secondary" style="margin-top:13px" data-page="library">Generate from a lecture →</button></aside></div>`:`<div class="empty">No flashcards yet. Upload a lecture in My Library and select “Cards”.</div><button class="btn" data-page="library">Open My Library →</button>`}`);
}

async function renderPlanner() {
  state.tasks=await api('/api/planner');
  setContent(`${pageHead('Study Planner','Turn big deadlines into small, doable quests.','PLAN YOUR WEEK')}
    <section class="card"><div class="card-head"><div class="card-title">Add a study task</div><span class="chip blue">KEEP IT SMALL</span></div><form id="task-form" class="task-form"><div class="field"><label>Task</label><input name="title" placeholder="Revise OS process scheduling" required maxlength="180"/></div><div class="field"><label>Subject</label><select name="subject"><option>Maths</option><option>S&AI</option><option>PSP</option><option>Personal</option></select></div><div class="field"><label>Due date</label><input name="due_date" type="date"/></div><div class="field"><label>Priority</label><select name="priority"><option value="medium">Medium</option><option value="high">High</option><option value="low">Low</option></select></div><button class="btn">Add task</button></form></section>
    <section class="card" style="margin-top:18px"><div class="card-head"><div class="card-title">Your quests</div><span class="chip">${state.tasks.filter(t=>!t.done).length} OPEN</span></div>${state.tasks.length?state.tasks.map(t=>`<div class="list-row"><button class="quest-check ${t.done?'done':''}" data-action="task-toggle" data-id="${t.id}">${t.done?'✓':''}</button><div class="list-main" style="flex:1"><strong class="${t.done?'task-done':''}">${esc(t.title)}</strong><span>${esc(t.subject)} · ${fmtDate(t.due_date)}</span></div><span class="chip">${esc(t.priority)}</span><button class="btn ghost tiny" data-action="task-delete" data-id="${t.id}">×</button></div>`).join(''):'<div class="empty">No tasks yet. Add one small step above.</div>'}</section>`);
}

async function renderCgpa() {
  const [scale,courses,result]=await Promise.all([api('/api/settings/grade-scale'),api('/api/courses'),api('/api/performance/cgpa')]);
  state.gradeScale=scale;state.courses=courses;
  const bands=scale.bands||[];
  setContent(`${pageHead('CGPA Studio','Use your university’s official grade-point scale. No guessed conversions.','TRACK YOUR PROGRESS')}
    <div class="grid two"><section class="card"><div class="card-head"><div class="card-title">Your CGPA</div><span class="chip">${result.configured?'CALCULATED':'NEEDS SCALE'}</span></div><div class="cgpa-result"><strong>${result.cgpa===null||result.cgpa===undefined?'—':result.cgpa.toFixed(2)}</strong><span>${result.configured?'Weighted grade-point average':'Add your official scale below'}</span></div><p class="small">Target CGPA: ${scale.target_cgpa??'Not set'} · Credits: ${result.total_credits??0}</p><div class="notice">This calculator uses only the grade bands you enter. Confirm them against your official ADYPU academic regulations.</div></section>
    <section class="card"><div class="card-title">Add course result</div><form id="course-form" class="inline-form" style="margin-top:12px"><div class="field"><label>Course</label><input name="name" placeholder="Problem Solving with Python" required/></div><div class="field"><label>Credits</label><input name="credits" type="number" min="0.5" max="12" step="0.5" value="3" required/></div><div class="field"><label>Percentage</label><input name="percentage" type="number" min="0" max="100" step="0.1" placeholder="82" required/></div><button class="btn">Add</button></form></section></div>
    <section class="card" style="margin-top:18px"><div class="card-head"><div class="card-title">Course results</div><span class="chip">${courses.length} COURSES</span></div>${courses.length?courses.map(c=>`<div class="list-row"><div class="list-main" style="flex:1"><strong>${esc(c.name)}</strong><span>${c.credits} credits · ${c.percentage}%</span></div><button class="btn ghost tiny" data-action="course-delete" data-id="${c.id}">Remove</button></div>`).join(''):'<div class="empty">Add your course marks to see the weighted calculation.</div>'}</section>
    <section class="card" style="margin-top:18px"><div class="card-head"><div class="card-title">Official grade-point bands</div><span class="chip blue">YOUR UNIVERSITY SCALE</span></div><p class="small">Enter a minimum percentage and its grade point. The highest matching minimum is used for each course.</p><form id="scale-form"><div id="scale-rows">${(bands.length?bands:[{min:0,gp:'',label:''}]).map((b,i)=>`<div class="inline-form scale-row" style="margin:7px 0"><div class="field"><label>Minimum %</label><input type="number" name="min" min="0" max="100" step="0.1" value="${esc(b.min)}" required/></div><div class="field"><label>Grade point</label><input type="number" name="gp" min="0" max="20" step="0.1" value="${esc(b.gp)}" required/></div><div class="field"><label>Label (optional)</label><input name="label" value="${esc(b.label||'')}"/></div><button type="button" class="btn ghost tiny" data-action="remove-band">×</button></div>`).join('')}</div><button type="button" class="btn ghost tiny" data-action="add-band">+ Add grade band</button><div class="field" style="max-width:240px;margin-top:14px"><label>Target CGPA</label><input type="number" name="target_cgpa" min="0" max="20" step="0.1" value="${scale.target_cgpa??9}" required/></div><button class="btn" style="margin-top:10px">Save grade scale</button></form></section>`);
}

function signOut(show=true) {
  state.token='';state.user=null;state.dashboard=null;localStorage.removeItem('sq_token');
  state.page='home';state.worlds=[];state.tutorMessages=[];
  renderAuth(); if(show) toast('Signed out. See you next time!');
}
async function enterApp(token,user) {
  state.token=token;state.user=user;localStorage.setItem('sq_token',token);state.page='home';state.dashboard=null;
  renderShell();
}

// ----------------------------- events -------------------------------------
app.addEventListener('click', async e => {
  const nav=e.target.closest('[data-page]');
  if(nav) { state.page=nav.dataset.page; document.getElementById('sidebar')?.classList.remove('open'); renderShell(); return; }
  const action=e.target.closest('[data-action]');
  if(!action) {
    const option=e.target.closest('[data-option]');
    if(option && state.quiz.submitted===null) {state.quiz.selected=Number(option.dataset.option);renderQuiz();}
    const pyMission=e.target.closest('[data-py-mission]');
    if(pyMission) {const m=state.py.missions.find(x=>x.id===pyMission.dataset.pyMission);selectPythonMission(m);renderPython();}
    const shMission=e.target.closest('[data-sh-mission]');
    if(shMission) {state.selectedTerminal=shMission.dataset.shMission;renderTerminal();}
    const worldTab=e.target.closest('[data-world-tab]');
    if(worldTab) {state.selectedWorld=worldTab.dataset.worldTab;state.selectedConcept=null;renderAtlas();}
    return;
  }
  try {
    if(action.dataset.action==='theme') {
      state.theme=state.theme==='light'?'dark':'light';applyTheme();
      document.querySelectorAll('.theme-btn').forEach(el=>el.outerHTML=themeButton());
      if(state.token) api('/api/me/theme',{method:'PATCH',body:JSON.stringify({theme:state.theme})}).catch(()=>{});
    }
    if(action.dataset.action==='logout') signOut();
    if(action.dataset.action==='menu') document.getElementById('sidebar')?.classList.toggle('open');
    if(action.dataset.action==='back-login') renderAuth();
    if(action.dataset.action==='world-quiz') {state.quiz.world=action.dataset.world;state.quiz.questions=[];state.page='quiz';renderShell();}
    if(action.dataset.action==='concept-quiz') {state.quiz.world=action.dataset.world;state.quiz.questions=[];state.page='quiz';renderShell();}
    if(action.dataset.action==='quiz-world') {state.quiz.world=action.dataset.world;state.quiz.questions=[];state.quiz.index=0;state.quiz.submitted=null;state.quiz.selected=null;renderQuiz();}
    if(action.dataset.action==='quiz-reset') {state.quiz.world='';state.quiz.questions=[];state.quiz.index=0;state.quiz.submitted=null;state.quiz.selected=null;renderQuiz();}
    if(action.dataset.action==='quiz-submit') {
      if(state.quiz.selected===null) return;
      const q=state.quiz.questions[state.quiz.index];
      state.quiz.submitted=await api('/api/quiz/answer',{method:'POST',body:JSON.stringify({question_id:q.id,selected:state.quiz.selected})});renderQuiz();
    }
    if(action.dataset.action==='quiz-next') {
      state.quiz.index++;state.quiz.selected=null;state.quiz.submitted=null;
      if(state.quiz.index>=state.quiz.questions.length){state.quiz.questions=[];state.quiz.index=0;state.quiz.world='';toast('Round complete. Your progress has been saved.');}
      renderQuiz();
    }
    if(action.dataset.action==='py-hint') {state.py.hint=Math.min(state.py.hint+1,(state.py.missions.find(x=>x.id===state.py.mission)?.hints.length||1)-1);state.py.source=document.getElementById('py-source')?.value||state.py.source;state.py.stdin=document.getElementById('py-stdin')?.value||'';renderPython();}
    if(action.dataset.action==='py-reset') {const m=state.py.missions.find(x=>x.id===state.py.mission);selectPythonMission(m);renderPython();}
    if(action.dataset.action==='py-run') {
      state.py.source=document.getElementById('py-source')?.value||'';state.py.stdin=document.getElementById('py-stdin')?.value||'';
      const r=await api('/api/python/run',{method:'POST',body:JSON.stringify({source:state.py.source,stdin:state.py.stdin})});
      state.py.output=(r.stdout||'')+(r.stderr?'\n'+r.stderr:'')+(r.error?'\n'+r.error.explanation:'');
      const out=document.getElementById('py-output');if(out)out.textContent=state.py.output||'(no output)';
      if(r.error?.type==='SandboxUnavailable')toast('Docker sandbox is not configured. No code was executed.');
    }
    if(action.dataset.action==='py-check') {
      state.py.source=document.getElementById('py-source')?.value||'';
      const r=await api(`/api/python/missions/${state.py.mission}/check`,{method:'POST',body:JSON.stringify({source:state.py.source})});
      state.py.output=(r.message||'')+'\n'+(r.result?.stdout||'')+(r.result?.stderr||'');
      const out=document.getElementById('py-output');if(out)out.textContent=state.py.output;
      toast(r.message||'Check complete');
    }
    if(action.dataset.action==='shell-reset') {await api('/api/shell/reset',{method:'POST'});state.shell.output='Virtual files reset.\n';renderTerminal();}
    if(action.dataset.action==='sh-help') {state.shell.output='Available commands: pwd, ls, cd, mkdir, touch, cat, echo, cp, mv, rm, chmod, grep, head, wc, find, git.\n';const o=document.getElementById('terminal-output');if(o)o.textContent=state.shell.output;}
    if(action.dataset.action==='sh-check') {const r=await api(`/api/shell/missions/${state.selectedTerminal}/check`,{method:'POST'});toast(r.message+(r.xp?` +${r.xp} XP`:''));state.user.xp=(state.user.xp||0)+r.xp;}
    if(action.dataset.action==='make-cards') {const r=await api('/api/flashcards/generate',{method:'POST',body:JSON.stringify({material_id:Number(action.dataset.id)})});toast(`${r.created} flashcards created.`);state.page='flashcards';renderShell();}
    if(action.dataset.action==='delete-material') {if(confirm('Delete this upload and its flashcards?')){await api(`/api/materials/${action.dataset.id}`,{method:'DELETE'});renderLibrary();}}
    if(action.dataset.action==='flip-card') {state.cardFlipped=!state.cardFlipped;renderFlashcards();}
    if(action.dataset.action==='card-prev') {state.cardIndex=Math.max(0,state.cardIndex-1);state.cardFlipped=false;renderFlashcards();}
    if(action.dataset.action==='card-next') {state.cardIndex=Math.min(state.cards.length-1,state.cardIndex+1);state.cardFlipped=false;renderFlashcards();}
    if(action.dataset.action==='card-grade') {const card=state.cards[state.cardIndex];await api(`/api/flashcards/${card.id}/review`,{method:'POST',body:JSON.stringify({grade:Number(action.dataset.grade)})});toast('Review saved. Next interval updated.');state.cardFlipped=false;state.cardIndex=Math.min(state.cards.length-1,state.cardIndex+1);renderFlashcards();}
    if(action.dataset.action==='task-toggle') {const t=state.tasks.find(x=>x.id===Number(action.dataset.id));await api(`/api/planner/${t.id}`,{method:'PATCH',body:JSON.stringify({done:!t.done})});renderPlanner();}
    if(action.dataset.action==='task-delete') {await api(`/api/planner/${action.dataset.id}`,{method:'DELETE'});renderPlanner();}
    if(action.dataset.action==='course-delete') {await api(`/api/courses/${action.dataset.id}`,{method:'DELETE'});renderCgpa();}
    if(action.dataset.action==='add-band') {document.getElementById('scale-rows').insertAdjacentHTML('beforeend',`<div class="inline-form scale-row" style="margin:7px 0"><div class="field"><label>Minimum %</label><input type="number" name="min" min="0" max="100" step="0.1" required/></div><div class="field"><label>Grade point</label><input type="number" name="gp" min="0" max="20" step="0.1" required/></div><div class="field"><label>Label</label><input name="label"/></div><button type="button" class="btn ghost tiny" data-action="remove-band">×</button></div>`);}
    if(action.dataset.action==='remove-band') {const rows=document.querySelectorAll('.scale-row');if(rows.length>1)action.closest('.scale-row').remove();}
  } catch(err) { toast(err.message); }
});

app.addEventListener('submit', async e => {
  const form=e.target;
  try {
    if(form.id==='login-form') {
      e.preventDefault();const fd=new FormData(form);
      const r=await api('/api/auth/start',{method:'POST',body:JSON.stringify({email:fd.get('email'),password:fd.get('password')})});
      renderAuth('code',{email:r.email,dev_code:r.dev_code});
    }
    if(form.id==='verify-form') {
      e.preventDefault();const fd=new FormData(form);
      const r=await api('/api/auth/verify',{method:'POST',body:JSON.stringify({email:fd.get('email'),code:fd.get('code')})});
      await enterApp(r.token,r.user);toast('Welcome to Semester Quest!');
    }
    if(form.id==='terminal-form') {
      e.preventDefault();const fd=new FormData(form);const command=String(fd.get('command')||'');
      const out=document.getElementById('terminal-output');
      const r=await api('/api/shell/run',{method:'POST',body:JSON.stringify({command})});
      state.shell.cwd=r.cwd;state.shell.files=r.files;state.shell.git=r.git;
      state.shell.output=(out?.textContent||'')+`\nstudent@quest:${r.cwd.replace('/home/student','~')}$ ${command}\n`+(r.stdout||'')+(r.stderr?'\n'+r.stderr:'');
      renderTerminal();const terminal=document.getElementById('terminal-output');if(terminal)terminal.textContent=state.shell.output;
    }
    if(form.id==='upload-form') {
      e.preventDefault();const fd=new FormData(form);
      const r=await api('/api/materials',{method:'POST',body:fd});toast(`Uploaded ${r.filename}. +${r.xp_awarded} XP`);renderLibrary();
    }
    if(form.id==='tutor-form') {
      e.preventDefault();const fd=new FormData(form);const message=String(fd.get('message')||'').trim();if(!message)return;
      state.tutorMessages.push({role:'user',text:message});state.tutorMessages.push({role:'assistant',text:'Thinking through your material…'});renderTutor();
      const r=await api('/api/tutor',{method:'POST',body:JSON.stringify({message,mode:'teach'})});
      state.tutorMessages.pop();state.tutorMessages.push({role:'assistant',text:r.reply,cites:r.cites||[]});renderTutor();
    }
    if(form.id==='task-form') {
      e.preventDefault();const fd=new FormData(form);await api('/api/planner',{method:'POST',body:JSON.stringify({title:fd.get('title'),subject:fd.get('subject'),due_date:fd.get('due_date'),priority:fd.get('priority')})});toast('Study task added.');renderPlanner();
    }
    if(form.id==='course-form') {
      e.preventDefault();const fd=new FormData(form);await api('/api/courses',{method:'POST',body:JSON.stringify({name:fd.get('name'),credits:Number(fd.get('credits')),percentage:Number(fd.get('percentage'))})});toast('Course result added.');renderCgpa();
    }
    if(form.id==='scale-form') {
      e.preventDefault();const fd=new FormData(form);const rows=[...document.querySelectorAll('.scale-row')].map(row=>({min:Number(row.querySelector('[name=min]').value),gp:Number(row.querySelector('[name=gp]').value),label:row.querySelector('[name=label]').value}));
      await api('/api/settings/grade-scale',{method:'PUT',body:JSON.stringify({bands:rows,target_cgpa:Number(fd.get('target_cgpa'))})});toast('Official grade scale saved.');renderCgpa();
    }
  } catch(err) { toast(err.message); }
});

async function boot() {
  applyTheme();
  if(!state.token) {renderAuth();return;}
  try {const r=await api('/api/me');state.user=r.user;renderShell();}
  catch(e){signOut(false);}
}
boot();
