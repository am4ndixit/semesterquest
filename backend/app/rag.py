"""Lightweight BM25-style retrieval over a student's uploaded course material."""
from __future__ import annotations
import math, re
from collections import Counter

STOP = set("a an the and or of to in on for with is are was were be been it this that as at by from into your you we they their its not no can will how what when which who whom whose do does did have has had than then so if else also such these those there here about more most other some any each per via over under".split())

def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(t) > 1 and t not in STOP]

def chunk_text(text: str, max_words: int = 180, overlap: int = 30) -> list[str]:
    words = text.split()
    if not words: return []
    chunks=[]; start=0
    while start < len(words):
        end=min(len(words),start+max_words)
        chunks.append(" ".join(words[start:end]))
        if end == len(words): break
        start=max(start+1,end-overlap)
    return chunks

def retrieve(query: str, documents: list[dict], limit: int = 5) -> list[dict]:
    q=tokens(query)
    if not q: return []
    candidates=[]
    for doc in documents:
        text=doc.get("text","")
        chunks=chunk_text(text)
        for idx,chunk in enumerate(chunks):
            terms=tokens(chunk)
            if not terms: continue
            counts=Counter(terms)
            score=0.0
            for term in set(q):
                tf=counts[term]
                if tf:
                    score += (tf/(tf+1.2)) * (1.0 + math.log(1+len(q)/max(1,terms.count(term))))
            if score>0:
                candidates.append({"score":score,"text":chunk[:1200],"filename":doc["filename"],"material_id":doc["id"],"chunk":idx})
    return sorted(candidates,key=lambda x:x["score"],reverse=True)[:limit]

def extract_file(filename: str, raw: bytes) -> tuple[str,int]:
    ext=filename.lower().rsplit(".",1)[-1] if "." in filename else ""
    if ext in {"txt","md","csv","json","py","java","c","cpp","h","html","xml","tex","rst"}:
        return raw.decode("utf-8",errors="replace"), 0
    if ext == "pdf":
        from pypdf import PdfReader
        import io
        reader=PdfReader(io.BytesIO(raw))
        pages=[p.extract_text() or "" for p in reader.pages]
        return "\n\n".join(pages),len(reader.pages)
    if ext == "docx":
        from docx import Document
        import io
        doc=Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs),0
    if ext == "pptx":
        from pptx import Presentation
        import io
        prs=Presentation(io.BytesIO(raw)); parts=[]
        for n,slide in enumerate(prs.slides,1):
            parts.append(f"Slide {n}")
            for shape in slide.shapes:
                if getattr(shape,"has_text_frame",False): parts.append(shape.text)
        return "\n".join(parts),len(prs.slides)
    raise ValueError("Supported formats: PDF, DOCX, PPTX, TXT, MD, CSV, JSON and source-code files.")

def best_sentences(text: str, query: str, n: int = 3, maxlen: int = 360) -> str:
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",text) if s.strip()]
    q=set(tokens(query))
    if not sentences: return text[:maxlen]
    ranked=sorted(range(len(sentences)),key=lambda i:(-len(q & set(tokens(sentences[i]))),i))[:n]
    out=" ".join(sentences[i] for i in sorted(ranked))
    return out if len(out)<=maxlen else out[:maxlen].rsplit(" ",1)[0]+"…"
