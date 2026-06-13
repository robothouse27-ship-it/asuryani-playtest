#!/usr/bin/env python3
"""Extract Asuryani HH3.0 playtest rules (docx/xlsx) -> JSON in ../data.
Stdlib only. Best-effort, table-aware."""
import zipfile, re, json, os, sys
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "2- Playtest Stage")
OUT  = os.path.join(ROOT, "data")

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def slug(s):
    s = re.sub(r"[’']", "", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s

# ---------- DOCX ----------
def _cell(tc):
    return '\n'.join(''.join(t.text or '' for t in p.iter(W+'t')) for p in tc.iter(W+'p')).strip()

def docx_blocks(path):
    """Return ordered list of ('p', text) and ('tbl', rows) blocks."""
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read('word/document.xml'))
    body = root.find(W+'body')
    blocks = []
    for el in body:
        tag = el.tag.replace(W, '')
        if tag == 'p':
            txt = ''.join(t.text or '' for t in el.iter(W+'t')).strip()
            if txt:
                blocks.append(('p', txt))
        elif tag == 'tbl':
            rows = [[_cell(tc) for tc in tr.findall(W+'tc')] for tr in el.findall(W+'tr')]
            blocks.append(('tbl', rows))
    return blocks

def docx_text(path):
    out = []
    for kind, c in docx_blocks(path):
        if kind == 'p':
            out.append(c)
        else:
            for row in c:
                out.append('\t'.join(row))
    return '\n'.join(out)

# ---------- XLSX ----------
def xlsx_sheets(path):
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        r = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in r.iter(S+'si'):
            shared.append(''.join(t.text or '' for t in si.iter(S+'t')))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    relmap = {r.get('Id'): r.get('Target') for r in rels}
    RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    result = {}
    for sh in wb.iter(S+'sheet'):
        name = sh.get('name'); rid = sh.get(RNS+'id')
        target = relmap[rid]
        if not target.startswith('xl/'):
            target = 'xl/' + target
        sheet = ET.fromstring(z.read(target))
        rows = []
        for row in sheet.iter(S+'row'):
            cells = {}
            for c in row.iter(S+'c'):
                ref = c.get('r'); t = c.get('t'); v = c.find(S+'v')
                col = re.match(r'([A-Z]+)', ref).group(1)
                val = ''
                if v is not None:
                    val = shared[int(v.text)] if t == 's' else v.text
                cells[col] = val
            rows.append(cells)
        result[name] = rows
    return result

def num(x):
    if x is None or x == '': return x
    try:
        f = float(x)
        return int(f) if f == int(f) else f
    except: return x

# ---------- WEAPONS ----------
def extract_weapons():
    path = os.path.join(SRC, "!5 - Asuryani Weapons.xlsx")
    sheets = xlsx_sheets(path)
    weapons = []
    for sheet_name, rows in sheets.items():
        if not rows: continue
        header = rows[0]
        cols = sorted(header.keys(), key=lambda c: (len(c), c))
        keys = [header[c].strip() for c in cols]
        for r in rows[1:]:
            name_col = cols[2] if len(cols) > 2 else None
            name = (r.get(name_col) or '').strip()
            if not name: continue
            obj = {}
            for c, k in zip(cols, keys):
                if not k: continue
                obj[k] = (r.get(c) or '').strip()
            for nk in ('R','FP','RS','AP','D','S','I'):
                if nk in obj: obj[nk] = num(obj[nk])
            obj['category'] = 'ranged' if sheet_name.lower().startswith('rang') else 'melee'
            obj['id'] = slug(name)
            weapons.append(obj)
    return weapons

# ---------- WARGEAR LISTS ----------
def extract_wargear_lists():
    path = os.path.join(SRC, "!3 - Asuryani Wargear Lists.docx")
    lines = [l for l in docx_text(path).split('\n') if l.strip()]
    lists = {}
    cur = None
    price_re = re.compile(r'^(.*?)\s*(Free|\+?\s*\d+\s*points?)\s*$', re.I)
    for ln in lines:
        ln = ln.replace('\t', ' ').strip()
        low = ln.lower()
        # header line ends with "List" (and no price) => new list
        if (low.endswith('list') or low.endswith('list:')) and not price_re.match(ln):
            name = ln.rstrip(':').strip()
            cur = slug(name)
            lists[cur] = {'name': name, 'items': []}
            continue
        m = price_re.match(ln)
        if m and cur:
            item = m.group(1).strip().rstrip('*').strip()
            ptxt = m.group(2).strip()
            pts = 0 if ptxt.lower() == 'free' else int(re.search(r'\d+', ptxt).group())
            if item:
                lists[cur]['items'].append({'name': item, 'points': pts})
    return lists

# ---------- UNITS ----------
STAT_KEYS = ['M','WS','BS','S','T','W','I','A','LD','CL','WP','IN','SAV','INV']

# Unit titles whose docx heading mis-extracts (e.g. a drop-cap first letter the
# parser drops). Keyed by the filename-derived id; overrides the parsed title.
NAME_OVERRIDES = {
    'ranger-lord': 'Ranger Lord',
}

def parse_unit(path, slot):
    blocks = docx_blocks(path)
    name = None
    for k, c in blocks:
        if k == 'p':
            name = c; break
        if k == 'tbl' and c and c[0]:
            name = c[0][0]; break
    uid = slug(os.path.splitext(os.path.basename(path))[0])
    unit = {
        'id': uid,
        'name': NAME_OVERRIDES.get(uid, name or os.path.splitext(os.path.basename(path))[0]),
        'slot': slot,
        'composition': None, 'baseCost': None, 'pointsValue': None,
        'sizeRules': [], 'lore': [], 'profiles': [],
        'wargear': {}, 'specialRules': {}, 'traits': [], 'types': {},
        'options': [], 'raw': docx_text(path)
    }
    def handle_grid(rows):
        # find header row(s): a row whose first non-empty cell is 'M' (infantry or vehicle stat line)
        for i, row in enumerate(rows):
            cleaned = [x.strip() for x in row]
            nonempty = [c for c in cleaned if c]
            is_header = (len(nonempty) >= 4 and nonempty[0].upper() == 'M'
                         and any(c.upper() in ('WS','BS','LD','HP','FRONT','SAV') for c in nonempty))
            if not is_header: continue
            hdr = cleaned  # keep alignment incl. leading blank (name col)
            for row2 in rows[i+1:]:
                cells = [x.strip() for x in row2]
                if not any(cells): continue
                pname = cells[0]
                # stop if we hit another header or a label row
                if pname.upper() == 'M' or pname.upper().endswith(':'): break
                if not pname: continue
                stats = {}
                for h, val in zip(hdr[1:], cells[1:]):
                    if h.strip(): stats[h.strip().upper()] = val.strip()
                if stats:
                    unit['profiles'].append({'name': pname, 'stats': stats})
        # composition / cost in same or other tables
        for row in rows:
            joined = ' '.join(row)
            for i, cell in enumerate(row):
                cl = cell.strip().lower()
                if cl.startswith('unit composition') and i+1 < len(row):
                    unit['composition'] = row[i+1].strip()
                if cl.startswith('base unit cost') and i+1 < len(row):
                    unit['baseCost'] = row[i+1].strip()
                    m = re.search(r'\d+', row[i+1])
                    if m: unit['pointsValue'] = int(m.group())
            if re.search(r'may include up to|points per model|for every', joined, re.I) \
               and 'composition' not in joined.lower() and len(row) <= 2:
                txt = joined.strip()
                if txt and txt not in unit['sizeRules']:
                    unit['sizeRules'].append(txt)
            # lore: long single-cell paragraphs
            if len(row) == 1 and len(row[0]) > 160:
                unit['lore'].append(row[0].strip())

    def split_per_model(text):
        """Parse 'Exarch:\nA\nB\n\nTrooper:\nC' into {model: [items]} or {'_': [...]}."""
        result = {}
        cur = '_'
        result[cur] = []
        for ln in text.split('\n'):
            t = ln.strip()
            if not t: continue
            if t.endswith(':'):
                cur = t[:-1].strip()
                result.setdefault(cur, [])
            else:
                result.setdefault(cur, []).append(t)
        if list(result.keys()) == ['_'] :
            return {'_': result['_']}
        result.pop('_', None) if not result.get('_') else None
        return result

    for k, c in blocks:
        if k != 'tbl': continue
        rows = c
        flat = ' '.join(' '.join(r) for r in rows).lower()
        if 'ws' in [x.strip().lower() for r in rows for x in r] or 'base unit cost' in flat or 'unit composition' in flat:
            handle_grid(rows)
        # Scan every row for WARGEAR / TRAITS / OPTIONS header rows (they may share a table)
        for ri, row in enumerate(rows):
            header = [x.strip().upper().rstrip(':') for x in row]
            body = rows[ri+1] if ri+1 < len(rows) else None
            if 'WARGEAR' in header and body:
                wi = header.index('WARGEAR')
                si = header.index('SPECIAL RULES') if 'SPECIAL RULES' in header else None
                if wi < len(body): unit['wargear'] = split_per_model(body[wi])
                if si is not None and si < len(body): unit['specialRules'] = split_per_model(body[si])
            if 'TRAITS' in header and body:
                ti = header.index('TRAITS')
                yi = header.index('TYPES') if 'TYPES' in header else None
                if ti < len(body):
                    unit['traits'] = [x.strip() for x in body[ti].split('\n') if x.strip()]
                if yi is not None and yi < len(body):
                    types = {}
                    for ln in body[yi].split('\n'):
                        if ':' in ln:
                            kk, vv = ln.split(':', 1); types[kk.strip()] = vv.strip()
                        elif ln.strip():
                            types.setdefault('_', []).append(ln.strip())
                    unit['types'] = types
            if header and header[0] == 'OPTIONS':
                for orow in rows[ri+1:]:
                    txt = ' '.join(x for x in orow if x).strip()
                    if txt and txt not in unit['options']: unit['options'].append(txt)
    # de-dup: size rules must not also appear as lore
    sr = set(unit['sizeRules'])
    unit['lore'] = [l for l in unit['lore'] if l not in sr]
    return unit

SLOT_DIRS = {
    '1 - High Command': 'High Command', '2 - Command': 'Command', '3 - Retinue': 'Retinue',
    '4 - Elites': 'Elites', '5 - Heavy Assault': 'Heavy Assault', '6 - Troops': 'Troops',
    '7 - Support': 'Support', '8 - War-Engines': 'War-Engines', '9 - Transports': 'Transports',
    '10 - Heavy Transports': 'Heavy Transports', '11 - Reconnaissance': 'Reconnaissance',
    '12 - Fast Attack': 'Fast Attack', '13 - Armour': 'Armour', '14 - Lords of War': 'Lords of War',
    '16 - Fortifications': 'Fortifications', '0 - Primarch': 'Primarch',
}

def extract_units():
    units = []
    for d in sorted(os.listdir(SRC)):
        full = os.path.join(SRC, d)
        if not os.path.isdir(full) or d not in SLOT_DIRS: continue
        slot = SLOT_DIRS[d]
        for f in sorted(os.listdir(full)):
            if not f.endswith('.docx'): continue
            try:
                units.append(parse_unit(os.path.join(full, f), slot))
            except Exception as e:
                print(f"  !! {f}: {e}", file=sys.stderr)
    return units

# ---------- SLOTS / TRAITS / SPECIAL ----------
def extract_slots():
    path = os.path.join(SRC, "!1 - Asuryani Unit Slot Breakdown.docx")
    lines = [l.strip() for l in docx_text(path).split('\n') if l.strip()]
    order = list(SLOT_DIRS.values())
    slots = {}
    cur = None
    known = set(s.lower() for s in order) | {'lords of war','recon','war-engines','fast attack',
        'heavy transports','heavy assault','high command'}
    for ln in lines[2:]:
        low = ln.lower().rstrip(':')
        if low in known or low in ('recon',):
            cur = 'Reconnaissance' if low == 'recon' else next((o for o in order if o.lower()==low), ln)
            slots.setdefault(cur, [])
        elif cur:
            slots[cur].append(ln)
    return slots

def main():
    os.makedirs(os.path.join(OUT, 'units'), exist_ok=True)
    weapons = extract_weapons()
    json.dump(weapons, open(os.path.join(OUT,'weapons.json'),'w'), indent=2, ensure_ascii=False)
    print(f"weapons: {len(weapons)}")

    wl = extract_wargear_lists()
    json.dump(wl, open(os.path.join(OUT,'wargearLists.json'),'w'), indent=2, ensure_ascii=False)
    print(f"wargear lists: {len(wl)}")

    slots = extract_slots()
    json.dump(slots, open(os.path.join(OUT,'slots.json'),'w'), indent=2, ensure_ascii=False)
    print(f"slot groups: {len(slots)}")

    for ref, fn in [("!2 - Asuryani Traits.docx",'traits.txt'),
                    ("!6 - Asuryani Special Rules.docx",'specialRules.txt'),
                    ("!4 - Asuryani Wargear.docx",'wargear.txt')]:
        open(os.path.join(OUT, fn),'w').write(docx_text(os.path.join(SRC, ref)))

    units = extract_units()
    index = []
    for u in units:
        json.dump(u, open(os.path.join(OUT,'units', u['id']+'.json'),'w'), indent=2, ensure_ascii=False)
        index.append({'id':u['id'],'name':u['name'],'slot':u['slot'],'points':u['pointsValue']})
    json.dump(index, open(os.path.join(OUT,'units','_index.json'),'w'), indent=2, ensure_ascii=False)
    print(f"units: {len(units)}")

if __name__ == '__main__':
    main()
