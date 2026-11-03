from __future__ import annotations
import os, re, json, secrets, smtplib, time, copy
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from . import models as m, content, rag, llm, engines, vshell
from .config import (DATA_DIR, UPLOAD_DIR, MAX_UPLOAD_MB, SMTP_HOST, SMTP_PORT,
                     SMTP_USER, SMTP_PASS, SMTP_FROM, DEV_SHOW_CODE, OTP_MINUTES)
from .db import Base, engine, get_db, SessionLocal
from .security import (current_user, valid_email, hash_pw, check_pw, hash_code,
                       check_code, new_code, make_token)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield

app = FastAPI(title="Semester Quest API", version="1.0.0", description="Gamified learning platform for Newton School of Technology students.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in os.getenv("SQ_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets", check_dir=False), name="assets")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seed_database(db: Session) -> None:
    if db.scalar(select(func.count(m.World.id))) == 0:
        for w in content.WORLDS:
            db.add(m.World(**w))
        db.flush()
    if db.scalar(select(func.count(m.QuizQuestion.id))) == 0:
        for world, topic, prompt, options, answer, explanation, difficulty in content.QUESTIONS:
            db.add(m.QuizQuestion(world_slug=world, topic=topic, prompt=prompt, options=options,
                                  answer=answer, explanation=explanation, difficulty=difficulty))
    db.commit()

# ----------------------------- schemas ------------------------------------
class AuthStart(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)

class AuthVerify(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)

class ThemeIn(BaseModel):
    theme: str = Field(pattern="^(light|dark)$")

class QuizAnswer(BaseModel):
    question_id: int
    selected: int = Field(ge=0, le=10)

class TutorIn(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    mode: str = "teach"

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    subject: str = Field(default="", max_length=50)
    due_date: str = Field(default="", max_length=10)
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")

class TaskUpdate(BaseModel):
    done: bool | None = None
    title: str | None = Field(default=None, max_length=180)
    due_date: str | None = Field(default=None, max_length=10)
    priority: str | None = Field(default=None, pattern="^(low|medium|high)$")

class GradeBand(BaseModel):
    min: float = Field(ge=0, le=100)
    gp: float = Field(ge=0, le=20)
    label: str = Field(default="", max_length=8)

class GradeScaleIn(BaseModel):
    bands: list[GradeBand] = Field(min_length=1, max_length=20)
    target_cgpa: float = Field(default=9.0, ge=0, le=20)

class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    credits: float = Field(ge=0.5, le=12)
    percentage: float = Field(ge=0, le=100)

class ShellIn(BaseModel):
    command: str = Field(max_length=1000)

class FlashcardReview(BaseModel):
    grade: int = Field(ge=0, le=5)

class MaterialGenerate(BaseModel):
    material_id: int


# ----------------------------- helpers ------------------------------------
def user_dict(u: m.User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "xp": u.xp, "theme": u.theme,
            "created_at": u.created_at.isoformat() if u.created_at else None}

def level_info(xp: int) -> dict:
    level = xp // 100 + 1
    in_level = xp % 100
    return {"level": level, "level_xp": in_level, "next_level_xp": 100, "progress_percent": in_level}

def public_question(q: m.QuizQuestion) -> dict:
    return {"id": q.id, "world": q.world_slug, "topic": q.topic, "prompt": q.prompt,
            "options": q.options, "difficulty": q.difficulty}

def owned_material(db: Session, user: m.User, material_id: int) -> m.Material:
    x = db.get(m.Material, material_id)
    if not x or x.user_id != user.id:
        raise HTTPException(404, "Material not found")
    return x

def shell_state(db: Session, user: m.User) -> tuple[m.ShellState, dict]:
    row = db.scalar(select(m.ShellState).where(m.ShellState.user_id == user.id))
    if not row:
        state = vshell.initial_state()
        row = m.ShellState(user_id=user.id, files=state["files"], cwd=state["cwd"], git=state["git"])
        db.add(row); db.flush()
    state = {"files": row.files or {}, "cwd": row.cwd, "git": row.git or {"initialized":False,"staged":[],"commits":[]}}
    return row, state

def task_dict(t: m.PlannerTask) -> dict:
    return {"id":t.id,"title":t.title,"subject":t.subject,"due_date":t.due_date,"priority":t.priority,"done":t.done}

def material_dict(x: m.Material) -> dict:
    return {"id":x.id,"filename":x.filename,"kind":x.kind,"size":x.size,"pages":x.pages,
            "folder":x.folder,"status":x.status,"created_at":x.created_at.isoformat() if x.created_at else None,
            "has_text":bool(x.text_content)}

def earned_badges(db: Session, user: m.User) -> list[dict]:
    attempts=db.scalars(select(m.QuizAttempt).where(m.QuizAttempt.user_id==user.id)).all()
    correct=sum(1 for a in attempts if a.correct)
    xp=user.xp
    shell=db.scalar(select(m.ShellState).where(m.ShellState.user_id==user.id))
    git_ready=bool(shell and shell.git and shell.git.get("commits"))
    term_done=(user.settings or {}).get("completed_terminals",[])
    badges=[
        ("first_solve","First Spark","Answer your first question correctly",correct>=1,"✨"),
        ("ten_solves","Quiz Explorer","Get 10 questions right",correct>=10,"◇"),
        ("terminal_tamer","Terminal Tamer","Complete a terminal mission",len(term_done)>=1,"⌘"),
        ("git_gud","Git Gud","Make a virtual Git commit",git_ready,"◇"),
        ("level_up","Level Up","Reach level 2",xp>=100,"⬆"),
        ("library_keeper","Library Keeper","Upload your first class resource",db.scalar(select(func.count(m.Material.id)).where(m.Material.user_id==user.id))>0,"▤"),
        ("flashcard_fan","Flashcard Fan","Review your first flashcard",db.scalar(select(func.count(m.Flashcard.id)).where(m.Flashcard.user_id==user.id,m.Flashcard.repetitions>0))>0,"▧"),
    ]
    return [{"id":i,"title":t,"description":d,"earned":e,"icon":ic} for i,t,d,e,ic in badges]


def send_login_code(email: str, code: str) -> bool:
    if not SMTP_HOST:
        return False
    msg=EmailMessage()
    msg["Subject"]="Your Semester Quest sign-in code"
    msg["From"]=SMTP_FROM
    msg["To"]=email
    msg.set_content(f"Your Semester Quest verification code is {code}. It expires in {OTP_MINUTES} minutes. If you did not request it, ignore this email.")
    with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=15) as server:
        server.starttls()
        if SMTP_USER: server.login(SMTP_USER,SMTP_PASS)
        server.send_message(msg)
    return True


# ----------------------------- health/auth -------------------------------
@app.get("/api/health")
def health():
    return {"ok":True,"app":"Semester Quest","version":"1.0.0","python_sandbox":engines.isolation_level()}

@app.get("/api/meta")
def meta():
    return {"email_domain":"adypu.edu.in","otp_required":True,"theme_modes":["light","dark"],
            "llm_engine":llm.engine_name(),"python_sandbox":engines.isolation_level(),
            "upload_max_mb":MAX_UPLOAD_MB}

@app.post("/api/auth/start")
def auth_start(body: AuthStart, db: Session=Depends(get_db)):
    email=body.email.strip().lower()
    if not valid_email(email): raise HTTPException(400,"Use your Pune ADYPU email ending in @adypu.edu.in.")
    user=db.scalar(select(m.User).where(m.User.email==email))
    if user:
        if not check_pw(body.password,user.password_hash): raise HTTPException(401,"Email or password is incorrect.")
    else:
        username=email.split("@",1)[0]
        user=m.User(email=email,password_hash=hash_pw(body.password),name=username.upper(),settings={})
        db.add(user); db.flush()
    code=new_code()
    db.query(m.LoginCode).filter(m.LoginCode.email==email).delete()
    db.add(m.LoginCode(email=email,code_hash=hash_code(code),expires_at=utcnow()+timedelta(minutes=OTP_MINUTES)))
    db.commit()
    delivered=False
    if SMTP_HOST:
        try: delivered=send_login_code(email,code)
        except Exception as exc: raise HTTPException(503,"Could not send the verification email. Check SMTP settings and retry.") from exc
    result={"message":"Verification code sent to your ADYPU inbox." if delivered else "Email delivery is not configured. Use the development code shown below.","email":email,"delivery":"email" if delivered else "development"}
    if not delivered and DEV_SHOW_CODE: result["dev_code"]=code
    return result

@app.post("/api/auth/verify")
def auth_verify(body: AuthVerify, db: Session=Depends(get_db)):
    email=body.email.strip().lower()
    row=db.scalar(select(m.LoginCode).where(m.LoginCode.email==email).order_by(desc(m.LoginCode.created_at)))
    if not row: raise HTTPException(400,"Request a new verification code.")
    if row.attempts>=5: raise HTTPException(429,"Too many attempts. Request a new code.")
    if row.expires_at < utcnow(): raise HTTPException(400,"Code expired. Request a new one.")
    row.attempts+=1
    if not check_code(body.code,row.code_hash):
        db.commit(); raise HTTPException(400,"That code is not correct.")
    user=db.scalar(select(m.User).where(m.User.email==email))
    if not user: raise HTTPException(404,"Account not found. Start sign-in again.")
    db.delete(row); db.commit()
    return {"token":make_token(user.id),"user":user_dict(user)}

@app.get("/api/me")
def me(user: m.User=Depends(current_user)):
    return {"user":user_dict(user),**level_info(user.xp)}

@app.patch("/api/me/theme")
def set_theme(body: ThemeIn, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    user.theme=body.theme; db.commit()
    return {"theme":user.theme}

@app.post("/api/auth/logout")
def logout(user: m.User=Depends(current_user)):
    return {"ok":True,"message":"Signed out on this device. Remove the local token to finish."}


# ----------------------------- dashboard/worlds ---------------------------
@app.get("/api/dashboard")
def dashboard(user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    correct_ids=set(db.scalars(select(m.QuizAttempt.question_id).where(m.QuizAttempt.user_id==user.id,m.QuizAttempt.correct.is_(True))).all())
    worlds=db.scalars(select(m.World).order_by(m.World.position)).all()
    world_rows=[]
    for w in worlds:
        qs=db.scalars(select(m.QuizQuestion.id).where(m.QuizQuestion.world_slug==w.slug)).all()
        done=sum(1 for qid in qs if qid in correct_ids)
        world_rows.append({"slug":w.slug,"title":w.title,"subtitle":w.subtitle,"icon":w.icon,"concepts":w.concepts,"done":done,"total_questions":len(qs),"progress":round(done/max(1,len(qs))*100)})
    attempts=db.scalars(select(m.QuizAttempt).where(m.QuizAttempt.user_id==user.id)).all()
    right=sum(a.correct for a in attempts)
    tasks=db.scalars(select(m.PlannerTask).where(m.PlannerTask.user_id==user.id).order_by(m.PlannerTask.due_date).limit(6)).all()
    today=utcnow().date().isoformat()
    settings=user.settings or {}
    quests=[
        {"id":"daily_quiz","title":"Solve one quiz question","xp":10,"done":any(a.correct and a.created_at.date()==utcnow().date() for a in attempts)},
        {"id":"plan","title":"Add a study task","xp":5,"done":db.scalar(select(func.count(m.PlannerTask.id)).where(m.PlannerTask.user_id==user.id,m.PlannerTask.created_at>=datetime.combine(utcnow().date(),datetime.min.time())))>0},
        {"id":"library","title":"Upload a class resource","xp":10,"done":db.scalar(select(func.count(m.Material.id)).where(m.Material.user_id==user.id))>0},
    ]
    return {"user":user_dict(user),**level_info(user.xp),"worlds":world_rows,"badges":earned_badges(db,user),
            "quests":quests,"recent_tasks":[task_dict(t) for t in tasks],"stats":{"correct_answers":right,"quiz_attempts":len(attempts),"materials":db.scalar(select(func.count(m.Material.id)).where(m.Material.user_id==user.id)),"flashcards_due":db.scalar(select(func.count(m.Flashcard.id)).where(m.Flashcard.user_id==user.id,m.Flashcard.due_at<=utcnow()))}}

@app.get("/api/worlds")
def get_worlds(db: Session=Depends(get_db), user: m.User=Depends(current_user)):
    result=[]
    for w in db.scalars(select(m.World).order_by(m.World.position)).all():
        result.append({"slug":w.slug,"title":w.title,"subtitle":w.subtitle,"icon":w.icon,"concepts":w.concepts})
    return result

@app.get("/api/worlds/{slug}")
def get_world(slug: str, db: Session=Depends(get_db), user: m.User=Depends(current_user)):
    w=db.scalar(select(m.World).where(m.World.slug==slug))
    if not w: raise HTTPException(404,"World not found")
    qcount=db.scalar(select(func.count(m.QuizQuestion.id)).where(m.QuizQuestion.world_slug==slug))
    return {"slug":w.slug,"title":w.title,"subtitle":w.subtitle,"icon":w.icon,"concepts":w.concepts,"question_count":qcount}


# ----------------------------- quiz/progress -------------------------------
@app.get("/api/quiz/questions")
def quiz_questions(world: str|None=None, topic: str|None=None, limit: int=Query(default=10,ge=1,le=30), db: Session=Depends(get_db), user: m.User=Depends(current_user)):
    query=select(m.QuizQuestion)
    if world: query=query.where(m.QuizQuestion.world_slug==world)
    if topic: query=query.where(m.QuizQuestion.topic==topic)
    return [public_question(q) for q in db.scalars(query.order_by(m.QuizQuestion.id).limit(limit)).all()]

@app.post("/api/quiz/answer")
def quiz_answer(body: QuizAnswer, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    q=db.get(m.QuizQuestion,body.question_id)
    if not q: raise HTTPException(404,"Question not found")
    if body.selected>=len(q.options): raise HTTPException(422,"Select one of the listed options.")
    correct=body.selected==q.answer
    already=db.scalar(select(m.QuizAttempt.id).where(m.QuizAttempt.user_id==user.id,m.QuizAttempt.question_id==q.id,m.QuizAttempt.correct.is_(True))) is not None
    xp=10 if correct and not already else 0
    db.add(m.QuizAttempt(user_id=user.id,question_id=q.id,selected=body.selected,correct=correct,xp_awarded=xp))
    user.xp+=xp
    db.commit()
    return {"correct":correct,"xp":xp,"already_mastered":already,"correct_index":q.answer,
            "explanation":q.explanation,"level":level_info(user.xp)["level"],"total_xp":user.xp}


# ----------------------------- python lab ----------------------------------
PYTHON_MISSIONS=[
    {"id":"py-01","title":"Hello, explorer","topic":"print()","difficulty":"starter","prompt":"Print the exact text: Hello, Semester Quest!","starter":"# Your first Python mission\n","hints":["Use print() to display text.","Put the message inside quotes."],"expected":"Hello, Semester Quest!"},
    {"id":"py-02","title":"Add two numbers","topic":"input & int","difficulty":"starter","prompt":"Read two integers from separate lines and print their sum.","starter":"a = int(input())\nb = int(input())\n","hints":["input() returns text.","Convert each input with int(), then add."],"expected":"sum"},
    {"id":"py-03","title":"Even or odd","topic":"conditionals","difficulty":"easy","prompt":"Read an integer and print Even when divisible by 2, otherwise Odd.","starter":"n = int(input())\n","hints":["The remainder operator is %.","Check n % 2 == 0."],"expected":"parity"},
    {"id":"py-04","title":"The largest of three","topic":"if-elif-else","difficulty":"easy","prompt":"Read three integers and print the largest value.","starter":"a, b, c = map(int, input().split())\n","hints":["Compare the values.","You can also use max(a, b, c)."],"expected":"max"},
    {"id":"py-05","title":"Count the vowels","topic":"for loop","difficulty":"medium","prompt":"Read one line and print how many vowels (a, e, i, o, u) it contains. Ignore case.","starter":"text = input().lower()\n","hints":["Loop through each character.","Count it when it is in 'aeiou'."],"expected":"vowels"},
    {"id":"py-06","title":"Factorial function","topic":"functions","difficulty":"medium","prompt":"Define factorial(n) and print factorial of the given non-negative integer.","starter":"def factorial(n):\n    # write your logic\n    pass\n\nn = int(input())\nprint(factorial(n))\n","hints":["The factorial of 0 is 1.","Multiply the numbers from 1 through n."],"expected":"factorial"},
    {"id":"py-07","title":"Multiplication table","topic":"for loop & range","difficulty":"medium","prompt":"Read an integer n and print its first 10 multiples, one per line.","starter":"n = int(input())\n","hints":["Use for i in range(1, 11).","Print n * i on each iteration."],"expected":"table"},
    {"id":"py-08","title":"Recursive sum","topic":"recursion","difficulty":"challenge","prompt":"Write a recursive function total(n) that returns 1 + 2 + ... + n. For n <= 0 return 0.","starter":"def total(n):\n    # base case and recursive case\n    pass\n\nprint(total(int(input())))\n","hints":["Base case: n <= 0 returns 0.","Recursive case: n + total(n - 1)."],"expected":"recursive_sum"},
    {"id":"py-09","title":"Electricity bill","topic":"conditionals & arithmetic","difficulty":"challenge","prompt":"Read units. Charge ₹4 per unit for first 100, ₹5 for next 100, ₹6 for next 100, and ₹7 above 300. Print the bill rounded to 1 decimal place.","starter":"units = int(input())\n","hints":["Use slabs with if/elif/else.","Only the units inside each slab use that slab's rate."],"expected":"bill"},
    {"id":"py-10","title":"Prime checker","topic":"loops & functions","difficulty":"challenge","prompt":"Read an integer n and print Prime or Not Prime.","starter":"n = int(input())\n","hints":["Numbers below 2 are not prime.","Try divisors up to the square root of n."],"expected":"prime"},
]

@app.get("/api/python/missions")
def python_missions(user: m.User=Depends(current_user)):
    return [{k:v for k,v in item.items() if k!="expected"} for item in PYTHON_MISSIONS]

@app.post("/api/python/run")
def python_run(body: dict[str,Any], user: m.User=Depends(current_user)):
    source=str(body.get("source","")); stdin=str(body.get("stdin",""))
    return engines.run_python(source,stdin)

@app.post("/api/python/missions/{mission_id}/check")
def python_mission_check(mission_id: str, body: dict[str,Any], user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    mission=next((x for x in PYTHON_MISSIONS if x["id"]==mission_id),None)
    if not mission: raise HTTPException(404,"Mission not found")
    source=str(body.get("source",""));
    # Check code through the isolated runner. A disabled runner cannot award a pass.
    sample_inputs={"py-01":"","py-02":"2\n3\n","py-03":"4\n","py-04":"2 9 4\n","py-05":"Semester Quest\n","py-06":"5\n","py-07":"3\n","py-08":"5\n","py-09":"250\n","py-10":"7\n"}
    result=engines.run_python(source,sample_inputs.get(mission_id,""))
    if result.get("error"):
        return {"passed":False,"result":result,"message":"Fix the error or enable the isolated Docker runner first."}
    expected={"py-01":"Hello, Semester Quest!","py-02":"5","py-03":"Even","py-04":"9","py-05":"4","py-06":"120","py-07":"3\n6\n9\n12\n15\n18\n21\n24\n27\n30","py-08":"15","py-09":"1150.0","py-10":"Prime"}
    passed=result["stdout"].strip()==expected.get(mission_id)
    settings=dict(user.settings or {}); cleared=set(settings.get("completed_python",[])); xp=0
    if passed and mission_id not in cleared:
        cleared.add(mission_id); settings["completed_python"]=sorted(cleared); user.settings=settings; user.xp+=25; xp=25
        db.commit()
    return {"passed":passed,"xp":xp,"message":"Mission cleared! +25 XP" if passed else "Output did not match the mission check.","result":result}


# ----------------------------- terminal lab --------------------------------
TERMINAL_MISSIONS=[
    {"id":"sh-01","title":"Build a project folder","xp":40,"brief":"Create quest/src, then create README.md, src/main.py and run.sh. Make run.sh executable.","check":"project"},
    {"id":"sh-02","title":"Find the errors","xp":25,"brief":"Search practice/log.txt for lines containing ERROR (case-sensitive).","check":"grep"},
    {"id":"sh-03","title":"Start tracking with Git","xp":40,"brief":"Initialise a Git repository, stage your files and create a commit.","check":"git"},
    {"id":"sh-04","title":"Write a summary","xp":25,"brief":"Create summary.txt in your home folder with at least one useful line of text.","check":"summary"},
    {"id":"sh-05","title":"Count log entries","xp":25,"brief":"Use a grep and wc pipeline to count the ERROR lines in practice/log.txt.","check":"count"},
    {"id":"sh-06","title":"Make a script executable","xp":25,"brief":"Create scripts/hello.sh and add executable permission.","check":"script"},
]

@app.get("/api/shell")
def shell_get(user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    row,state=shell_state(db,user); db.commit()
    return {"cwd":state["cwd"],"files":state["files"],"git":state["git"],"missions":TERMINAL_MISSIONS}

@app.post("/api/shell/run")
def shell_run(body: ShellIn, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    if body.command.count(";")>8: raise HTTPException(422,"Too many commands in one request.")
    row,state=shell_state(db,user)
    result=vshell.run_command(state,body.command)
    row.files=copy.deepcopy(state["files"]); row.cwd=state["cwd"]; row.git=copy.deepcopy(state["git"])
    flag_modified(row, "files"); flag_modified(row, "git")
    db.commit()
    return {"stdout":result["stdout"],"stderr":result["stderr"],"exit":result["exit"],"cwd":state["cwd"],"files":state["files"],"git":state["git"]}

@app.post("/api/shell/reset")
def shell_reset(user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    row,state=shell_state(db,user); clean=vshell.initial_state()
    row.files=clean["files"]; row.cwd=clean["cwd"]; row.git=clean["git"]
    db.commit(); return {"ok":True,"cwd":row.cwd,"files":row.files}

@app.post("/api/shell/missions/{mission_id}/check")
def terminal_mission_check(mission_id: str, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    mission=next((x for x in TERMINAL_MISSIONS if x["id"]==mission_id),None)
    if not mission: raise HTTPException(404,"Mission not found")
    row,state=shell_state(db,user); files=state["files"]; home="/home/student"
    checks={
        "project": all(p in files for p in [home+"/quest",home+"/quest/README.md",home+"/quest/src",home+"/quest/src/main.py",home+"/quest/run.sh"]) and files.get(home+"/quest/run.sh",{}).get("mode")=="755",
        "grep": True,
        "git": bool(state["git"].get("commits")),
        "summary": home+"/summary.txt" in files and len(files[home+"/summary.txt"].get("content","" ).strip())>0,
        "count": True,
        "script": home+"/scripts/hello.sh" in files and files.get(home+"/scripts/hello.sh",{}).get("mode")=="755",
    }
    # The grep/count tasks are terminal exercises: require a shell file artifact so completion is auditable.
    if mission_id=="sh-02": checks["grep"]=home+"/error_report.txt" in files and "ERROR" in files[home+"/error_report.txt"].get("content","")
    if mission_id=="sh-05": checks["count"]=home+"/error_count.txt" in files and files[home+"/error_count.txt"].get("content","").strip() in {"2","2  ","2\n"}
    cleared=bool(checks[mission["check"]]); settings=dict(user.settings or {}); completed=set(settings.get("completed_terminals",[])); xp=0
    if cleared and mission_id not in completed:
        completed.add(mission_id); settings["completed_terminals"]=sorted(completed); user.settings=settings; user.xp+=mission["xp"]; xp=mission["xp"]
    db.commit()
    return {"cleared":cleared,"first_clear":xp>0,"xp":xp,"message":"Mission cleared!" if cleared else "Not quite yet. Check the mission steps and try again."}


# ----------------------------- library / tutor -----------------------------
ALLOWED_EXT={".pdf",".docx",".pptx",".txt",".md",".csv",".json",".py",".java",".c",".cpp",".h",".html",".xml",".tex",".rst"}

@app.get("/api/materials")
def list_materials(user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    return [material_dict(x) for x in db.scalars(select(m.Material).where(m.Material.user_id==user.id).order_by(desc(m.Material.created_at))).all()]

@app.post("/api/materials")
async def upload_material(file: UploadFile=File(...), kind: str=Form(default="notes"), folder: str=Form(default="My uploads"), user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    filename=Path(file.filename or "upload").name
    ext=Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT: raise HTTPException(415,"This file type is not supported for text extraction.")
    raw=await file.read(MAX_UPLOAD_MB*1024*1024+1)
    if len(raw)>MAX_UPLOAD_MB*1024*1024: raise HTTPException(413,f"Upload limit is {MAX_UPLOAD_MB} MB.")
    try: extracted,pages=rag.extract_file(filename,raw)
    except Exception as exc: raise HTTPException(422,f"Could not read this file: {type(exc).__name__}.") from exc
    if not extracted.strip(): raise HTTPException(422,"No readable text was found in this file. Try a text-based PDF or DOCX/PPTX export.")
    user_dir=UPLOAD_DIR/str(user.id); user_dir.mkdir(parents=True,exist_ok=True)
    stored=f"{secrets.token_hex(12)}{ext}"; (user_dir/stored).write_bytes(raw)
    material=m.Material(user_id=user.id,filename=filename,stored_name=stored,kind=kind[:30],size=len(raw),pages=pages,folder=folder[:100],text_content=extracted,status="ready")
    db.add(material); db.commit(); db.refresh(material)
    # A first upload is a learning milestone.
    settings=dict(user.settings or {}); user.xp+=10; db.commit()
    return {**material_dict(material),"extracted_characters":len(extracted),"xp_awarded":10}

@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    material=owned_material(db,user,material_id)
    path=UPLOAD_DIR/str(user.id)/material.stored_name
    if path.exists(): path.unlink()
    db.query(m.Flashcard).filter(m.Flashcard.material_id==material.id).delete()
    db.delete(material); db.commit(); return {"ok":True}

@app.post("/api/tutor")
def tutor(body: TutorIn, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    docs=[{"id":x.id,"filename":x.filename,"text":x.text_content} for x in db.scalars(select(m.Material).where(m.Material.user_id==user.id)).all()]
    hits=rag.retrieve(body.message,docs,limit=5)
    citations=[{"material_id":h["material_id"],"filename":h["filename"],"text":rag.best_sentences(h["text"],body.message),"origin":"your upload"} for h in hits]
    if llm.available():
        context="\n\n".join(f"[{c['filename']}] {h['text']}" for c,h in zip(citations,hits))
        system="You are Semester Quest's friendly, concise study tutor. Explain concepts step by step at first-year undergraduate level. Use the supplied excerpts when relevant; never invent a citation. Clearly say when the uploaded material does not cover the question."
        reply=llm.chat([{"role":"system","content":system+"\n\nStudent's uploaded material:\n"+context},{"role":"user","content":body.message}],temperature=0.25,max_tokens=750)
        if reply:
            return {"reply":reply,"cites":citations,"engine":llm.engine_name(),"grounded":bool(hits)}
    if hits:
        excerpts="\n".join(f"• **{c['filename']}** — {c['text']}" for c in citations[:3])
        reply=("I found a few relevant passages in your uploaded class material:\n\n"+excerpts+
               "\n\nTry reading the cited section once, then ask me to break down a specific line or example. The built-in tutor is extractive right now; configure an OpenAI-compatible model in `.env` for generated explanations.")
        return {"reply":reply,"cites":citations,"engine":llm.engine_name(),"grounded":True}
    return {"reply":"I couldn't find a matching passage in your uploads yet. Upload the relevant lecture PDF, slides or notes and ask again. I can still help with a general explanation, but I won't label it as coming from your faculty material.\n\nFor generated explanations, configure an OpenAI-compatible model such as Ollama or another compatible endpoint in `.env`.","cites":[],"engine":llm.engine_name(),"grounded":False}


# ----------------------------- flashcards (SM-2) ----------------------------
@app.get("/api/flashcards")
def list_flashcards(due_only: bool=False, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    query=select(m.Flashcard).where(m.Flashcard.user_id==user.id)
    if due_only: query=query.where(m.Flashcard.due_at<=utcnow())
    cards=db.scalars(query.order_by(m.Flashcard.due_at)).all()
    return [{"id":c.id,"front":c.front,"back":c.back,"ease":c.ease,"interval":c.interval,"repetitions":c.repetitions,"due_at":c.due_at.isoformat(),"material_id":c.material_id} for c in cards]

@app.post("/api/flashcards/generate")
def generate_flashcards(body: MaterialGenerate, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    material=owned_material(db,user,body.material_id)
    if not material.text_content: raise HTTPException(422,"This material has no extracted text.")
    paragraphs=[p.strip() for p in re.split(r"\n+",material.text_content) if len(p.strip())>35]
    if not paragraphs: paragraphs=[s.strip() for s in re.split(r"(?<=[.!?])\s+",material.text_content) if len(s.strip())>35]
    cards=[]
    for paragraph in paragraphs[:12]:
        sentence=paragraph[:240]
        front="Explain this idea from "+material.filename+": "+sentence[:110]+("…" if len(sentence)>110 else "")
        back=sentence
        card=m.Flashcard(user_id=user.id,material_id=material.id,front=front,back=back)
        db.add(card); cards.append(card)
    db.commit()
    return {"created":len(cards),"message":"Draft flashcards created from extracted text. Review and edit them as needed."}

@app.post("/api/flashcards/{card_id}/review")
def review_flashcard(card_id: int, body: FlashcardReview, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    card=db.scalar(select(m.Flashcard).where(m.Flashcard.id==card_id,m.Flashcard.user_id==user.id))
    if not card: raise HTTPException(404,"Flashcard not found")
    grade=body.grade
    if grade<3:
        card.repetitions=0; card.interval=1
    else:
        if card.repetitions==0: card.interval=1
        elif card.repetitions==1: card.interval=6
        else: card.interval=max(1,round(card.interval*card.ease))
        card.repetitions+=1
    card.ease=max(1.3,card.ease+(0.1-(5-grade)*(0.08+(5-grade)*0.02)))
    card.last_grade=grade; card.due_at=utcnow()+timedelta(days=card.interval)
    db.commit()
    return {"id":card.id,"interval":card.interval,"ease":round(card.ease,2),"repetitions":card.repetitions,"due_at":card.due_at.isoformat()}


# ----------------------------- planner / CGPA -------------------------------
@app.get("/api/planner")
def get_planner(user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    return [task_dict(t) for t in db.scalars(select(m.PlannerTask).where(m.PlannerTask.user_id==user.id).order_by(m.PlannerTask.due_date,m.PlannerTask.id)).all()]

@app.post("/api/planner")
def add_task(body: TaskIn, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    if body.due_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",body.due_date): raise HTTPException(422,"Due date must use YYYY-MM-DD.")
    task=m.PlannerTask(user_id=user.id,title=body.title.strip(),subject=body.subject,due_date=body.due_date,priority=body.priority)
    db.add(task); db.commit(); db.refresh(task); return task_dict(task)

@app.patch("/api/planner/{task_id}")
def update_task(task_id: int, body: TaskUpdate, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    task=db.scalar(select(m.PlannerTask).where(m.PlannerTask.id==task_id,m.PlannerTask.user_id==user.id))
    if not task: raise HTTPException(404,"Task not found")
    for key,value in body.model_dump(exclude_unset=True).items(): setattr(task,key,value)
    db.commit(); return task_dict(task)

@app.delete("/api/planner/{task_id}")
def delete_task(task_id: int, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    task=db.scalar(select(m.PlannerTask).where(m.PlannerTask.id==task_id,m.PlannerTask.user_id==user.id))
    if not task: raise HTTPException(404,"Task not found")
    db.delete(task); db.commit(); return {"ok":True}

@app.get("/api/settings/grade-scale")
def get_grade_scale(user: m.User=Depends(current_user)):
    settings=user.settings or {}; bands=settings.get("grade_scale",[])
    return {"bands":bands,"target_cgpa":settings.get("target_cgpa",9.0),"configured":bool(bands)}

@app.put("/api/settings/grade-scale")
def put_grade_scale(body: GradeScaleIn, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    bands=sorted([x.model_dump() for x in body.bands],key=lambda x:x["min"])
    if bands[0]["min"]>0: raise HTTPException(422,"Your lowest grade band should start at 0%.")
    settings=dict(user.settings or {}); settings["grade_scale"]=bands; settings["target_cgpa"]=body.target_cgpa; user.settings=settings
    db.commit(); return {"bands":bands,"target_cgpa":body.target_cgpa,"configured":True}

@app.get("/api/courses")
def get_courses(user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    rows=db.scalars(select(m.Course).where(m.Course.user_id==user.id)).all()
    return [{"id":c.id,"name":c.name,"credits":c.credits,"percentage":c.percentage} for c in rows]

@app.post("/api/courses")
def add_course(body: CourseIn, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    c=m.Course(user_id=user.id,name=body.name,credits=body.credits,percentage=body.percentage); db.add(c); db.commit(); db.refresh(c)
    return {"id":c.id,"name":c.name,"credits":c.credits,"percentage":c.percentage}

@app.delete("/api/courses/{course_id}")
def delete_course(course_id: int, user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    c=db.scalar(select(m.Course).where(m.Course.id==course_id,m.Course.user_id==user.id))
    if not c: raise HTTPException(404,"Course not found")
    db.delete(c); db.commit(); return {"ok":True}

@app.get("/api/performance/cgpa")
def cgpa(user: m.User=Depends(current_user), db: Session=Depends(get_db)):
    settings=user.settings or {}; bands=settings.get("grade_scale",[])
    courses=db.scalars(select(m.Course).where(m.Course.user_id==user.id)).all()
    if not bands: return {"configured":False,"cgpa":None,"message":"Add the official grade-point bands from your university before calculating CGPA."}
    total=0.0; credits=0.0; rows=[]
    for c in courses:
        eligible=[b for b in bands if c.percentage>=b["min"]]
        point=(eligible[-1]["gp"] if eligible else bands[0]["gp"])
        total+=point*c.credits; credits+=c.credits
        rows.append({"name":c.name,"credits":c.credits,"percentage":c.percentage,"grade_point":point})
    return {"configured":True,"cgpa":round(total/credits,2) if credits else None,"total_credits":credits,"target_cgpa":settings.get("target_cgpa",9.0),"courses":rows}


# ----------------------------- app shell -----------------------------------
@app.get("/", include_in_schema=False)
def index():
    path=STATIC_DIR/"index.html"
    if path.exists(): return FileResponse(path)
    return {"message":"Semester Quest frontend is not built yet. Run the frontend build or open /docs."}

@app.get("/{path:path}", include_in_schema=False)
def spa_fallback(path: str):
    # Keep API/docs and missing static resources out of the SPA fallback.
    if path.startswith(("api/","docs","redoc","openapi.json","assets/")): raise HTTPException(404,"Not found")
    index_path=STATIC_DIR/"index.html"
    if index_path.exists(): return FileResponse(index_path)
    raise HTTPException(404,"Not found")
