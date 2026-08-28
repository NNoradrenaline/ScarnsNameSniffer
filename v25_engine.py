#!/usr/bin/env python3
"""Feature engine for Scarn's Name Sniffer v2.5."""
from __future__ import annotations
import csv, json, math, os, re, secrets, sqlite3, sys, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

APP_NAME = "ScarnsNameSniffer"
REPO = "NNoradrenaline/ScarnsNameSniffer"
GITHUB_LATEST_RELEASE = f"https://api.github.com/repos/{REPO}/releases/latest"
DEFAULT_WORKERS, MIN_WORKERS, MAX_WORKERS = 16, 4, 32
CACHE_TTLS = {"available": 900, "taken": 2592000, "inappropriate": 7776000, "invalid_format": 7776000, "invalid_length": 7776000}
DEFAULT_CACHE_TTL = 3600
BUILTIN_PRESETS = {
    "rare-4": {"description":"4-character letters only, clean filtering","length":4,"target":10,"max_checks":1000,"aesthetic":False,"filters":{"allow_digits":False,"allow_underscores":False,"max_digits":0,"must_start_letter":True,"must_contain_vowel":False,"avoid_repeats":True}},
    "clean-5": {"description":"5-character word-like names with no digits","length":5,"target":10,"max_checks":1000,"aesthetic":True,"filters":{"allow_digits":False,"allow_underscores":False,"max_digits":0,"must_start_letter":True,"must_contain_vowel":True,"avoid_repeats":True}},
    "mixed-6": {"description":"6-character mixed names with at most one digit","length":6,"target":10,"max_checks":1000,"aesthetic":False,"filters":{"allow_digits":True,"allow_underscores":False,"max_digits":1,"must_start_letter":True,"must_contain_vowel":False,"avoid_repeats":True}},
}

def utc_now_ts(): return time.time()
def utc_iso(ts=None): return datetime.fromtimestamp(ts or utc_now_ts(), tz=timezone.utc).isoformat()
def app_root(): return Path(sys.executable if getattr(sys,"frozen",False) else __file__).resolve().parent
def portable_mode():
    env=os.environ.get("SCARN_PORTABLE","").strip().lower()
    return env in {"1","true","yes","on"} or (app_root()/"portable.flag").exists()
def state_dir():
    if portable_mode(): path=app_root()/"data"
    elif os.name=="nt": path=Path(os.environ.get("LOCALAPPDATA") or Path.home())/APP_NAME
    else: path=Path.home()/".scarns_name_sniffer"
    path.mkdir(parents=True,exist_ok=True); return path
def exports_dir():
    if portable_mode(): path=state_dir()/"exports"
    else:
        desktop=Path.home()/"Desktop"; path=desktop if desktop.exists() else state_dir()/"exports"
    path.mkdir(parents=True,exist_ok=True); return path
def db_path(): return state_dir()/"history.sqlite3"
def checkpoint_path(): return state_dir()/"resume.json"
def presets_path(): return state_dir()/"presets.json"
def excluded_patterns_path(): return state_dir()/"excluded_patterns.txt"
def ensure_support_files():
    p=excluded_patterns_path()
    if not p.exists(): p.write_text("# One substring or regular expression per line.\n# Blank lines and lines beginning with # are ignored.\n",encoding="utf-8")
    p2=presets_path()
    if not p2.exists(): p2.write_text(json.dumps(BUILTIN_PRESETS,indent=2),encoding="utf-8")


class UniqueSpaceGenerator:
    """Random-looking permutation of a finite username space.

    Every value is produced at most once without needing a growing duplicate
    set. Position-specific alphabets let the scanner enforce cheap structural
    rules such as "must start with a letter" before network work begins.
    """

    def __init__(self, alphabets, multiplier=None, offset=None, index=0):
        self.alphabets = [tuple(dict.fromkeys(chars)) for chars in alphabets]
        if not self.alphabets or any(not chars for chars in self.alphabets):
            raise ValueError("every position needs at least one character")
        self.radices = [len(chars) for chars in self.alphabets]
        self.size = math.prod(self.radices)
        self.index = int(index)

        if multiplier is None:
            if self.size <= 1:
                multiplier = 1
            else:
                while True:
                    candidate = secrets.randbelow(self.size - 1) + 1
                    if math.gcd(candidate, self.size) == 1:
                        multiplier = candidate
                        break
        if math.gcd(int(multiplier), self.size) != 1:
            raise ValueError("multiplier must be coprime with username-space size")

        self.multiplier = int(multiplier)
        self.offset = secrets.randbelow(self.size) if offset is None else int(offset) % self.size

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= self.size:
            raise StopIteration
        value = (self.multiplier * self.index + self.offset) % self.size
        self.index += 1

        chars = [""] * len(self.alphabets)
        for pos in range(len(self.alphabets) - 1, -1, -1):
            radix = self.radices[pos]
            value, digit = divmod(value, radix)
            chars[pos] = self.alphabets[pos][digit]
        return "".join(chars)

    def snapshot(self):
        return {
            "alphabets": ["".join(chars) for chars in self.alphabets],
            "multiplier": self.multiplier,
            "offset": self.offset,
            "index": self.index,
        }

    @classmethod
    def from_snapshot(cls, payload):
        return cls(
            payload["alphabets"],
            multiplier=payload["multiplier"],
            offset=payload["offset"],
            index=payload.get("index", 0),
        )

@dataclass
class FilterConfig:
    allow_digits: bool=True
    allow_underscores: bool=False
    max_digits: int=99
    must_start_letter: bool=True
    must_contain_vowel: bool=False
    avoid_repeats: bool=False
    @classmethod
    def from_dict(cls,data):
        data=data or {}; return cls(**{k:data[k] for k in cls.__dataclass_fields__ if k in data})

@dataclass
class ScanStats:
    started_at: float
    checked:int=0; network_checks:int=0; cache_hits:int=0; available:int=0; taken:int=0; inappropriate:int=0; other:int=0
    http_requests:int=0; bulk_requests:int=0; bulk_resolved:int=0; individual_validations:int=0
    def record(self,status,cached=False):
        self.checked+=1; self.cache_hits+=int(cached); self.network_checks+=int(not cached)
        if status=="available": self.available+=1
        elif status=="taken": self.taken+=1
        elif status=="inappropriate": self.inappropriate+=1
        else: self.other+=1
    @property
    def elapsed(self): return max(.001,time.time()-self.started_at)
    @property
    def speed(self): return self.checked/self.elapsed

class AdaptiveWorkers:
    def __init__(self,workers=DEFAULT_WORKERS,minimum=MIN_WORKERS,maximum=MAX_WORKERS):
        self.minimum=minimum; self.maximum=maximum; self.workers=max(minimum,min(maximum,workers)); self.healthy_streak=0
    def observe(self,statuses):
        """AIMD-style concurrency control: ramp on health, cut hard on 429."""
        statuses=list(statuses)
        if not statuses:return self.workers
        rl=sum(s=="ratelimited" for s in statuses)
        errors=sum(s=="csrf_blocked" or s.startswith("http_") or s.startswith("error(") for s in statuses)
        if rl:
            self.workers=max(self.minimum,max(1,self.workers//2)); self.healthy_streak=0
        elif errors/len(statuses)>=.25:
            self.workers=max(self.minimum,self.workers-4); self.healthy_streak=0
        else:
            self.healthy_streak+=1
            if self.healthy_streak>=2:
                self.workers=min(self.maximum,self.workers+4); self.healthy_streak=0
        return self.workers

class HistoryStore:
    def __init__(self,path=None):
        self.path=Path(path or db_path()); self.path.parent.mkdir(parents=True,exist_ok=True); self.conn=sqlite3.connect(self.path); self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA cache_size=-16000")
        self.conn.execute("PRAGMA mmap_size=268435456")
        self.query_chunk_size = 800
        try:
            for row in self.conn.execute("PRAGMA compile_options"):
                option = row[0]
                if option.startswith("MAX_VARIABLE_NUMBER="):
                    limit = int(option.split("=", 1)[1])
                    self.query_chunk_size = max(800, min(5000, limit - 16))
                    break
        except Exception:
            pass
        self._init_schema()
    def _init_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS checks(username TEXT PRIMARY KEY,status TEXT NOT NULL,checked_at REAL NOT NULL,score INTEGER NOT NULL DEFAULT 0,mode TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS idx_checks_status ON checks(status);
        CREATE INDEX IF NOT EXISTS idx_checks_checked_at ON checks(checked_at);
        CREATE TABLE IF NOT EXISTS watchlist(username TEXT PRIMARY KEY,added_at REAL NOT NULL,note TEXT NOT NULL DEFAULT '');
        """); self.conn.commit()
    def close(self): self.conn.close()
    def record_many(self,records,checked_at=None):
        rows=[]
        now=utc_now_ts() if checked_at is None else float(checked_at)
        for record in records:
            if isinstance(record,dict):
                rows.append((str(record["username"]).lower(),str(record["status"]),float(record.get("checked_at_ts",now)),int(record.get("score",0)),str(record.get("mode",""))))
            else:
                username,status,score,mode=record
                rows.append((str(username).lower(),str(status),now,int(score),str(mode)))
        if not rows:return
        self.conn.executemany("""INSERT INTO checks(username,status,checked_at,score,mode) VALUES(?,?,?,?,?) ON CONFLICT(username) DO UPDATE SET status=excluded.status,checked_at=excluded.checked_at,score=excluded.score,mode=excluded.mode""",rows)
        self.conn.commit()
    def record(self,username,status,score=0,mode=""):
        self.record_many([(username,status,score,mode)])
    def get(self,username): return self.conn.execute("SELECT * FROM checks WHERE username=?",(username.lower(),)).fetchone()
    def cached_status_many(self,usernames,now=None):
        names=list(dict.fromkeys(str(name).lower() for name in usernames if name))
        if not names:return {}
        current=utc_now_ts() if now is None else float(now)
        result={}
        for offset in range(0,len(names),self.query_chunk_size):
            chunk=names[offset:offset+self.query_chunk_size]
            placeholders=",".join("?" for _ in chunk)
            rows=self.conn.execute(f"SELECT username,status,checked_at FROM checks WHERE username IN ({placeholders})",chunk).fetchall()
            for row in rows:
                ttl=ttl_for_status(row["status"])
                if ttl>0 and current-float(row["checked_at"])<=ttl:
                    result[row["username"]]=row["status"]
        return result
    def cached_status(self,username,now=None):
        return self.cached_status_many([username],now).get(username.lower())
    def add_watch(self,username,note=""):
        self.conn.execute("""INSERT INTO watchlist(username,added_at,note) VALUES(?,?,?) ON CONFLICT(username) DO UPDATE SET note=excluded.note""",(username.lower(),utc_now_ts(),note)); self.conn.commit()
    def remove_watch(self,username): self.conn.execute("DELETE FROM watchlist WHERE username=?",(username.lower(),)); self.conn.commit()
    def watch_items(self): return self.conn.execute("""SELECT w.username,w.added_at,w.note,c.status,c.checked_at,c.score FROM watchlist w LEFT JOIN checks c ON c.username=w.username ORDER BY w.added_at DESC""").fetchall()
    def summary(self):
        total=self.conn.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
        statuses={r[0]:r[1] for r in self.conn.execute("SELECT status,COUNT(*) FROM checks GROUP BY status")}
        watches=self.conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        return {"total":total,"statuses":statuses,"watchlist":watches}

def ttl_for_status(status):
    if status=="ratelimited" or status=="csrf_blocked" or status.startswith("error(") or status.startswith("http_") or status.startswith("unknown"): return 0
    return CACHE_TTLS.get(status,DEFAULT_CACHE_TTL)
def load_banned_patterns(path=None):
    p=Path(path or excluded_patterns_path())
    if not p.exists():return []
    return [x.strip() for x in p.read_text(encoding="utf-8",errors="ignore").splitlines() if x.strip() and not x.strip().startswith("#")]
def matches_banned(name,patterns):
    lower=name.lower()
    for pattern in patterns:
        try:
            if re.search(pattern,lower,re.I):return True
        except re.error:
            if pattern.lower() in lower:return True
    return False
def passes_filters(name,config,banned_patterns=None):
    if not name:return False
    if not config.allow_digits and any(c.isdigit() for c in name):return False
    if not config.allow_underscores and "_" in name:return False
    if sum(c.isdigit() for c in name)>config.max_digits:return False
    if config.must_start_letter and not name[0].isalpha():return False
    if config.must_contain_vowel and not any(c.lower() in "aeiou" for c in name):return False
    if config.avoid_repeats and any(a==b for a,b in zip(name,name[1:])):return False
    if matches_banned(name,banned_patterns or []):return False
    return True
COMMON_BIGRAMS={"th","he","in","er","an","re","on","at","en","nd","st","to","it","ha","ou","ea","ng","al","ar","le","se","or","te","co","de","ra","ri","ne","ma","li","ro","ch","sh","tr","br","cr","dr","fr","gr","pr","cl","fl","gl","pl","sl","sp","sw","sk"}
UGLY_BIGRAMS={"qx","xq","qj","jq","zx","xz","vv","qq","jj","ww","zz"}
def score_username(name):
    if not name:return 0
    lower=name.lower(); score=45; digits=sum(c.isdigit() for c in lower); underscores=lower.count("_"); vowels=sum(c in "aeiou" for c in lower); alpha=sum(c.isalpha() for c in lower)
    if lower[0].isalpha():score+=6
    if lower[-1].isalpha():score+=3
    if 4<=len(lower)<=6:score+=5
    score+=min(18,sum(4 for i in range(len(lower)-1) if lower[i:i+2] in COMMON_BIGRAMS)); score-=sum(9 for i in range(len(lower)-1) if lower[i:i+2] in UGLY_BIGRAMS)
    if alpha and vowels:
        ratio=vowels/alpha
        if .25<=ratio<=.60:score+=10
        elif ratio<.15 or ratio>.75:score-=6
    if digits==0:score+=8
    elif digits==1:score+=2
    else:score-=min(18,(digits-1)*6)
    score-=underscores*5
    if len(set(lower))==len(lower):score+=4
    if any(a==b for a,b in zip(lower,lower[1:])):score-=7
    if re.search(r"[a-z]\d[a-z]\d|\d[a-z]\d[a-z]",lower):score-=5
    return max(0,min(100,int(score)))
def score_label(score):
    return "Excellent" if score>=90 else "Great" if score>=80 else "Good" if score>=65 else "Fair" if score>=45 else "Random"
def mutate_word(word,target_length=None,limit=200):
    word=re.sub(r"[^a-zA-Z0-9_]","",word.strip().lower())
    if not word:return []
    out={word}; leet={"a":"4","e":"3","i":"1","o":"0","s":"5","t":"7"}; subs={"c":"k","k":"c","s":"z","z":"s","v":"x","x":"v"}
    for i,ch in enumerate(word):
        if ch in leet:out.add(word[:i]+leet[ch]+word[i+1:])
        if ch in subs:out.add(word[:i]+subs[ch]+word[i+1:])
        out.add(word[:i]+word[i+1:])
    for suffix in ("x","z","v","r","n","s","7","1","0"):out.add(word+suffix)
    for prefix in ("x","v","z","i"):out.add(prefix+word)
    if len(word)>=2:out.add(word[:-1]+word[-1]*2);out.add(word[0]*2+word[1:])
    if target_length:
        expanded=set()
        for item in out:
            if len(item)==target_length:expanded.add(item)
            elif len(item)>target_length:expanded.add(item[:target_length])
            else:
                for suffix in ("x","z","7","1","0","v","r","n"):expanded.add((item+suffix*target_length)[:target_length])
        out=expanded
    return sorted(out,key=lambda n:(-score_username(n),n))[:limit]
def save_checkpoint(data):
    ensure_support_files()
    payload=dict(data)
    payload["saved_at"]=utc_iso()
    checkpoint_path().write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
    return checkpoint_path()
def load_checkpoint():
    p=checkpoint_path()
    if not p.exists():return None
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None
def clear_checkpoint():
    try:checkpoint_path().unlink()
    except FileNotFoundError:pass
def load_presets():
    ensure_support_files()
    try:
        data=json.loads(presets_path().read_text(encoding="utf-8"));return data if isinstance(data,dict) else dict(BUILTIN_PRESETS)
    except Exception:return dict(BUILTIN_PRESETS)
def save_presets(data):presets_path().write_text(json.dumps(data,indent=2),encoding="utf-8")
def export_results(results,prefix="scan"):
    rows=list(results);stamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S");base=exports_dir()/f"{prefix}_{stamp}"
    paths={"txt":str(base.with_suffix(".txt")),"csv":str(base.with_suffix(".csv")),"json":str(base.with_suffix(".json"))}
    with open(paths["txt"],"w",encoding="utf-8") as f:
        for row in rows:f.write(f"{row.get('username','')}\n")
    fields=["username","status","score","length","checked_at"]
    with open(paths["csv"],"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();[w.writerow(r) for r in rows]
    with open(paths["json"],"w",encoding="utf-8") as f:json.dump(rows,f,indent=2)
    return paths
def version_tuple(value):
    nums=re.findall(r"\d+",value or "");return tuple(int(n) for n in nums[:4]) or (0,)
def is_newer_version(current,latest):
    a=version_tuple(current);b=version_tuple(latest);width=max(len(a),len(b));return b+(0,)*(width-len(b))>a+(0,)*(width-len(a))
def format_duration(seconds):
    seconds=max(0,int(seconds));minutes,sec=divmod(seconds,60);hours,minutes=divmod(minutes,60);return f"{hours:02d}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:02d}:{sec:02d}"
def result_row(username,status,checked_at=None):
    return {"username":username,"status":status,"score":score_username(username),"length":len(username),"checked_at":checked_at or utc_iso()}
ensure_support_files()
