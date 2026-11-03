"""A deliberately small virtual shell. It never invokes a host shell or process."""
from __future__ import annotations
import re, shlex, posixpath
from copy import deepcopy

DEFAULT_FILES = {
    "/home/student": {"type":"dir", "content":"", "mode":"755"},
    "/home/student/practice": {"type":"dir", "content":"", "mode":"755"},
    "/home/student/practice/log.txt": {"type":"file", "content":"INFO app started\nERROR database timeout\nWARNING retrying\nERROR connection refused\n", "mode":"644"},
    "/home/student/practice/notes.txt": {"type":"file", "content":"Use grep to search text.\nUse pipes to combine commands.\n", "mode":"644"},
    "/home/student/README.md": {"type":"file", "content":"# My project\n\nSemester Quest practice workspace.\n", "mode":"644"},
}

def initial_state() -> dict:
    return {"files": deepcopy(DEFAULT_FILES), "cwd": "/home/student", "git": {"initialized": False, "staged": [], "commits": []}}

def _path(raw: str, cwd: str) -> str:
    if raw in {"~", "~/"}: raw = "/home/student"
    elif raw.startswith("~/"): raw = "/home/student/" + raw[2:]
    elif not raw.startswith("/"): raw = posixpath.join(cwd, raw)
    return posixpath.normpath(raw)

def _parent(path: str) -> str:
    return posixpath.dirname(path.rstrip("/")) or "/"

def _entry(state: dict, path: str):
    return state["files"].get(path)

def _descendants(state: dict, path: str) -> list[str]:
    prefix = path.rstrip("/") + "/"
    return sorted(k for k in state["files"] if k.startswith(prefix))

def _format_ls(state: dict, path: str, long: bool = False, all_: bool = False) -> str:
    node = _entry(state, path)
    if not node: return ""
    if node["type"] == "file":
        names = [posixpath.basename(path)]
        base = path
    else:
        names = [posixpath.basename(p) + ("/" if state["files"][p]["type"] == "dir" else "") for p in _descendants(state, path) if _parent(p) == path]
        base = path
    if not names: return ""
    if long:
        rows = []
        for name in names:
            full = name.rstrip("/") if node["type"] == "file" else posixpath.join(base, name.rstrip("/"))
            item = state["files"].get(full, {})
            mode = item.get("mode", "755" if item.get("type") == "dir" else "644")
            perms = ("d" if item.get("type") == "dir" else "-") + "rwxr-xr-x" if mode == "755" else ("d" if item.get("type") == "dir" else "-") + "rw-r--r--"
            size = len(item.get("content", ""))
            rows.append(f"{perms} 1 student student {size:>5} {name}")
        return "\n".join(rows)
    return "  ".join(names)

def _run_one(state: dict, command: str, piped: str = "") -> tuple[str, str, int]:
    try: args = shlex.split(command)
    except ValueError as e: return "", f"syntax error: {e}", 2
    if not args: return "", "", 0
    cmd, a = args[0], args[1:]
    cwd = state["cwd"]
    files = state["files"]
    if cmd in {"help", "?"}:
        return "Available commands: pwd, ls, cd, mkdir, touch, cat, echo, cp, mv, rm, chmod, grep, head, wc, find, git. This is a virtual practice shell.", "", 0
    if cmd == "pwd": return cwd + "\n", "", 0
    if cmd == "cd":
        target = _path(a[0] if a else "/home/student", cwd)
        if target in files and files[target]["type"] == "dir": state["cwd"] = target; return "", "", 0
        return "", f"cd: {a[0] if a else target}: No such directory", 1
    if cmd == "ls":
        long, all_ = "-l" in a or "-la" in a or "-al" in a, "-a" in a or "-la" in a or "-al" in a
        paths = [x for x in a if not x.startswith("-")] or [cwd]
        chunks=[]
        for raw in paths:
            p = _path(raw,cwd)
            if p not in files: return "", f"ls: cannot access '{raw}': No such file or directory", 1
            chunks.append(_format_ls(state,p,long,all_))
        return "\n".join(x for x in chunks if x) + ("\n" if any(chunks) else ""), "", 0
    if cmd == "mkdir":
        recursive = "-p" in a or "--parents" in a
        targets=[x for x in a if not x.startswith("-")]
        if not targets: return "", "mkdir: missing operand", 1
        for raw in targets:
            p=_path(raw,cwd)
            parent=_parent(p)
            if parent not in files and not recursive: return "", f"mkdir: cannot create directory '{raw}': No such file or directory", 1
            if recursive:
                cur="/"
                for part in p.strip("/").split("/"):
                    cur=posixpath.join(cur,part); files.setdefault(cur,{"type":"dir","content":"","mode":"755"})
            else:
                if p in files: return "", f"mkdir: cannot create directory '{raw}': File exists", 1
                files[p]={"type":"dir","content":"","mode":"755"}
        return "", "", 0
    if cmd == "touch":
        if not a: return "", "touch: missing file operand", 1
        for raw in a:
            p=_path(raw,cwd)
            if _parent(p) not in files: return "", f"touch: cannot touch '{raw}': No such directory", 1
            files.setdefault(p,{"type":"file","content":"","mode":"644"})
        return "", "", 0
    if cmd == "cat":
        paths=[x for x in a if not x.startswith("-")]
        if not paths:
            if piped: return piped, "", 0
            return "", "cat: missing file operand", 1
        out=[]
        for raw in paths:
            p=_path(raw,cwd); item=files.get(p)
            if not item or item["type"] != "file": return "", f"cat: {raw}: No such file or directory", 1
            out.append(item["content"])
        return "".join(out), "", 0
    if cmd == "echo": return " ".join(a) + "\n", "", 0
    if cmd in {"cp","mv"}:
        if len(a)<2: return "", f"{cmd}: missing destination operand", 1
        src,dst=_path(a[0],cwd),_path(a[1],cwd)
        if src not in files: return "", f"{cmd}: cannot stat '{a[0]}': No such file or directory", 1
        if _parent(dst) not in files: return "", f"{cmd}: cannot create '{a[1]}': No such directory", 1
        if files[src]["type"]=="dir": return "", f"{cmd}: directory operation is not supported in this practice shell", 1
        files[dst]=deepcopy(files[src])
        if cmd=="mv": del files[src]
        return "", "", 0
    if cmd == "rm":
        targets=[x for x in a if not x.startswith("-")]
        if "-r" in a or "-rf" in a or "--recursive" in a:
            return "", "refusing recursive deletion in the practice shell; remove individual files instead", 1
        if not targets: return "", "rm: missing operand", 1
        for raw in targets:
            p=_path(raw,cwd)
            if p not in files: return "", f"rm: cannot remove '{raw}': No such file or directory", 1
            if files[p]["type"]=="dir": return "", f"rm: cannot remove '{raw}': Is a directory", 1
            del files[p]
        return "", "", 0
    if cmd == "chmod":
        if len(a)<2: return "", "chmod: missing mode or file", 1
        mode,path=a[0],_path(a[1],cwd)
        if path not in files: return "", f"chmod: cannot access '{a[1]}': No such file", 1
        if mode=="+x": files[path]["mode"]="755"
        elif re.fullmatch(r"[0-7]{3,4}",mode): files[path]["mode"]=mode[-3:]
        else: return "", f"chmod: unsupported mode '{mode}'", 1
        return "", "", 0
    if cmd == "grep":
        ignore="-i" in a; line_no="-n" in a; count_mode="-c" in a
        rest=[x for x in a if x not in {"-i","-n","-c"}]
        if not rest: return "", "grep: missing pattern", 2
        pattern=rest[0]; target=rest[1:] 
        if target:
            texts=[]
            for raw in target:
                p=_path(raw,cwd); item=files.get(p)
                if not item or item["type"]!="file": return "", f"grep: {raw}: No such file or directory", 2
                texts.append(item["content"])
            text="\n".join(texts)
        else: text=piped
        if not text and not target: return "", "grep: missing input", 2
        rows=[]
        for i,line in enumerate(text.splitlines(),1):
            found=pattern.lower() in line.lower() if ignore else pattern in line
            if found: rows.append((f"{i}:" if line_no else "")+line)
        if count_mode: return f"{len(rows)}\n", "", 0
        return ("\n".join(rows)+("\n" if rows else "")), "", 0 if rows else 1
    if cmd == "head":
        n=10; rest=[]; i=0
        while i<len(a):
            if a[i] in {"-n","--lines"} and i+1<len(a):
                try:n=int(a[i+1]); i+=2; continue
                except ValueError: pass
            if re.fullmatch(r"-\d+",a[i]): n=int(a[i][1:]); i+=1; continue
            rest.append(a[i]); i+=1
        text=piped
        if rest:
            p=_path(rest[-1],cwd); item=files.get(p)
            if not item or item["type"]!="file": return "", f"head: cannot open '{rest[-1]}': No such file", 1
            text=item["content"]
        rows=text.splitlines()[:max(0,n)]
        return "\n".join(rows)+("\n" if rows else ""), "", 0
    if cmd == "wc":
        line_mode="-l" in a
        paths=[x for x in a if not x.startswith("-")]
        texts=[]
        if paths:
            for raw in paths:
                p=_path(raw,cwd); item=files.get(p)
                if not item or item["type"]!="file": return "", f"wc: {raw}: No such file", 1
                texts.append((raw,item["content"]))
        else: texts=[("",piped)]
        out=[]
        for name,text in texts:
            count=len(text.splitlines()) if line_mode else len(text.split())
            out.append(f"{count:>7}"+(f" {name}" if name else ""))
        return "\n".join(out)+"\n", "", 0
    if cmd == "find":
        base=_path(a[0],cwd) if a and not a[0].startswith("-") else cwd
        if base not in files or files[base]["type"]!="dir": return "", f"find: '{base}': No such directory", 1
        return "\n".join([base]+_descendants(state,base))+"\n", "", 0
    if cmd == "git":
        if not a: return "", "usage: git <command>", 2
        sub=a[0]; git=state["git"]
        if sub=="init": git.update({"initialized":True,"staged":[],"commits":[]}); return "Initialized empty Git repository in /home/student/.git/\n", "", 0
        if not git.get("initialized"): return "", "fatal: not a git repository (or any parent up to mount point)", 128
        if sub=="status":
            changed=[p for p in files if p.startswith("/home/student/") and files[p]["type"]=="file"]
            staged=set(git.get("staged",[])); unstaged=[posixpath.relpath(p,"/home/student") for p in changed if posixpath.relpath(p,"/home/student") not in staged]
            staged_names=sorted(staged)
            out="On branch main\n"
            out += "Changes to be committed:\n"+"".join(f"  new file:   {x}\n" for x in staged_names) if staged_names else out+"nothing added to commit yet\n"
            if unstaged: out+="Untracked files:\n"+"".join(f"  {x}\n" for x in unstaged)
            return out,"",0
        if sub=="add":
            if len(a)<2: return "", "Nothing specified, nothing added.", 1
            for raw in a[1:]:
                if raw==".": targets=[p for p in files if p.startswith("/home/student/") and files[p]["type"]=="file"]
                else: targets=[_path(raw,cwd)]
                for p in targets:
                    if p not in files or files[p]["type"]!="file": return "", f"fatal: pathspec '{raw}' did not match any files", 128
                    rel=posixpath.relpath(p,"/home/student")
                    if rel not in git["staged"]: git["staged"].append(rel)
            return "", "", 0
        if sub=="commit":
            msg="commit"
            if "-m" in a and a.index("-m")+1<len(a): msg=a[a.index("-m")+1]
            if not git.get("staged"): return "", "nothing to commit, working tree clean", 1
            git["commits"].append({"message":msg,"files":list(git["staged"])})
            git["staged"]=[]
            return f"[main {len(git['commits']):07x}] {msg}\n", "", 0
        if sub=="log":
            if not git.get("commits"): return "", "fatal: your current branch has no commits yet", 128
            return "\n".join(f"commit {i+1:040x}\n    {c['message']}" for i,c in reversed(list(enumerate(git["commits"]))))+"\n", "", 0
        return "", f"git: '{sub}' is not a git command", 1
    return "", f"{cmd}: command not found (this is a safe virtual shell; type help)", 127

def run_command(state: dict, command: str) -> dict:
    state.setdefault("files",deepcopy(DEFAULT_FILES)); state.setdefault("git",{"initialized":False,"staged":[],"commits":[]}); state.setdefault("cwd","/home/student")
    command=command.strip()
    if not command: return {"stdout":"","stderr":"","exit":0,"state":state}
    # Support simple && sequences. No command is ever passed to the host shell.
    outputs=[]; errors=[]; code=0
    for sequence in re.split(r"\s+&&\s+",command):
        # Handle a single output redirect for echo/cat-like output.
        if ">" in sequence and "|" not in sequence:
            left,dest=sequence.split(">",1); dest=dest.strip().lstrip(">")
            out,err,code=_run_one(state,left.strip())
            path=_path(dest.strip(),state["cwd"])
            if _parent(path) not in state["files"]: err=f"No such directory: {_parent(path)}"; code=1
            else: state["files"][path]={"type":"file","content":out,"mode":"644"}; out=""
        elif "|" in sequence:
            pipe=sequence.split("|"); value=""; err=""
            for part in pipe:
                value,err,code=_run_one(state,part.strip(),value)
                if code not in (0,1) and err: break
            out=value
        else: out,err,code=_run_one(state,sequence)
        outputs.append(out); 
        if err: errors.append(err)
        if code not in (0,1): break
    return {"stdout":"".join(outputs),"stderr":"\n".join(errors),"exit":code,"state":state}
