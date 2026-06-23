#!/usr/bin/env python3
"""Regenerate the clean Legions-only build from the playtest app.

Policy (memory: sync-both-apps): updates to the playtest app are mirrored into the
clean Legion builder, keeping playtest-only things (Aeldari/Asuryani army + OP/UP/OK
balance tags) out of the clean version. This script is that mirror.

It transforms the playtest index.html with a fixed list of exact string replacements
(each asserts its match count, so source drift fails loudly), re-copies the encrypted
legion bundles + crests + icons, regenerates the Dark Angels bootstrap bundle, and
bumps the clean sw.js cache so clients refresh.

Usage:  PW='<gate passphrase>' python3 build/make_clean.py [DEST] [--check]
  DEST     clean repo path (default: ../heresy-legion-builder)
  --check  transform in-memory and diff index.html against DEST; touch nothing
"""
import os, re, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOTSTRAP_ARMY = "dark-angels"   # the clean build's default + ENC_BUNDLE source

args = [a for a in sys.argv[1:] if not a.startswith("--")]
CHECK = "--check" in sys.argv
DEST = os.path.abspath(args[0]) if args else os.path.join(os.path.dirname(ROOT), "heresy-legion-builder")


def transform(src):
    """Apply the playtest -> clean replacements. Each rep asserts its count."""
    log = []
    def rep(a, b, n, label):
        nonlocal src
        c = src.count(a)
        assert c == n, "make_clean: expected %d of [%s], found %d — source drifted" % (n, label, c)
        src = src.replace(a, b); log.append(label)

    rep('<html lang="en" data-skin="asuryani">', '<html lang="en" data-skin="neutral">', 1, "html data-skin")

    rep('''/* ---- Asuryani: wraithbone + spirit-stone ---- */
html[data-skin="asuryani"]{
  --bg:#070b0e; --bg-glow:#0f2a2a; --panel:#0e151a; --panel2:#16212a;
  --line:#22323d; --edge:#33505c;
  --bone:#ece7d8; --muted:#93a4ab; --dim:#5d717a;
  --teal:#62d7b2; --teal-d:#0e6f58; --blue:#6fb1ef; --amber:#f0c069;
  --red:#e8786c; --green:#8fce63;
  --accent:var(--teal); --accent-d:var(--teal-d);
  --glow:rgba(98,215,178,.16); --glow-strong:rgba(98,215,178,.34);
}
''', '', 1, "asuryani CSS block")

    rep('<span class="crest" id="crest"><img src="Eldar_Rune.webp" alt=""></span> <b id="armyName">Asuryani</b>',
        '<span class="crest" id="crest"><img src="app/crests/dark-angels.png" alt=""></span> <b id="armyName">Dark Angels</b>',
        1, "header crest/name")
    rep('<span id="skinLabel">Asuryani</span>', '<span id="skinLabel">Dark Angels</span>', 1, "skinLabel")
    rep('const id=document.getElementById("armyPick").value||"asuryani";',
        'const id=document.getElementById("armyPick").value||"dark-angels";', 1, "beginWithArmy default")
    rep('if(ARMY_MAP[want] && (want==="asuryani"||ARMY_MAP[want].data)){',
        'if(ARMY_MAP[want] && (want==="dark-angels"||ARMY_MAP[want].data)){', 1, "loadRoster bootstrap id")
    rep('  aeldari :{label:"Aeldari",          glyph:"✦", bg:"#070b0e",panel:"#0e151a",panel2:"#16212a",line:"#22323d",edge:"#33505c",bone:"#ece7d8",muted:"#93a4ab",dim:"#5d717a",amber:"#f0c069",red:"#e8786c",green:"#8fce63"},\n',
        '', 1, "aeldari GROUPS")
    rep('const GROUP_ORDER=["aeldari","loyalist","traitor","generic"];',
        'const GROUP_ORDER=["loyalist","traitor","generic"];', 1, "GROUP_ORDER")
    rep('  A("aeldari","asuryani","Asuryani","#62d7b2","#0e6f58","Wraithbone & spirit-stone",{img:"Eldar_Rune.webp",bg:"#070b0e",bgGlow:"#0f2a2a"}),\n',
        '', 1, "asuryani ARMIES entry")
    rep('let curArmy="asuryani";', 'let curArmy="dark-angels";', 1, "curArmy default")
    rep('let LOADED_ARMY="asuryani";', 'let LOADED_ARMY="dark-angels";', 1, "LOADED_ARMY default")
    rep('if(id!=="asuryani" && !a.data) return false;', 'if(id!=="dark-angels" && !a.data) return false;', 1, "loadArmy theme guard")
    rep('else if(id==="asuryani"){ data=JSON.parse(sessionStorage.getItem("data")||"null"); }',
        'else if(id==="dark-angels"){ data=JSON.parse(sessionStorage.getItem("data")||"null"); }', 1, "loadArmy bootstrap read")
    rep('if((id==="asuryani"||a&&a.data) && id!==LOADED_ARMY){',
        'if((id==="dark-angels"||a&&a.data) && id!==LOADED_ARMY){', 1, "selectArmy guard")
    rep('let saved="asuryani"; try{saved=localStorage.getItem(SKIN_KEY)||"asuryani";}catch(e){}',
        'let saved="dark-angels"; try{saved=localStorage.getItem(SKIN_KEY)||"dark-angels";}catch(e){}', 1, "initSkin saved default")
    rep('saved=ARMY_MAP[saved]?saved:"asuryani";', 'saved=ARMY_MAP[saved]?saved:"dark-angels";', 1, "initSkin fallback")
    rep('if(saved!=="asuryani" && ARMY_MAP[saved].data){ loadArmy(saved).catch(()=>{}); }',
        'if(saved!=="dark-angels" && ARMY_MAP[saved].data){ loadArmy(saved).catch(()=>{}); }', 1, "initSkin load non-default")

    # remove the OP/UP/OK playtest balance tags; relabel the notes field
    rep('''  cfg+=`<div class="tagrow">
    ${["op","up","ok"].map(t=>`<span class="tag ${t} ${e.tag===t?'sel':''}" data-tag="${e.uid}:${t}">${({op:'OP',up:'Underpowered',ok:'Balanced'})[t]}</span>`).join("")}
    </div>
    <textarea class="note" placeholder="Playtest notes…" data-note="${e.uid}">${e.note||""}</textarea>`;''',
        '''  cfg+=`<textarea class="note" placeholder="Notes…" data-note="${e.uid}">${e.note||""}</textarea>`;''',
        1, "remove OP/UP/OK tags + relabel notes")

    rep('// Legions are a one-line add. The gate keeps the hardcoded data-skin="asuryani".',
        '// Legions are a one-line add. The gate keeps the hardcoded data-skin="neutral".', 1, "comment data-skin")
    rep('// Asuryani ships in the main bundle (window.ENC_BUNDLE). Other armies with a',
        '// Dark Angels ships in the main bundle (window.ENC_BUNDLE) as the bootstrap. Other armies with a',
        1, "comment bootstrap")
    return src, log


def encrypt_bootstrap(dest_enc):
    pw = os.environ.get("PW")
    if not pw:
        sys.exit("Set the gate passphrase: PW='…' python3 build/make_clean.py")
    node = r'''
const crypto=require("crypto"),fs=require("fs");
const pt=fs.readFileSync(process.env.SRC_BUNDLE,"utf8");
const salt=crypto.randomBytes(16),iv=crypto.randomBytes(12),ITER=200000;
const key=crypto.pbkdf2Sync(process.env.PW,salt,ITER,32,"sha256");
const c=crypto.createCipheriv("aes-256-gcm",key,iv);
const ct=Buffer.concat([c.update(pt,"utf8"),c.final()]);
const blob=Buffer.concat([salt,iv,ct,c.getAuthTag()]).toString("base64");
fs.writeFileSync(process.env.DEST_ENC,
  "// AUTO-GENERATED encrypted bootstrap bundle (Dark Angels). Safe to publish.\n"+
  "window.ENC_BUNDLE=\""+blob+"\";\nwindow.ENC_ITER="+ITER+";\n");
'''
    env = dict(os.environ, SRC_BUNDLE=os.path.join(ROOT, "data_%s" % BOOTSTRAP_ARMY, "bundle.json"), DEST_ENC=dest_enc)
    subprocess.run(["node", "-e", node], env=env, check=True)


def bump_sw_cache(sw_path):
    s = open(sw_path, encoding="utf-8").read()
    m = re.search(r'const CACHE = "legion-v(\d+)";', s)
    if not m:
        print("  (sw.js cache line not found — left unchanged)"); return
    n = int(m.group(1)) + 1
    open(sw_path, "w", encoding="utf-8").write(s.replace(m.group(0), 'const CACHE = "legion-v%d";' % n))
    print("  sw.js cache -> legion-v%d" % n)


def main():
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    out, log = transform(src)

    if CHECK:
        cur = open(os.path.join(DEST, "index.html"), encoding="utf-8").read()
        print("transform OK (%d replacements)." % len(log))
        print("index.html matches DEST." if out == cur else "index.html DIFFERS from DEST — run without --check to update.")
        return

    os.makedirs(os.path.join(DEST, "app"), exist_ok=True)
    open(os.path.join(DEST, "index.html"), "w", encoding="utf-8").write(out)
    print("index.html: %d replacements applied" % len(log))

    # copy encrypted legion bundles + art
    n = 0
    for f in os.listdir(os.path.join(ROOT, "app")):
        if re.match(r"data\.[a-z-]+\.enc\.js$", f):
            shutil.copy(os.path.join(ROOT, "app", f), os.path.join(DEST, "app", f)); n += 1
    for d in ("crests", "icons"):
        s, t = os.path.join(ROOT, "app", d), os.path.join(DEST, "app", d)
        if os.path.isdir(s):
            shutil.rmtree(t, ignore_errors=True); shutil.copytree(s, t)
    print("copied %d legion bundles + crests/icons" % n)

    encrypt_bootstrap(os.path.join(DEST, "app", "data.enc.js"))
    print("regenerated Dark Angels bootstrap (app/data.enc.js)")

    sw = os.path.join(DEST, "sw.js")
    if os.path.exists(sw):
        bump_sw_cache(sw)

    print("\nDone. Now commit/push BOTH repos (playtest + %s)." % os.path.basename(DEST))


if __name__ == "__main__":
    main()
