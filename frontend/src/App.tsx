import { FormEvent, useEffect, useMemo, useState } from 'react';

type Any = Record<string, any>;
type Page = 'home'|'atlas'|'quiz'|'python'|'terminal'|'library'|'tutor'|'flashcards'|'planner'|'cgpa';
const nav: {group:string;items:[Page,string,string][]}[] = [
  {group:'YOUR BASE',items:[['home','⌂','Home Base'],['atlas','✣','The Atlas'],['quiz','?','Quiz Arcade']]},
  {group:'PRACTICE LABS',items:[['python','{ }','Python Lab'],['terminal','⌘','Terminal Lab']]},
  {group:'YOUR LIBRARY',items:[['library','▤','My Library'],['tutor','✎','AI Study Buddy'],['flashcards','▧','Flashcards']]},
  {group:'YOUR PROGRESS',items:[['planner','☷','Study Planner'],['cgpa','∑','CGPA Studio']]},
];
const esc = (x:any) => String(x ?? '');

async function request(path:string, token:string, options:RequestInit={}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization',`Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type','application/json');
  const res = await fetch(path,{...options,headers});
  const data = (res.headers.get('content-type')||'').includes('json') ? await res.json() : await res.text();
  if (!res.ok) throw new Error(data?.detail || data?.message || `Request failed (${res.status})`);
  return data;
}
function Button({children,onClick,kind='primary',type='button',disabled=false}:any) {
  return <button type={type} disabled={disabled} className={`btn ${kind==='secondary'?'secondary':kind==='ghost'?'ghost':''}`} onClick={onClick}>{children}</button>;
}
function Head({kicker,title,subtitle,action}:Any) {
  return <div className="page-head"><div><div className="eyebrow">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}

export default function App() {
  const [token,setToken] = useState(localStorage.getItem('sq_token')||'');
  const [user,setUser] = useState<Any|null>(null);
  const [theme,setTheme] = useState(localStorage.getItem('sq_theme')||'light');
  const [page,setPage] = useState<Page>('home');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [email,setEmail] = useState('');
  const [password,setPassword] = useState('');
  const [devCode,setDevCode] = useState('');
  const [code,setCode] = useState('');
  const [authStep,setAuthStep] = useState<'email'|'code'>('email');
  const [data,setData] = useState<Any>({});
  const [world,setWorld] = useState('maths');
  const [questionIndex,setQuestionIndex] = useState(0);
  const [selected,setSelected] = useState<number|null>(null);
  const [answer,setAnswer] = useState<Any|null>(null);
  const [source,setSource] = useState('');
  const [stdin,setStdin] = useState('');
  const [runResult,setRunResult] = useState<Any|null>(null);
  const [terminalCommand,setTerminalCommand] = useState('');
  const [chat,setChat] = useState<Any[]>([]);
  const [flashIndex,setFlashIndex] = useState(0);
  const [flipped,setFlipped] = useState(false);
  const [mobileNav,setMobileNav] = useState(false);
  const [toast,setToast] = useState('');

  const notify=(message:string)=>{setToast(message);window.setTimeout(()=>setToast(''),3000);};
  const call=(path:string,options:RequestInit={})=>request(path,token,options);
  const toggleTheme=()=>setTheme(t=>t==='light'?'dark':'light');

  useEffect(()=>{
    document.body.dataset.theme=theme;localStorage.setItem('sq_theme',theme);
    if(token) call('/api/me/theme',{method:'PATCH',body:JSON.stringify({theme})}).catch(()=>{});
  },[theme]);

  useEffect(()=>{
    if(!token) return;
    call('/api/me').then(r=>setUser(r.user)).catch(()=>{localStorage.removeItem('sq_token');setToken('');setUser(null);});
  },[token]);

  useEffect(()=>{
    if(!token || !user) return;
    setError('');
    const load=async()=>{
      try {
        if(page==='home') setData(await call('/api/dashboard'));
        if(page==='atlas') setData(await call('/api/worlds'));
        if(page==='quiz') {setData(await call(`/api/quiz/questions?limit=20${world?`&world=${world}`:''}`));setQuestionIndex(0);setSelected(null);setAnswer(null);}
        if(page==='python') setData(await call('/api/python/missions'));
        if(page==='terminal') setData(await call('/api/shell'));
        if(page==='library') setData(await call('/api/materials'));
        if(page==='flashcards') setData(await call('/api/flashcards'));
        if(page==='planner') setData(await call('/api/planner'));
        if(page==='cgpa') {
          const [scale,courses,result]=await Promise.all([call('/api/settings/grade-scale'),call('/api/courses'),call('/api/performance/cgpa')]);
          setData({scale,courses,result});
        }
      } catch(e:any) {setError(e.message);}
    };
    load();
  },[page,user?.id,world]);

  const selectPage=(next:Page)=>{setPage(next);setMobileNav(false);setError('');};
  const signOut=()=>{localStorage.removeItem('sq_token');setToken('');setUser(null);setData({});setAuthStep('email');setEmail('');setPassword('');};

  const startLogin=async(e:FormEvent)=>{
    e.preventDefault();setBusy(true);setError('');
    try {const r=await request('/api/auth/start','',{method:'POST',body:JSON.stringify({email,password})});setEmail(r.email);setDevCode(r.dev_code||'');setAuthStep('code');}
    catch(err:any){setError(err.message);} finally{setBusy(false);}
  };
  const verifyLogin=async(e:FormEvent)=>{
    e.preventDefault();setBusy(true);setError('');
    try {const r=await request('/api/auth/verify','',{method:'POST',body:JSON.stringify({email,code})});localStorage.setItem('sq_token',r.token);setToken(r.token);setUser(r.user);setPage('home');notify('Welcome to Semester Quest!');}
    catch(err:any){setError(err.message);} finally{setBusy(false);}
  };

  const submitAnswer=async()=>{
    const q=data?.[questionIndex];if(!q||selected===null)return;
    try {setAnswer(await call('/api/quiz/answer',{method:'POST',body:JSON.stringify({question_id:q.id,selected})}));}
    catch(e:any){setError(e.message);}
  };
  const runPython=async()=>{
    try {const r=await call('/api/python/run',{method:'POST',body:JSON.stringify({source,stdin})});setRunResult(r);if(r.error?.type==='SandboxUnavailable')notify('Docker sandbox is not configured. No code was executed.');}
    catch(e:any){setError(e.message);}
  };
  const runTerminal=async(e:FormEvent)=>{
    e.preventDefault();try {const r=await call('/api/shell/run',{method:'POST',body:JSON.stringify({command:terminalCommand})});setData((d:any)=>({...d,shellResult:r}));setTerminalCommand('');}
    catch(err:any){setError(err.message);}
  };
  const onUpload=async(e:FormEvent<HTMLFormElement>)=>{
    e.preventDefault();const form=new FormData(e.currentTarget);try {const r=await call('/api/materials',{method:'POST',body:form});notify(`Uploaded ${r.filename}. +${r.xp_awarded} XP`);setData(await call('/api/materials'));}
    catch(err:any){setError(err.message);}
  };
  const askTutor=async(e:FormEvent<HTMLFormElement>)=>{
    e.preventDefault();const form=new FormData(e.currentTarget);const message=String(form.get('message')||'');setChat(c=>[...c,{role:'user',text:message},{role:'assistant',text:'Searching your uploaded class material…'}]);
    try {const r=await call('/api/tutor',{method:'POST',body:JSON.stringify({message,mode:'teach'})});setChat(c=>[...c.slice(0,-1),{role:'assistant',text:r.reply,cites:r.cites}]);}
    catch(err:any){setError(err.message);setChat(c=>c.slice(0,-1));}
    e.currentTarget.reset();
  };
  const addTask=async(e:FormEvent<HTMLFormElement>)=>{e.preventDefault();const f=new FormData(e.currentTarget);try{await call('/api/planner',{method:'POST',body:JSON.stringify(Object.fromEntries(f))});setData(await call('/api/planner'));e.currentTarget.reset();}catch(err:any){setError(err.message);}};

  const themeControl=<button className="theme-btn" onClick={toggleTheme}><span className="theme-dot"/>{theme==='light'?'Light mode':'Dark mode'}</button>;

  if(!token || !user) return <div className="auth-wrap"><div className="auth-theme">{themeControl}</div><section className="auth-card"><div className="auth-inner"><div className="brand-lockup"><div className="brand-mark">SQ</div><div><div className="brand-name">Semester Quest</div><div className="brand-sub">Your semester. Your adventure.</div></div></div><div className="eyebrow">NEWTON SCHOOL OF TECHNOLOGY · PUNE</div><h1>{authStep==='email'?'Ready, explorer?':'Check your inbox'}</h1><p>{authStep==='email'?'Sign in with your Pune ADYPU student email to open your learning worlds.':'Enter the 6-digit code sent to your ADYPU email.'}</p>
    {authStep==='email'?<form onSubmit={startLogin}><div className="field"><label>ADYPU student email</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="e26b07f0007@adypu.edu.in" required/></div><div className="field"><label>Password</label><input type="password" value={password} onChange={e=>setPassword(e.target.value)} minLength={8} required/></div><button className="btn full" disabled={busy}>{busy?'Sending…':'Continue with ADYPU email →'}</button><div className="helper" style={{marginTop:12}}>Only addresses ending in <strong>@adypu.edu.in</strong> are accepted. A one-time code verifies mailbox access.</div></form>:
    <form onSubmit={verifyLogin}><div className="field"><label>6-digit verification code</label><input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e=>setCode(e.target.value)} required autoFocus/></div>{devCode&&<div className="notice">Development code: <strong className="mono">{devCode}</strong><br/>Configure SMTP and set DEV_SHOW_CODE=0 for production.</div>}<button className="btn full" disabled={busy}>Verify & enter Home Base →</button><Button kind="ghost" onClick={()=>setAuthStep('email')}>Use another email</Button></form>}
    {error&&<div className="notice" style={{marginTop:12}}>{error}</div>}<div className="auth-foot">A tiny bit of structure. A lot more curiosity. ✦</div></div></section></div>;

  const renderHome=()=> <>
    <Head kicker="HOME BASE" title={`Welcome back, ${user.name||'explorer'}!`} subtitle="Your next small win is one click away."/>
    <section className="hero"><div><div className="eyebrow">LEVEL {data.level||1} · THE ADVENTURE CONTINUES</div><h2>Make this semester<br/>your playground.</h2><p>Learn a little, practise a little, and stack up XP as you go. Your three worlds are ready when you are.</p><Button kind="secondary" onClick={()=>selectPage('atlas')}>Explore the Atlas →</Button></div><div className="hero-stat"><strong>{user.xp||0}</strong><span>Total experience points</span><div className="xp-row"><span>Level {data.level||1}</span><span>{data.level_xp||0}/100 XP</span></div><div className="progress-track"><div className="progress-fill" style={{width:`${data.progress_percent||0}%`,background:'#addcff'}}/></div></div></section>
    <div className="grid four" style={{margin:'20px 0'}}>{[['✦',data.stats?.correct_answers||0,'Correct answers'],['▤',data.stats?.materials||0,'Class uploads'],['▧',data.stats?.flashcards_due||0,'Cards due'],['☷',data.stats?.open_tasks||0,'Open tasks']].map(([i,v,l])=><div className="card stat-card"><div className="stat-icon">{i}</div><div><div className="stat-value">{v}</div><div className="stat-label">{l}</div></div></div>)}</div>
    <div className="card-head"><div className="card-title">Choose your world</div><Button kind="ghost" onClick={()=>selectPage('atlas')}>View all →</Button></div>
    <div className="grid three">{(data.worlds||[]).map((w:Any,i:number)=><article className="card world-card"><div className="world-icon">{w.icon}</div><span className="chip">WORLD 0{i+1}</span><h3>{w.title}</h3><p>{w.subtitle}</p><div className="progress-track"><div className="progress-fill" style={{width:`${w.progress}%`}}/></div><div className="world-bottom"><span>{w.done}/{w.total_questions} mastered</span><Button kind="secondary" onClick={()=>{setWorld(w.slug);selectPage('quiz');}}>Play →</Button></div></article>)}</div>
    <div className="grid two" style={{marginTop:22}}><section className="card"><div className="card-title">Today's tiny quests</div>{(data.quests||[]).map((q:Any)=><div className="list-row"><div className={`quest-check ${q.done?'done':''}`}>{q.done?'✓':'·'}</div><div className="list-main" style={{flex:1}}><strong>{q.title}</strong><span>{q.done?'Already in the bag!':`+${q.xp} XP when complete`}</span></div><span className="chip">{q.done?'DONE':`+${q.xp} XP`}</span></div>)}</section><section className="card"><div className="card-title">Badge shelf</div><div className="badge-grid" style={{marginTop:12}}>{(data.badges||[]).map((b:Any)=><div className={`badge-card ${b.earned?'earned':''}`}><div className="badge-icon">{b.icon}</div><strong>{b.title}</strong><span>{b.description}</span></div>)}</div></section></div>
  </>;

  const renderAtlas=()=>{const worlds=data||[];const active=worlds.find((w:Any)=>w.slug===world)||worlds[0];return <><Head kicker="YOUR THREE WORLDS" title="The Atlas" subtitle="Pick a path, explore a concept, and learn at your own pace."/><div className="world-tabs">{worlds.map((w:Any)=><button className={`tab-btn ${w.slug===active?.slug?'active':''}`} onClick={()=>setWorld(w.slug)}>{w.icon} {w.title}</button>)}</div>{active&&<><div className="card soft" style={{marginBottom:17}}><span className="chip blue">STARTER CONCEPT MAP</span><h2 className="card-title" style={{marginTop:10}}>{active.title}</h2><p>{active.subtitle}. This is a starter map, not an official syllabus. Upload faculty notes to make your study sessions course-specific.</p></div><div className="concept-grid">{active.concepts.map((c:Any,i:number)=><article className="concept"><div className="eyebrow">NODE {String(i+1).padStart(2,'0')} · {c.kind}</div><h3>{c.title}</h3><p>{c.description}</p></article>)}</div></>}</>};

  const renderQuiz=()=>{const questions=data||[];const q=questions[questionIndex];return <><Head kicker="PRACTICE MODE" title="Quiz Arcade" subtitle="One question at a time. Think it through, then lock in your answer." action={<Button kind="ghost" onClick={()=>{setWorld('maths');selectPage('quiz')}}>Restart</Button>}/><div className="world-tabs">{[['maths','Maths'],['sai','S&AI'],['psp','PSP']].map(([slug,label])=><button className={`tab-btn ${world===slug?'active':''}`} onClick={()=>setWorld(slug as string)}>{label}</button>)}</div>{q?<div className="grid two"><section className="card"><div className="card-head"><span className="chip blue">{q.world.toUpperCase()} · {q.difficulty}</span><span className="muted small">QUESTION {questionIndex+1} / {questions.length}</span></div><div className="question">{q.prompt}</div><div className="options">{q.options.map((o:string,i:number)=><button disabled={!!answer} className={`option ${selected===i?'selected':''} ${answer&&i===answer.correct_index?'correct':''}`} onClick={()=>setSelected(i)}><span className="option-key">{String.fromCharCode(65+i)}</span>{o}</button>)}</div>{answer?<div className="explanation"><strong>{answer.correct?'Nice work! ✦':'Good try — learn from it.'}</strong><br/>{answer.explanation}<p>+{answer.xp} XP</p><Button onClick={()=>{setQuestionIndex((n:number)=>n+1);setSelected(null);setAnswer(null);}}>Next question →</Button></div>:<Button style={{marginTop:14} as any} disabled={selected===null} onClick={submitAnswer}>Check answer</Button>}</section><aside className="card soft"><div className="card-title">Tiny hint</div><p>Read the question twice. Identify exactly what it asks before choosing an option.</p><div className="notice">Correct answers earn +10 XP the first time you master them.</div></aside></div>:<div className="empty">No more questions in this round. Pick another world or refresh to practise again.</div>}</>};

  const renderPython=()=>{const missions=data||[];const m=missions[0];return <><Head kicker="BUILD WITH PYTHON" title="Python Lab" subtitle="Write code, run it in an isolated sandbox, and learn from the output."/><div className="lab-layout"><aside className="card"><div className="card-title">Mission board</div>{missions.map((x:Any)=><button className="mission-item" onClick={()=>{setSource(x.starter||'');setData(missions);}}><strong>{x.title}</strong><span>{x.topic} · {x.difficulty}</span></button>)}</aside><section className="card"><div className="card-title">{m?.title||'Your code editor'}</div><p>{m?.prompt||'Choose a mission from the board.'}</p><div className="editor"><div className="editor-top"><span>main.py</span><span>PYTHON 3.13</span></div><textarea value={source||m?.starter||''} onChange={e=>setSource(e.target.value)} spellCheck={false}/><div className="editor-top">stdin · input()</div><textarea className="stdin" value={stdin} onChange={e=>setStdin(e.target.value)}/></div><Button onClick={runPython}>▶ Run code</Button><div className="card-title" style={{marginTop:15}}>Output</div><pre className="output">{runResult?.stdout||runResult?.stderr||'Run your code to see the output.'}</pre><div className="notice" style={{marginTop:12}}>Python execution requires Docker isolation. Install Docker Desktop and run <span className="mono">docker pull python:3.13-alpine</span>. Code will not run unsandboxed.</div></section></div></>};

  const renderTerminal=()=> <><Head kicker="COMMAND LINE QUESTS" title="Terminal Lab" subtitle="A virtual Linux playground. Commands change this sandbox, never your computer."/><div className="lab-layout"><aside className="card"><div className="card-title">Missions</div>{(data.missions||[]).map((m:Any)=><div className="mission-item"><strong>{m.title}</strong><span>+{m.xp} XP · VIRTUAL SHELL</span></div>)}</aside><section className="card"><div className="terminal-output">{data.shellResult?.stdout||'Welcome to quest-shell 1.0\nType help to see available commands.'}{data.shellResult?.stderr}</div><form className="terminal-line" onSubmit={runTerminal}><span className="mono small">student@quest:~$</span><input value={terminalCommand} onChange={e=>setTerminalCommand(e.target.value)} placeholder="try: ls -l"/><button className="btn tiny">Run ↵</button></form><div className="notice" style={{marginTop:12}}>Supported commands include pwd, ls, cd, mkdir, touch, cat, echo, cp, mv, rm, chmod, grep, head, wc, find and a virtual Git workflow.</div></section></div></>;

  const renderLibrary=()=> <><Head kicker="YOUR CLASS MATERIALS" title="My Library" subtitle="Upload lectures, notes and assignments. Your tutor can search their extracted text."/><div className="grid two"><section className="card"><div className="card-title">Add a class resource</div><form onSubmit={async e=>{e.preventDefault();const f=new FormData(e.currentTarget as HTMLFormElement);try{const r=await call('/api/materials',{method:'POST',body:f});notify(`Uploaded ${r.filename}.`);setData(await call('/api/materials'));}catch(err:any){setError(err.message);}}}><div className="field"><label>Choose file</label><input type="file" name="file" required accept=".pdf,.docx,.pptx,.txt,.md,.csv,.json,.py,.java,.c,.cpp"/></div><div className="field"><label>Resource type</label><select name="kind"><option value="notes">Lecture notes</option><option value="slides">Slides</option><option value="assignment">Assignment</option><option value="syllabus">Syllabus</option></select></div><button className="btn full">Upload & extract text →</button></form></section><section className="card"><div className="card-title">Your learning shelf</div>{(data||[]).map((m:Any)=><div className="material-row"><div className="file-icon">{m.filename.split('.').pop()}</div><div><strong>{m.filename}</strong><div className="small muted">{Math.round(m.size/1024)} KB · {m.pages||'Text'} pages</div></div></div>)}</section></div></>;

  const renderTutor=()=> <><Head kicker="ASK · LEARN · TRY AGAIN" title="AI Study Buddy" subtitle="Ask about concepts and your uploaded lecture notes."/><section className="card"><div className="chat-log">{chat.map(m=><div className={`chat-bubble ${m.role==='user'?'user':'assistant'}`}><strong className="small">{m.role==='user'?'YOU':'STUDY BUDDY'}</strong><div style={{whiteSpace:'pre-wrap'}}>{m.text}</div>{(m.cites||[]).map((c:Any)=><div className="citation">From {c.filename}: {c.text}</div>)}</div>)}</div><form className="inline-form" onSubmit={askTutor}><div className="field"><label>Your question</label><input name="message" placeholder="Explain recursion step by step…" required/></div><button className="btn">Ask →</button></form><div className="helper">The built-in tutor retrieves excerpts. Add an OpenAI-compatible model in .env for generated explanations.</div></section></>;

  const renderFlashcards=()=>{const cards=data||[];const c=cards[flashIndex];return <><Head kicker="REMEMBER MORE" title="Flashcards" subtitle="Quick recall sessions powered by spaced repetition."/>{c?<div className="card" style={{maxWidth:740}}><div className="flashcard" onClick={()=>setFlipped(f=>!f)}><div><div className="eyebrow">{flipped?'THE BACK':'THE FRONT'} · TAP TO FLIP</div><div className="fc-text">{flipped?c.back:c.front}</div></div></div><div style={{display:'flex',gap:8,marginTop:14,flexWrap:'wrap'}}><Button kind="ghost" onClick={()=>{setFlashIndex(Math.max(0,flashIndex-1));setFlipped(false);}}>← Previous</Button><Button kind="secondary" onClick={()=>setFlipped(f=>!f)}>Flip</Button><Button onClick={()=>{setFlashIndex(Math.min(cards.length-1,flashIndex+1));setFlipped(false);}}>Next →</Button></div>{flipped&&<div style={{display:'flex',gap:7,marginTop:16}}>{[0,1,2,3,4,5].map(n=><Button kind={n>=3?'secondary':'ghost'} onClick={async()=>{await call(`/api/flashcards/${c.id}/review`,{method:'POST',body:JSON.stringify({grade:n})});setFlashIndex(Math.min(cards.length-1,flashIndex+1));setFlipped(false);}}>{n} · {['Again','Again','Hard','Okay','Good','Easy'][n]}</Button>)}</div>}</div>:<div className="empty">No flashcards yet. Upload a lecture in My Library and generate a deck.</div>}</>};

  const renderPlanner=()=> <><Head kicker="PLAN YOUR WEEK" title="Study Planner" subtitle="Turn big deadlines into small, doable quests."/><section className="card"><form className="inline-form" onSubmit={addTask}><div className="field"><label>Task</label><input name="title" placeholder="Revise OS process scheduling" required/></div><div className="field"><label>Subject</label><select name="subject"><option>Maths</option><option>S&AI</option><option>PSP</option><option>Personal</option></select></div><div className="field"><label>Due date</label><input type="date" name="due_date"/></div><div className="field"><label>Priority</label><select name="priority"><option value="medium">Medium</option><option value="high">High</option><option value="low">Low</option></select></div><button className="btn">Add task</button></form></section><section className="card" style={{marginTop:16}}>{(data||[]).map((t:Any)=><div className="list-row"><button className={`quest-check ${t.done?'done':''}`} onClick={async()=>{await call(`/api/planner/${t.id}`,{method:'PATCH',body:JSON.stringify({done:!t.done})});setData(await call('/api/planner'));}}>{t.done?'✓':''}</button><div className="list-main" style={{flex:1}}><strong className={t.done?'task-done':''}>{t.title}</strong><span>{t.subject} · {t.due_date||'No date'}</span></div><span className="chip">{t.priority}</span></div>)}</section></>;

  const renderCgpa=()=> <><Head kicker="TRACK YOUR PROGRESS" title="CGPA Studio" subtitle="Use your university's official grade-point scale. No guessed conversions."/><div className="grid two"><section className="card"><div className="cgpa-result"><strong>{data.result?.cgpa??'—'}</strong><span>{data.result?.configured?'Weighted grade-point average':'Add your official grade bands'}</span></div><p className="small">Target: {data.scale?.target_cgpa??'—'} · Credits: {data.result?.total_credits??0}</p></section><section className="card"><div className="card-title">Your courses</div>{(data.courses||[]).map((c:Any)=><div className="list-row"><div className="list-main"><strong>{c.name}</strong><span>{c.credits} credits · {c.percentage}%</span></div></div>)}<form className="inline-form" onSubmit={async e=>{e.preventDefault();const f=new FormData(e.currentTarget as HTMLFormElement);await call('/api/courses',{method:'POST',body:JSON.stringify({name:f.get('name'),credits:Number(f.get('credits')),percentage:Number(f.get('percentage'))})});const [scale,courses,result]=await Promise.all([call('/api/settings/grade-scale'),call('/api/courses'),call('/api/performance/cgpa')]);setData({scale,courses,result});}}><div className="field"><label>Course</label><input name="name" required/></div><div className="field"><label>Credits</label><input name="credits" type="number" value="3" min="0.5" max="12" required/></div><div className="field"><label>Mark %</label><input name="percentage" type="number" min="0" max="100" required/></div><button className="btn">Add</button></form></section></div><section className="card" style={{marginTop:16}}><div className="card-title">Official grade-point bands</div><p>Enter a minimum percentage and corresponding grade point. Your university's scale is not assumed.</p><form onSubmit={async e=>{e.preventDefault();const f=new FormData(e.currentTarget as HTMLFormElement);const rows=JSON.parse(String(f.get('bands')));await call('/api/settings/grade-scale',{method:'PUT',body:JSON.stringify({bands:rows,target_cgpa:Number(f.get('target'))})});const [scale,courses,result]=await Promise.all([call('/api/settings/grade-scale'),call('/api/courses'),call('/api/performance/cgpa')]);setData({scale,courses,result});notify('Grade scale saved.');}}><div className="field"><label>Grade bands JSON</label><textarea name="bands" rows={5} defaultValue={JSON.stringify(data.scale?.bands?.length?data.scale.bands:[{min:0,gp:0,label:'Enter your bands'}],null,2)}/></div><div className="field" style={{maxWidth:200}}><label>Target CGPA</label><input name="target" type="number" defaultValue={data.scale?.target_cgpa||9} min="0" max="20" step="0.1"/></div><button className="btn">Save official scale</button></form></section></>;

  const renderPage=()=>{
    if(page==='home')return renderHome();if(page==='atlas')return renderAtlas();if(page==='quiz')return renderQuiz();if(page==='python')return renderPython();if(page==='terminal')return renderTerminal();if(page==='library')return renderLibrary();if(page==='tutor')return renderTutor();if(page==='flashcards')return renderFlashcards();if(page==='planner')return renderPlanner();return renderCgpa();
  };

  return <div className="shell"><aside className={`sidebar ${mobileNav?'open':''}`}><div className="side-brand"><div className="brand-mark">SQ</div><div><div className="brand-name">Semester Quest</div><div className="brand-sub">LEARN · PLAY · LEVEL UP</div></div></div>{nav.map(group=><div className="nav-group"><div className="nav-label">{group.group}</div>{group.items.map(([id,icon,label])=><button className={`nav-item ${page===id?'active':''}`} onClick={()=>selectPage(id)}><span className="nav-ico">{icon}</span>{label}</button>)}</div>)}<div className="side-spacer"/><div className="side-user"><div className="avatar">{user.name?.slice(0,2)||'SQ'}</div><div style={{minWidth:0,flex:1}}><strong style={{fontSize:11,display:'block'}}>{user.name}</strong><div className="user-email">{user.email}</div></div><Button kind="ghost" onClick={signOut}>↗</Button></div></aside><main className="main"><header className="topbar"><div className="topbar-left"><button className="btn ghost tiny mobile-menu" onClick={()=>setMobileNav(v=>!v)}>☰</button><div className="breadcrumb">Semester Quest / {nav.flatMap(g=>g.items).find(i=>i[0]===page)?.[2]}</div></div><div className="topbar-right"><div className="streak-pill">✦ LEVEL {Math.floor((user.xp||0)/100)+1} · {user.xp||0} XP</div>{themeControl}</div></header><section className="content">{error&&<div className="notice" style={{marginBottom:15}}>{error}</div>}{renderPage()}</section></main>{toast&&<div className="toast">{toast}</div>}</div>;
}
