#!/usr/bin/env python3
import requests, random, string, time, sys, re, os, webbrowser, subprocess, secrets, ctypes
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from collections import Counter
from datetime import datetime

LETTERS = string.ascii_lowercase
DIGITS  = string.digits
CHARSET = LETTERS + DIGITS
NUMBERS_ONLY = DIGITS
VOWELS  = set('aeiou')
MAX_WORKERS = 10
REQUEST_DELAY = 0.15

COMMON_BIGRAMS = {
    'th','he','in','er','an','re','ed','on','es','st','en','at',
    'to','nt','wa','hi','it','nd','ha','ou','ea','ng','al','ar',
    've','ra','le','sa','ro','li','se','la','ne','el','ma','ch',
    'sh','io','ti','ci','si','be','me','de','no','te','co','ca',
    'pa','ta','lo','fo','ho','mo','ke','so','wo','pe','qu','ph',
    'gh','ck','ke','ly','ty','ry','ny','ll','ss','tt','ff','bb',
    'dd','gg','mm','nn','pp','rr'
}
NICE_ENDINGS = {'er','ly','ed','en','al','el','le','on','an','ar',
                'ck','ng','ty','ry','ke','ne','ll','ss','tt'}
NICE_STARTS = {'th','he','re','be','de','co','ca','pa','ma','ta',
               'lo','ro','ho','mo','ke','se','le','ne','te','ve',
               'ra','st','wh','ch','sh','fl','tr','br','gr','pr',
               'dr','fr','pl','cl','bl','gl','cr','sp','sw','tw'}
CONS = list('bcdfghjklmnpqrstvwxyz')

PATTERNS_4 = ['CVCV','VCVC','CVCC','CCVC','VCCV','CVC']
PATTERNS_5 = ['CVCVC','CVCV','VCVCV','VCCVC','CVCCV','CVCVV','VVCVC','CCVCC','CVC','VCVC']
PATTERNS_6 = ['CVCVCV','VCVCVC','CVCCVC','VCCVCC','CVCVCC','VCVCCV','CCVCVC','CVCCVV']

APP_NAME = "Scarn's Name Sniffer"
APP_VER = "2.4"
ROBLOX_REGISTRATION_URL = "https://www.roblox.com/CreateAccount"
SAVE_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
os.makedirs(SAVE_DIR, exist_ok=True)

# ── Secure account credential storage ─────────────────────────
PASSWORD_LOWER = "abcdefghijkmnopqrstuvwxyz"
PASSWORD_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
PASSWORD_DIGITS = "23456789"
PASSWORD_SYMBOLS = "!@#$%"


def generate_account_password(length=16):
    """Generate a strong password without ambiguous characters."""
    rng = secrets.SystemRandom()
    chars = [
        secrets.choice(PASSWORD_LOWER),
        secrets.choice(PASSWORD_UPPER),
        secrets.choice(PASSWORD_DIGITS),
        secrets.choice(PASSWORD_SYMBOLS),
    ]
    alphabet = PASSWORD_LOWER + PASSWORD_UPPER + PASSWORD_DIGITS + PASSWORD_SYMBOLS
    while len(chars) < max(12, length):
        chars.append(secrets.choice(alphabet))
    rng.shuffle(chars)
    return "".join(chars)


def save_windows_credential(username, password):
    """Save one Roblox credential in Windows Credential Manager.

    The password is stored as a Generic Credential under the current Windows
    account. Nothing is written to a plaintext password file.
    """
    if os.name != "nt":
        return False

    try:
        from ctypes import wintypes

        class FILETIME(ctypes.Structure):
            _fields_ = [
                ("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD),
            ]

        class CREDENTIALW(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        cred_write = advapi32.CredWriteW
        cred_write.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
        cred_write.restype = wintypes.BOOL

        blob = password.encode("utf-16-le")
        blob_buffer = ctypes.create_string_buffer(blob)

        credential = CREDENTIALW()
        credential.Flags = 0
        credential.Type = 1
        credential.TargetName = f"ScarnsNameSniffer:{username}"
        credential.Comment = f"Saved by {APP_NAME} v{APP_VER}"
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_ubyte))
        credential.Persist = 2
        credential.AttributeCount = 0
        credential.Attributes = None
        credential.TargetAlias = None
        credential.UserName = username

        return bool(cred_write(ctypes.byref(credential), 0))
    except Exception:
        return False


def make_autofill_payload(username, password, saved):
    return f"SCARN_AUTOFILL_V2|{username}|{password}|{1 if saved else 0}"

# ── Clipboard helper ──────────────────────────────────────────
def copy_to_clipboard(text):
    """Copy text to the Windows clipboard reliably."""
    text = str(text)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.Popen(["clip.exe"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, creationflags=creationflags)
        proc.communicate(text, timeout=5)
        if proc.returncode == 0: return True
    except Exception:
        pass
    try:
        proc = subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "[Console]::In.ReadToEnd() | Set-Clipboard"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, creationflags=creationflags)
        proc.communicate(text, timeout=5)
        if proc.returncode == 0: return True
    except Exception:
        pass
    return False

def print_available(name, extra=""):
    print(f"    -> \033[92m{name}\033[0m  {extra}")

# ── Scoring ──────────────────────────────────────────────────
def is_wordlike(name):
    name = name.lower(); n = len(name)
    if n < 3 or not any(c in VOWELS for c in name): return 0
    cur_cons = 0
    for c in name:
        if c in VOWELS: cur_cons = 0
        else: cur_cons += 1
        if cur_cons > 3: return 0
    score = sum(2 for i in range(n-1) if name[i:i+2] in COMMON_BIGRAMS)
    if n >= 2 and name[-2:] in NICE_ENDINGS: score += 3
    if n >= 3 and name[-3:] in ('ing','ion','ent','ive','ble','ght'): score += 4
    if name[:2] in NICE_STARTS: score += 2
    vc = sum(1 for c in name if c in VOWELS)
    if vc in (2,3): score += 2
    elif vc in (1,4): score += 1
    dc = sum(1 for c in name if c in DIGITS)
    if dc > 2: score -= 2
    elif dc == 0: score += 1
    if n >= 4 and all((name[i] in VOWELS) != (name[i+1] in VOWELS) for i in range(n-1)): score += 3
    ugly = {'xz','zx','xq','qx','qq','zz','jj','vv','ww','yy','kk','hx','xj','jz','zq','qj'}
    for i in range(n-1):
        if name[i:i+2] in ugly: score -= 3
    return max(0, score)

def is_aesthetic(name): return is_wordlike(name) >= 5

def generate_aesthetic(length=5):
    if length < 3: return ''.join(random.choices(LETTERS, k=length))
    pattern_map = {4: PATTERNS_4, 5: PATTERNS_5, 6: PATTERNS_6}
    usable = pattern_map.get(length, []) or [p for p in (PATTERNS_4+PATTERNS_5+PATTERNS_6) if abs(len(p)-length) <= 1]
    if not usable: usable = PATTERNS_5
    name_chars=[]
    for ch in random.choice(usable):
        name_chars.append(random.choice(CONS) if ch == 'C' else random.choice(list(VOWELS)) if ch == 'V' else ch)
    result=''.join(name_chars)[:length]
    while len(result)<length: result += random.choice(LETTERS)
    leet={'a':'4','e':'3','i':'1','o':'0','s':'5','t':'7'}
    if random.random()<0.25:
        idx=random.randrange(len(result))
        if result[idx] in leet and random.random()<0.5:
            lst=list(result); lst[idx]=leet[result[idx]]; result=''.join(lst)
    return result

def generate_random(length=5, charset=None): return ''.join(random.choices(charset or CHARSET, k=length))

def generate_from_word(word, length=5):
    word=word.strip().lower()
    if not word: return None
    if len(word)==length: return word
    if len(word)<length: return word + ''.join(random.choices(CHARSET, k=length-len(word)))
    return word[:length]

def save_results(names, mode_desc="batch", extra=""):
    timestamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"); filename=f"sniff_{timestamp}.txt"; filepath=os.path.join(SAVE_DIR,filename)
    with open(filepath,'w') as f:
        f.write(f"{APP_NAME} v{APP_VER}\nMode: {mode_desc}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*40}\n")
        for name in names: f.write(f"{name}\n")
        if extra: f.write(f"\n{extra}\n")
        f.write("\n--- made by scarn ---\n")
    print(f"\n  [SAVED] Results written to: {filepath}"); return filepath

def open_registration_page(name=None):
    if not name:
        try: webbrowser.open_new_tab(ROBLOX_REGISTRATION_URL); print("    Opening Roblox Create Account...")
        except Exception as e: print(f"    Could not open browser: {e}")
        return
    password=generate_account_password(); saved=save_windows_credential(name,password); copied=copy_to_clipboard(make_autofill_payload(name,password,saved))
    print(f"    Saved '{name}' securely in Windows Credential Manager." if saved else "    Warning: Windows Credential Manager save failed.")
    print("    Prepared one-time autofill handoff for the browser companion." if copied else "    Clipboard handoff failed; browser autofill may need manual input.")
    try:
        webbrowser.open_new_tab(ROBLOX_REGISTRATION_URL); print("    Opening Roblox Create Account..."); print("    Companion v2.4 will fill username/password and clear the clipboard handoff.")
    except Exception as e: print(f"    Could not open browser: {e}")

def open_signup_pages(names, max_tabs=10):
    selected=list(names[:max_tabs])
    if not selected: return
    print("    Bulk mode opens signup tabs only. Use single-name claim mode for secure password saving.")
    for i,_name in enumerate(selected):
        try:
            if i==0: webbrowser.open_new(ROBLOX_REGISTRATION_URL)
            else: webbrowser.open_new_tab(ROBLOX_REGISTRATION_URL)
        except Exception: pass

TOKEN_LOCK=Lock(); CSRF_TOKEN=None; SESH=requests.Session(); SESH.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
def get_csrf_token():
    global CSRF_TOKEN
    try:
        resp=SESH.post("https://auth.roblox.com/v2/logout",timeout=10); tok=resp.headers.get("x-csrf-token")
        if tok: CSRF_TOKEN=tok; return tok
        resp2=SESH.get("https://www.roblox.com/",timeout=10); m=re.search(r'data-token="([^"]+)"',resp2.text)
        if m: CSRF_TOKEN=m.group(1); return m.group(1)
    except: pass
    return None
def ensure_token():
    global CSRF_TOKEN
    # Fast path: once initialized, concurrent validators avoid the lock.
    if CSRF_TOKEN:
        return CSRF_TOKEN
    with TOKEN_LOCK:
        if CSRF_TOKEN:
            return CSRF_TOKEN
        return get_csrf_token()
def refresh_token():
    with TOKEN_LOCK: return get_csrf_token()
def check_username(name):
    url="https://auth.roblox.com/v1/usernames/validate"; params={"request.username":name,"request.context":"Signup","request.birthday":"2000-01-01"}; token=ensure_token(); headers={"x-csrf-token":token} if token else {}
    try:
        resp=SESH.get(url,params=params,headers=headers,timeout=10)
        if resp.status_code==403:
            t2=refresh_token()
            if t2: headers["x-csrf-token"]=t2; resp=SESH.get(url,params=params,headers=headers,timeout=10)
        if resp.status_code==429:return(name,"ratelimited")
        if resp.status_code==403:return(name,"csrf_blocked")
        if resp.status_code!=200:return(name,f"http_{resp.status_code}")
        data=resp.json(); msg=data.get("message",""); code=data.get("code")
        if "Username is valid" in msg or "Valid username" in msg:return(name,"available")
        if "already in use" in msg or "AlreadyInUse" in msg:return(name,"taken")
        if "not appropriate" in msg or "inappropriate" in msg:return(name,"inappropriate")
        if "start or end with" in msg or "cannot start" in msg:return(name,"invalid_format")
        if code==0:return(name,"available")
        if code in(1,4):return(name,"taken")
        if code==2:return(name,"invalid_length")
        if code==3:return(name,"inappropriate")
        return(name,f"unknown({msg[:40]})")
    except requests.exceptions.RequestException as e:return(name,f"error({e})")
def check_username_v2(name):
    url="https://auth.roblox.com/v2/usernames/validate"; params={"request.username":name,"request.birthday":"04/15/2002","request.context":"Signup"}; token=ensure_token(); headers={"x-csrf-token":token} if token else {}
    try:
        resp=SESH.get(url,params=params,headers=headers,timeout=10)
        if resp.status_code==403:
            t2=refresh_token()
            if t2: headers["x-csrf-token"]=t2; resp=SESH.get(url,params=params,headers=headers,timeout=10)
        if resp.status_code!=200:return(name,None)
        c=resp.json().get("code","")
        if "ValidUsername" in c:return(name,"available")
        if "AlreadyInUseError" in c:return(name,"taken")
        return(name,None)
    except:return(name,None)
def smart_check(name):
    r=check_username(name)
    if r[1] and (r[1].startswith("unknown") or r[1].startswith("error(")):
        r2=check_username_v2(name)
        if r2[1] is not None:return r2
    return r
p_lock=Lock()
def p_prog(name,status,found,total):
    with p_lock:
        mark="AVAILABLE <<<<" if status=="available" else "taken" if status=="taken" else (status or "?")[:25]; sys.stdout.write(f"\r  [{total:>4}] {name:<8} -> {mark:<30}"); sys.stdout.flush()
def pick_length():
    l=input("Name length? [4/5/6] (default 5): ").strip(); return int(l) if l in('4','6') else 5
def get_tab_count():
    ans=input("  Max browser tabs to open? (default 10, 0 to skip): ").strip()
    try:return max(0,int(ans))
    except:return 10
def claim_available_name(names):
    unique_names=list(dict.fromkeys(names))
    if not unique_names:return
    print("\n  CLAIM A NAME\n  "+"-"*36)
    for i,name in enumerate(unique_names,1):print(f"  [{i:>2}] {name}")
    while True:
        choice=input("\n  Choose a number to claim, [b] bulk open, or Enter to skip: ").strip().lower()
        if not choice:return
        if choice=='b': open_signup_pages(unique_names,get_tab_count()); return
        if choice.isdigit():
            idx=int(choice)-1
            if 0<=idx<len(unique_names):open_registration_page(unique_names[idx]); return
        print(f"  Enter a number from 1 to {len(unique_names)}, 'b', or press Enter to skip.")

def manual_lookup_mode():
    print("\n--- Manual Lookup Mode ---\nType usernames to check one at a time. Type 'done' to finish.\n"); found=[]; checked=[]
    while True:
        name=input("  Check name: ").strip()
        if not name or name.lower()=='done':break
        if not re.match(r'^[a-zA-Z0-9_]+$',name):print("    Invalid (letters, numbers, underscores only)");continue
        _,status=smart_check(name.lower());checked.append((name,status))
        if status=="available":print(f"    -> \033[92m{name.lower()}\033[0m: AVAILABLE!");found.append(name.lower())
        elif status=="taken":print(f"    -> {name}: Taken")
        else:print(f"    -> {name}: {status}")
    print(f"\n{'='*55}\n  MANUAL LOOKUP RESULTS\n{'='*55}")
    for n,s in checked: print(f"    \033[92m{n:<15}\033[0m -> AVAILABLE <<<<" if s=="available" else f"    {n:<15} -> {s}")
    if found:
        claim_available_name(found); ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
        if ans2!='n':save_results(found,"manual-lookup")
    print("\n--- made by scarn ---\n")

def wordlist_mode(length):
    path=input("Path to wordlist file: ").strip().replace('"','')
    if not os.path.exists(path):print(f"  File not found: {path}");return
    with open(path,'r',encoding='utf-8',errors='ignore') as f:words=[w.strip() for w in f.readlines() if w.strip()]
    variations=list(set(filter(None,[generate_from_word(w,length) for w in words])));print(f"  Loaded {len(words)} words from file\n  Generated {len(variations)} unique {length}-char variations\n\nChecking {len(variations)} names...\n")
    res=[]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for i,f in enumerate(as_completed({ex.submit(smart_check,n):n for n in variations})):
            res.append(f.result());n,s=res[-1];p_prog(n,s,len([r for r in res if r[1]=="available"]),i+1)
            if(i+1)%MAX_WORKERS==0:time.sleep(REQUEST_DELAY)
    av=[n for n,s in res if s=="available"];aest=[n for n in av if is_aesthetic(n)];rand=[n for n in av if not is_aesthetic(n)]
    print(f"\n\n{'='*55}\n  WORDLIST RESULTS ({length} chars) - Available: {len(av)}/{len(variations)}\n{'='*55}")
    if aest:
        print(f"\n  AESTHETIC ({len(aest)}):")
        for n in aest:print_available(n,f"({is_wordlike(n)}/10)")
    if rand:
        print(f"\n  RANDOM ({len(rand)}):")
        for n in rand:print_available(n)
    if av:
        claim_available_name(av);ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
        if ans2!='n':save_results(av,"wordlist",f"Source: {path}")
    print("\n--- made by scarn ---\n")

if __name__=="__main__":
    try:
        print(f"{APP_NAME} v{APP_VER}".center(55));print("(Roblox username generator + availability checker)".center(55));print();print("Fetching CSRF token...",end=" ");tok=get_csrf_token();print(f"{'OK' if tok else 'FAILED'}\n")
        mode=input("Mode: [s]can [g]enerate [a]esthetic-only [m]anual [w]ordlist? ").strip().lower()
        if mode=='m':manual_lookup_mode()
        elif mode=='w':wordlist_mode(pick_length())
        elif mode=='a':
            length=pick_length();target=int(input("How many aesthetic names to find? ") or "5");max_c=int(input("Max checks? ") or "500");found=[];total=0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                while len(found)<target and total<max_c:
                    bs=min(MAX_WORKERS,max_c-total);names=[generate_aesthetic(length) for _ in range(bs)]
                    for f in as_completed({ex.submit(smart_check,n):n for n in names}):
                        n,s=f.result();total+=1
                        if s=="available":found.append(n)
                        p_prog(n,s,len(found),total)
                    time.sleep(REQUEST_DELAY)
            print(f"\n\n{'='*55}\n  AESTHETIC AVAILABLE ({length} chars): {len(found)}\n{'='*55}")
            for n in found:print_available(n)
            if found:
                claim_available_name(found);ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2!='n':save_results(found,f"aesthetic-{length}char")
            print("\n--- made by scarn ---\n")
        elif mode=='s':
            length=pick_length();target=int(input("How many names to find? ") or "5");print("Charset options:\n  [L] Letters only (a-z)\n  [M] Mixed letters+digits (default)\n  [N] Numbers only (0-9)");cs_in=input("Choose: ").strip().lower();cs=LETTERS if cs_in=='l' else NUMBERS_ONLY if cs_in=='n' else CHARSET;max_c=int(input("Max checks? ") or "500");found=[];total=0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                while len(found)<target and total<max_c:
                    bs=min(MAX_WORKERS,max_c-total);names=[generate_random(length,cs) for _ in range(bs)]
                    for f in as_completed({ex.submit(smart_check,n):n for n in names}):
                        n,s=f.result();total+=1
                        if s=="available":found.append(n)
                        p_prog(n,s,len(found),total)
                    time.sleep(REQUEST_DELAY)
            print(f"\n\n{'='*55}\n  SCAN DONE - Checked {total}, found {len(found)} available ({length} chars)\n{'='*55}")
            for n in found:print_available(n)
            if not found:print("    (none found)")
            if found:
                claim_available_name(found);ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2!='n':save_results(found,f"scan-{length}char")
            print("\n--- made by scarn ---\n")
        else:
            length=pick_length();batch=int(input("How many names? ") or "100");aeh=input("Aesthetic/word-like? [y/N]: ").strip().lower()=='y';print("Charset options:\n  [L] Letters only (a-z)\n  [M] Mixed letters+digits (default)\n  [N] Numbers only (0-9)");cs_in=input("Choose: ").strip().lower();cs=LETTERS if cs_in=='l' else NUMBERS_ONLY if cs_in=='n' else CHARSET;names=[generate_aesthetic(length) if aeh else generate_random(length,cs) for _ in range(batch)];res=[]
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                for i,f in enumerate(as_completed({ex.submit(smart_check,n):n for n in names})):
                    res.append(f.result());n,s=res[-1];p_prog(n,s,len([r for r in res if r[1]=="available"]),i+1)
                    if(i+1)%MAX_WORKERS==0:time.sleep(REQUEST_DELAY)
            av=[n for n,s in res if s=="available"];aest=[n for n in av if is_aesthetic(n)];rand=[n for n in av if not is_aesthetic(n)]
            print(f"\n\n{'='*55}\n  RESULTS ({length} chars) - Available: {len(av)}/{batch}\n{'='*55}")
            if aest:
                print(f"\n  AESTHETIC ({len(aest)}):")
                for n in aest:print_available(n,f"({is_wordlike(n)}/10)")
            if rand:
                print(f"\n  RANDOM ({len(rand)}):")
                for n in rand:print_available(n)
            if av:
                claim_available_name(av);ans2=input("  Save to desktop? [Y/n]: ").strip().lower()
                if ans2!='n':save_results(av,f"batch-{length}char")
            print("\n--- made by scarn ---\n")
        input("Press Enter to exit...")
    except KeyboardInterrupt:
        print("\n\nExiting.\n--- made by scarn ---");input("Press Enter to exit...")