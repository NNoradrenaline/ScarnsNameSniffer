#!/usr/bin/env python3
import requests, random, string, time, sys, re, os, webbrowser, subprocess
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
APP_VER = "2.1.1"
ROBLOX_REGISTRATION_URL = "https://www.roblox.com/NewLogin?mode=registration"
SAVE_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
os.makedirs(SAVE_DIR, exist_ok=True)

# ── Clipboard helper ──────────────────────────────────────────
def copy_to_clipboard(text):
    """Copy a Roblox username to the Windows clipboard reliably."""
    text = str(text)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        proc = subprocess.Popen(
            ["clip.exe"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
        proc.communicate(text, timeout=5)
        if proc.returncode == 0:
            return True
    except Exception:
        pass

    try:
        proc = subprocess.Popen(
            [
                "powershell.exe", "-NoProfile", "-NonInteractive",
                "-Command", "[Console]::In.ReadToEnd() | Set-Clipboard"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
        proc.communicate(text, timeout=5)
        if proc.returncode == 0:
            return True
    except Exception:
        pass

    try:
        with open(os.path.join(os.environ.get('TEMP', ''), '_sniff_last.txt'), 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception:
        pass
    return False

def print_available(name, extra=""):
    # v2.1: names are no longer terminal hyperlinks because Roblox does not
    # reliably preserve signup state through those links. Use the claim menu instead.
    print(f"    -> \033[92m{name}\033[0m  {extra}")

# ── Scoring ──────────────────────────────────────────────────
def is_wordlike(name):
    name = name.lower()
    n = len(name)
    if n < 3: return 0
    if not any(c in VOWELS for c in name): return 0
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

# ── Generators ────────────────────────────────────────────────
def generate_aesthetic(length=5):
    if length < 3: return ''.join(random.choices(LETTERS, k=length))
    pattern_map = {4: PATTERNS_4, 5: PATTERNS_5, 6: PATTERNS_6}
    usable = pattern_map.get(length, []) or [p for p in (PATTERNS_4+PATTERNS_5+PATTERNS_6) if abs(len(p)-length) <= 1]
    if not usable: usable = PATTERNS_5
    name_chars = []
    for ch in random.choice(usable):
        name_chars.append(random.choice(CONS) if ch == 'C' else random.choice(list(VOWELS)) if ch == 'V' else ch)
    result = ''.join(name_chars)[:length]
    while len(result) < length: result += random.choice(LETTERS)
    leet = {'a':'4','e':'3','i':'1','o':'0','s':'5','t':'7'}
    if random.random() < 0.25:
        idx = random.randrange(len(result))
        if result[idx] in leet and random.random() < 0.5:
            lst = list(result); lst[idx] = leet[result[idx]]; result = ''.join(lst)
    return result

def generate_random(length=5, charset=None):
    return ''.join(random.choices(charset or CHARSET, k=length))

def generate_from_word(word, length=5):
    word = word.strip().lower()
    if not word: return None
    if len(word) == length: return word
    if len(word) < length:
        suffix = ''.join(random.choices(CHARSET, k=length-len(word)))
        return word + suffix
    return word[:length]

# ── File saving ───────────────────────────────────────────────
def save_results(names, mode_desc="batch", extra=""):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"sniff_{timestamp}.txt"
    filepath = os.path.join(SAVE_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(f"{APP_NAME} v{APP_VER}\n")
        f.write(f"Mode: {mode_desc}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*40}\n")
        for name in names:
            f.write(f"{name}\n")
        if extra:
            f.write(f"\n{extra}\n")
        f.write(f"\n--- made by scarn ---\n")
    print(f"\n  [SAVED] Results written to: {filepath}")
    return filepath

def open_registration_page(name=None):
    """Copy one username and open Roblox's registration route."""
    if name:
        copied = copy_to_clipboard(name)
        if copied:
            print(f"    Copied '{name}' to clipboard. Paste it into Roblox with Ctrl+V.")
        else:
            print(f"    Username: {name}  (clipboard copy failed; copy it manually)")
    try:
        webbrowser.open_new_tab(ROBLOX_REGISTRATION_URL)
        print("    Opening Roblox registration...")
    except Exception as e:
        print(f"    Could not open browser: {e}")

def open_signup_pages(names, max_tabs=10):
    """Optional legacy bulk-open helper, now using the registration route."""
    count = min(len(names), max_tabs)
    if count == 0:
        return
    copied = copy_to_clipboard(names[0])
    if copied:
        print(f"    Opening {count} registration tab(s). '{names[0]}' is copied to clipboard.")
    else:
        print(f"    Opening {count} registration tab(s). Clipboard copy failed; copy '{names[0]}' manually.")
    for i in range(count):
        try:
            if i == 0:
                webbrowser.open_new(ROBLOX_REGISTRATION_URL)
            else:
                webbrowser.open_new_tab(ROBLOX_REGISTRATION_URL)
        except:
            pass

# ── Session & CSRF ────────────────────────────────────────────
TOKEN_LOCK = Lock()
CSRF_TOKEN = None
SESH = requests.Session()
SESH.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

def get_csrf_token():
    global CSRF_TOKEN
    try:
        resp = SESH.post("https://auth.roblox.com/v2/logout", timeout=10)
        tok = resp.headers.get("x-csrf-token")
        if tok: CSRF_TOKEN = tok; return tok
        resp2 = SESH.get("https://www.roblox.com/", timeout=10)
        m = re.search(r'data-token="([^"]+)"', resp2.text)
        if m: CSRF_TOKEN = m.group(1); return m.group(1)
    except: pass
    return None

def ensure_token():
    global CSRF_TOKEN
    with TOKEN_LOCK: return CSRF_TOKEN if CSRF_TOKEN else get_csrf_token()

def refresh_token():
    with TOKEN_LOCK: return get_csrf_token()

# ── Checking ──────────────────────────────────────────────────
def check_username(name):
    url = "https://auth.roblox.com/v1/usernames/validate"
    params = {"request.username":name,"request.context":"Signup","request.birthday":"2000-01-01"}
    token = ensure_token()
    headers = {"x-csrf-token":token} if token else {}
    try:
        resp = SESH.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 403:
            t2 = refresh_token()
            if t2: headers["x-csrf-token"] = t2; resp = SESH.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 429: return (name,"ratelimited")
        if resp.status_code == 403: return (name,"csrf_blocked")
        if resp.status_code != 200: return (name,f"http_{resp.status_code}")
        data = resp.json(); msg = data.get("message",""); code = data.get("code")
        if "Username is valid" in msg or "Valid username" in msg: return (name,"available")
        if "already in use" in msg or "AlreadyInUse" in msg: return (name,"taken")
        if "not appropriate" in msg or "inappropriate" in msg: return (name,"inappropriate")
        if "start or end with" in msg or "cannot start" in msg: return (name,"invalid_format")
        if code == 0: return (name,"available")
        if code in (1,4): return (name,"taken")
        if code == 2: return (name,"invalid_length")
        if code == 3: return (name,"inappropriate")
        return (name,f"unknown({msg[:40]})")
    except requests.exceptions.RequestException as e: return (name,f"error({e})")

def check_username_v2(name):
    url = "https://auth.roblox.com/v2/usernames/validate"
    params = {"request.username":name,"request.birthday":"04/15/2002","request.context":"Signup"}
    token = ensure_token(); headers = {"x-csrf-token":token} if token else {}
    try:
        resp = SESH.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 403:
            t2 = refresh_token()
            if t2: headers["x-csrf-token"] = t2; resp = SESH.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200: return (name,None)
        c = resp.json().get("code","")
        if "ValidUsername" in c: return (name,"available")
        if "AlreadyInUseError" in c: return (name,"taken")
        return (name,None)
    except: return (name,None)

def smart_check(name):
    r = check_username(name)
    if r[1] and (r[1].startswith("unknown") or r[1].startswith("error(")):
        r2 = check_username_v2(name)
        if r2[1] is not None: return r2
    return r

# ── Display ───────────────────────────────────────────────────
p_lock = Lock()
def p_prog(name,status,found,total):
    with p_lock:
        mark = "AVAILABLE <<<<" if status=="available" else "taken" if status=="taken" else (status or "?")[:25]
        sys.stdout.write(f"\r  [{total:>4}] {name:<8} -> {mark:<30}"); sys.stdout.flush()

def pick_length():
    l = input("Name length? [4/5/6] (default 5): ").strip()
    if l in ('4','6'): return int(l)
    return 5

def get_tab_count():
    """Ask user how many browser tabs they want to open (default 10)."""
    ans = input("  Max browser tabs to open? (default 10, 0 to skip): ").strip()
    try:
        n = int(ans)
        return max(0, n)
    except:
        return 10

def claim_available_name(names):
    """Let the user choose one available name, copy it, and open registration."""
    unique_names = list(dict.fromkeys(names))
    if not unique_names:
        return

    print("\n  CLAIM A NAME")
    print("  " + "-" * 36)
    for i, name in enumerate(unique_names, 1):
        print(f"  [{i:>2}] {name}")

    while True:
        choice = input("\n  Choose a number to claim, [b] bulk open, or Enter to skip: ").strip().lower()
        if not choice:
            return
        if choice == 'b':
            tabs = get_tab_count()
            open_signup_pages(unique_names, tabs)
            return
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(unique_names):
                chosen = unique_names[idx]
                open_registration_page(chosen)
                return
        print(f"  Enter a number from 1 to {len(unique_names)}, 'b', or press Enter to skip.")

# ── Manual Lookup Mode ────────────────────────────────────────
def manual_lookup_mode():
    print("\n--- Manual Lookup Mode ---")
    print("Type usernames to check one at a time. Type 'done' to finish.\n")
    found = []
    checked = []
    while True:
        name = input("  Check name: ").strip()
        if not name or name.lower() == 'done':
            break
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            print("    Invalid (letters, numbers, underscores only)")
            continue
        _, status = smart_check(name.lower())
        checked.append((name, status))
        if status == "available":
            copy_to_clipboard(name.lower())
            print(f"    -> \033[92m{name.lower()}\033[0m: AVAILABLE! [copied to clipboard]")
            found.append(name.lower())
        elif status == "taken":
            print(f"    -> {name}: Taken")
        else:
            print(f"    -> {name}: {status}")

    print(f"\n{'='*55}")
    print(f"  MANUAL LOOKUP RESULTS")
    print(f"{'='*55}")
    for n, s in checked:
        if s == "available":
            print(f"    \033[92m{n:<15}\033[0m -> AVAILABLE <<<<")
        else:
            print(f"    {n:<15} -> {s}")
    if found:
        claim_available_name(found)
        ans2 = input(f"  Save to desktop? [Y/n]: ").strip().lower()
        if ans2 != 'n': save_results(found, "manual-lookup")
    print("\n--- made by scarn ---\n")

# ── Wordlist Mode ─────────────────────────────────────────────
def wordlist_mode(length):
    path = input("Path to wordlist file: ").strip().replace('"', '')
    if not os.path.exists(path):
        print(f"  File not found: {path}")
        return
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        words = [w.strip() for w in f.readlines() if w.strip()]
    print(f"  Loaded {len(words)} words from file")
    variations = list(set(filter(None, [generate_from_word(w, length) for w in words])))
    print(f"  Generated {len(variations)} unique {length}-char variations")
    print(f"\nChecking {len(variations)} names...\n")
    res = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for i,f in enumerate(as_completed({ex.submit(smart_check,n):n for n in variations})):
            res.append(f.result()); n,s = res[-1]
            p_prog(n,s,len([r for r in res if r[1]=="available"]),i+1)
            if (i+1)%MAX_WORKERS==0: time.sleep(REQUEST_DELAY)
    av = [n for n,s in res if s=="available"]
    aest = [n for n in av if is_aesthetic(n)]
    rand = [n for n in av if not is_aesthetic(n)]
    print(f"\n\n{'='*55}")
    print(f"  WORDLIST RESULTS ({length} chars) - Available: {len(av)}/{len(variations)}")
    print(f"{'='*55}")
    if aest:
        print(f"\n  AESTHETIC ({len(aest)}):")
        for n in aest: print_available(n, f"({is_wordlike(n)}/10)")
    if rand:
        print(f"\n  RANDOM ({len(rand)}):")
        for n in rand: print_available(n)
    print(f"\n  TAKEN: {len([r for r in res if r[1]=='taken'])}")
    other = [r for r in res if r[1] not in ("available","taken")]
    if other:
        print("  OTHER:")
        for s,c in Counter(s for _,s in other).most_common(5):
            print(f"    {s}: {c}")
    if av:
        claim_available_name(av)
        ans2 = input(f"  Save to desktop? [Y/n]: ").strip().lower()
        if ans2 != 'n': save_results(av, "wordlist", f"Source: {path}")
    print("\n--- made by scarn ---\n")

# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        print(f"{APP_NAME} v{APP_VER}".center(55))
        print("(Roblox username generator + availability checker)".center(55))
        print()
        print("Fetching CSRF token...", end=" ")
        tok = get_csrf_token()
        print(f"{'OK' if tok else 'FAILED'}\n")

        mode = input("Mode: [s]can [g]enerate [a]esthetic-only [m]anual [w]ordlist? ").strip().lower()

        if mode == 'm':
            manual_lookup_mode()

        elif mode == 'w':
            wordlist_mode(pick_length())

        elif mode == 'a':
            length = pick_length()
            target = int(input("How many aesthetic names to find? ") or "5")
            max_c = int(input("Max checks? ") or "500")
            found,total = [],0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                while len(found) < target and total < max_c:
                    bs = min(MAX_WORKERS, max_c-total)
                    names = [generate_aesthetic(length) for _ in range(bs)]
                    for f in as_completed({ex.submit(smart_check,n):n for n in names}):
                        n,s = f.result(); total += 1
                        if s=="available": found.append(n)
                        p_prog(n,s,len(found),total)
                    time.sleep(REQUEST_DELAY)
            print(f"\n\n{'='*55}")
            print(f"  AESTHETIC AVAILABLE ({length} chars): {len(found)}")
            print(f"{'='*55}")
            for n in found: print_available(n)
            if found:
                claim_available_name(found)
                ans2 = input(f"  Save to desktop? [Y/n]: ").strip().lower()
                if ans2 != 'n': save_results(found, f"aesthetic-{length}char")
            print("\n--- made by scarn ---\n")

        elif mode == 's':
            length = pick_length()
            target = int(input("How many names to find? ") or "5")
            print("Charset options:")
            print("  [L] Letters only (a-z)")
            print("  [M] Mixed letters+digits (default)")
            print("  [N] Numbers only (0-9)")
            cs_in = input("Choose: ").strip().lower()
            if cs_in == 'l': cs = LETTERS
            elif cs_in == 'n': cs = NUMBERS_ONLY
            else: cs = CHARSET
            max_c = int(input("Max checks? ") or "500")
            found,total = [],0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                while len(found) < target and total < max_c:
                    bs = min(MAX_WORKERS, max_c-total)
                    names = [generate_random(length,cs) for _ in range(bs)]
                    for f in as_completed({ex.submit(smart_check,n):n for n in names}):
                        n,s = f.result(); total += 1
                        if s=="available": found.append(n)
                        p_prog(n,s,len(found),total)
                    time.sleep(REQUEST_DELAY)
            print(f"\n\n{'='*55}")
            print(f"  SCAN DONE - Checked {total}, found {len(found)} available ({length} chars)")
            print(f"{'='*55}")
            for n in found: print_available(n)
            if not found: print("    (none found)")
            if found:
                claim_available_name(found)
                ans2 = input(f"  Save to desktop? [Y/n]: ").strip().lower()
                if ans2 != 'n': save_results(found, f"scan-{length}char")
            print("\n--- made by scarn ---\n")

        else:  # generate batch
            length = pick_length()
            batch = int(input("How many names? ") or "100")
            aeh = input("Aesthetic/word-like? [y/N]: ").strip().lower()=='y'
            print("Charset options:")
            print("  [L] Letters only (a-z)")
            print("  [M] Mixed letters+digits (default)")
            print("  [N] Numbers only (0-9)")
            cs_in = input("Choose: ").strip().lower()
            if cs_in == 'l': cs = LETTERS
            elif cs_in == 'n': cs = NUMBERS_ONLY
            else: cs = CHARSET
            names = [generate_aesthetic(length) if aeh else generate_random(length,cs) for _ in range(batch)]
            res = []
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                for i,f in enumerate(as_completed({ex.submit(smart_check,n):n for n in names})):
                    res.append(f.result()); n,s = res[-1]
                    p_prog(n,s,len([r for r in res if r[1]=="available"]),i+1)
                    if (i+1)%MAX_WORKERS==0: time.sleep(REQUEST_DELAY)
            av = [n for n,s in res if s=="available"]
            aest = [n for n in av if is_aesthetic(n)]
            rand = [n for n in av if not is_aesthetic(n)]
            print(f"\n\n{'='*55}")
            print(f"  RESULTS ({length} chars) - Available: {len(av)}/{batch}")
            print(f"{'='*55}")
            if aest:
                print(f"\n  AESTHETIC ({len(aest)}):")
                for n in aest: print_available(n, f"({is_wordlike(n)}/10)")
            if rand:
                print(f"\n  RANDOM ({len(rand)}):")
                for n in rand: print_available(n)
            print(f"\n  TAKEN: {len([r for r in res if r[1]=='taken'])}")
            other = [r for r in res if r[1] not in ("available","taken")]
            if other:
                print("  OTHER:")
                for s,c in Counter(s for _,s in other).most_common(5):
                    print(f"    {s}: {c}")
            if av:
                claim_available_name(av)
                ans2 = input(f"  Save to desktop? [Y/n]: ").strip().lower()
                if ans2 != 'n': save_results(av, f"batch-{length}char")
            print("\n--- made by scarn ---\n")

        input("Press Enter to exit...")
    except KeyboardInterrupt:
        print("\n\nExiting.")
        print("--- made by scarn ---")
        input("Press Enter to exit...")
