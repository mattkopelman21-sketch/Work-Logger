from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import os
import psycopg2
import psycopg2.extras
from datetime import date
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "wl-secret-key-x9q2m7p")

USERNAME = os.environ.get("APP_USERNAME", "matt")
PASSWORD = os.environ.get("APP_PASSWORD", "Matt103006")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_fJ3eNX7dzgHG@ep-shiny-block-aq9fc48c-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL, body TEXT, tag TEXT, date TEXT
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL, done INTEGER DEFAULT 0,
                due TEXT, priority TEXT DEFAULT 'med', tag TEXT
            );
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL, contact TEXT, phone TEXT, email TEXT, notes TEXT
            );
            CREATE TABLE IF NOT EXISTS customer_notes (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL, body TEXT NOT NULL, date TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );
            """)
        conn.commit()

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def api_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Work Notes & Tasks — Login</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f5f5f4; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 1rem; }
  .card { background: #fff; border: 0.5px solid rgba(0,0,0,.12); border-radius: 12px; padding: 2rem; width: 100%; max-width: 360px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }
  h1 { font-size: 18px; font-weight: 500; color: #1a1a1a; margin-bottom: 6px; }
  p { font-size: 13px; color: #9ca3af; margin-bottom: 24px; }
  label { display: block; font-size: 12px; color: #6b7280; margin-bottom: 4px; }
  input { width: 100%; font-size: 13px; padding: 8px 10px; border: 0.5px solid rgba(0,0,0,.25); border-radius: 8px; margin-bottom: 14px; background: #fff; color: #1a1a1a; outline: none; }
  input:focus { border-color: #1a1a1a; }
  button { width: 100%; padding: 9px; background: #1a1a1a; color: #fff; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; margin-top: 4px; }
  button:hover { opacity: .85; }
  .error { font-size: 13px; color: #A32D2D; background: #FCEBEB; padding: 8px 12px; border-radius: 8px; margin-bottom: 14px; }
</style>
</head>
<body>
<div class="card">
  <h1>Work Notes &amp; Tasks</h1>
  <p>Sign in to continue</p>
  {% if error %}<div class="error">{{ error }}</div>{% endif %}
  <form method="POST" action="/login">
    <label>Username</label>
    <input type="text" name="username" autocomplete="username" autofocus/>
    <label>Password</label>
    <input type="password" name="password" autocomplete="current-password"/>
    <button type="submit">Sign in</button>
  </form>
</div>
</body>
</html>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Incorrect username or password."
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/notes", methods=["GET"])
@api_login_required
def get_notes():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM notes ORDER BY id DESC")
            return jsonify(cur.fetchall())

@app.route("/api/notes", methods=["POST"])
@api_login_required
def add_note():
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO notes (title,body,tag,date) VALUES (%s,%s,%s,%s) RETURNING *",
                (d["title"], d.get("body",""), d.get("tag",""), str(date.today())))
            row = cur.fetchone()
        conn.commit()
    return jsonify(row), 201

@app.route("/api/notes/<int:nid>", methods=["PUT"])
@api_login_required
def update_note(nid):
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE notes SET title=%s,body=%s,tag=%s WHERE id=%s RETURNING *",
                (d["title"], d.get("body",""), d.get("tag",""), nid))
            row = cur.fetchone()
        conn.commit()
    return jsonify(row)

@app.route("/api/notes/<int:nid>", methods=["DELETE"])
@api_login_required
def delete_note(nid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM notes WHERE id=%s", (nid,))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/tasks", methods=["GET"])
@api_login_required
def get_tasks():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks ORDER BY id DESC")
            return jsonify(cur.fetchall())

@app.route("/api/tasks", methods=["POST"])
@api_login_required
def add_task():
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO tasks (title,done,due,priority,tag) VALUES (%s,0,%s,%s,%s) RETURNING *",
                (d["title"], d.get("due",""), d.get("priority","med"), d.get("tag","")))
            row = cur.fetchone()
        conn.commit()
    return jsonify(row), 201

@app.route("/api/tasks/<int:tid>", methods=["PUT"])
@api_login_required
def update_task(tid):
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE tasks SET title=%s,done=%s,due=%s,priority=%s,tag=%s WHERE id=%s RETURNING *",
                (d["title"], int(d.get("done",0)), d.get("due",""), d.get("priority","med"), d.get("tag",""), tid))
            row = cur.fetchone()
        conn.commit()
    return jsonify(row)

@app.route("/api/tasks/<int:tid>", methods=["DELETE"])
@api_login_required
def delete_task(tid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id=%s", (tid,))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/customers", methods=["GET"])
@api_login_required
def get_customers():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM customers ORDER BY name")
            customers = cur.fetchall()
            result = []
            for c in customers:
                cur.execute("SELECT * FROM customer_notes WHERE customer_id=%s ORDER BY id DESC", (c["id"],))
                d = dict(c)
                d["cnotes"] = cur.fetchall()
                result.append(d)
    return jsonify(result)

@app.route("/api/customers", methods=["POST"])
@api_login_required
def add_customer():
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO customers (name,contact,phone,email,notes) VALUES (%s,%s,%s,%s,%s) RETURNING *",
                (d["name"], d.get("contact",""), d.get("phone",""), d.get("email",""), d.get("notes","")))
            row = dict(cur.fetchone())
        conn.commit()
    row["cnotes"] = []
    return jsonify(row), 201

@app.route("/api/customers/<int:cid>", methods=["DELETE"])
@api_login_required
def delete_customer(cid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM customer_notes WHERE customer_id=%s", (cid,))
            cur.execute("DELETE FROM customers WHERE id=%s", (cid,))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/customers/<int:cid>/notes", methods=["POST"])
@api_login_required
def add_customer_note(cid):
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO customer_notes (customer_id,body,date) VALUES (%s,%s,%s) RETURNING *",
                (cid, d["body"], str(date.today())))
            row = cur.fetchone()
        conn.commit()
    return jsonify(row), 201

@app.route("/api/customers/<int:cid>/notes/<int:nid>", methods=["DELETE"])
@api_login_required
def delete_customer_note(cid, nid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM customer_notes WHERE id=%s AND customer_id=%s", (nid, cid))
        conn.commit()
    return jsonify({"ok": True})

FRONTEND = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Work Notes & Tasks</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css"/>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root { --bg:#fff;--bg2:#f5f5f4;--tx:#1a1a1a;--tx2:#6b7280;--tx3:#9ca3af;--bd:rgba(0,0,0,.12);--bd2:rgba(0,0,0,.25);--r:8px;--rl:12px;--ib:#E6F1FB;--it:#0C447C; }
  body { font-family:system-ui,sans-serif;background:var(--bg2);min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:2rem 1rem; }
  .app { display:grid;grid-template-columns:200px 1fr;min-height:560px;border:.5px solid var(--bd);border-radius:var(--rl);overflow:hidden;background:var(--bg);width:100%;max-width:900px;box-shadow:0 2px 12px rgba(0,0,0,.06); }
  .sidebar { background:var(--bg2);border-right:.5px solid var(--bd);padding:1rem;display:flex;flex-direction:column;gap:4px; }
  .stitle { font-size:11px;font-weight:500;color:var(--tx3);text-transform:uppercase;letter-spacing:.06em;margin:12px 0 4px; }
  .stitle:first-child { margin-top:0; }
  .nitem { display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:var(--r);cursor:pointer;font-size:14px;color:var(--tx2);border:none;background:none;width:100%;text-align:left;transition:background .1s; }
  .nitem:hover { background:var(--bg);color:var(--tx); }
  .nitem.active { background:var(--bg);color:var(--tx);font-weight:500; }
  .badge { margin-left:auto;background:var(--ib);color:var(--it);font-size:11px;font-weight:500;padding:1px 6px;border-radius:99px; }
  .main { display:flex;flex-direction:column;min-width:0; }
  .topbar { display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:.5px solid var(--bd); }
  .topbar h2 { font-size:15px;font-weight:500;flex:1;color:var(--tx); }
  .btn { display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:var(--r);border:.5px solid var(--bd2);background:var(--bg);color:var(--tx);font-size:13px;cursor:pointer;transition:background .1s; }
  .btn:hover { background:var(--bg2); }
  .btn-p { background:var(--tx);color:var(--bg);border-color:transparent; }
  .btn-p:hover { opacity:.85; }
  .content { flex:1;padding:16px;overflow-y:auto;min-width:0; }
  .entry { border:.5px solid var(--bd);border-radius:var(--rl);padding:12px 14px;margin-bottom:10px; }
  .etitle { font-size:14px;font-weight:500;color:var(--tx); }
  .emeta { font-size:12px;color:var(--tx3);margin-top:3px; }
  .ebody { font-size:13px;color:var(--tx2);margin-top:8px;line-height:1.6; }
  .tag { display:inline-flex;font-size:11px;padding:2px 8px;border-radius:99px;font-weight:500;margin-right:4px; }
  .tw{background:#E6F1FB;color:#0C447C}.tp{background:#EEEDFE;color:#3C3489}.tu{background:#FCEBEB;color:#791F1F}
  .trow { display:flex;align-items:center;gap:10px;padding:8px 14px;border-bottom:.5px solid var(--bd);cursor:pointer; }
  .trow:last-child { border-bottom:none; }
  .trow:hover { background:var(--bg2); }
  .tchk { width:16px;height:16px;border-radius:4px;border:1.5px solid var(--bd2);flex-shrink:0;display:flex;align-items:center;justify-content:center; }
  .tchk.done { background:var(--tx);border-color:var(--tx); }
  .ttxt { font-size:13px;color:var(--tx);flex:1; }
  .ttxt.done { text-decoration:line-through;color:var(--tx3); }
  .tdue { font-size:11px;color:var(--tx3); }
  .tdue.ov { color:#A32D2D; }
  .pdot { width:6px;height:6px;border-radius:50%;flex-shrink:0; }
  .ph{background:#E24B4A}.pm{background:#EF9F27}.pl{background:#639922}
  .modal-wrap { display:none;position:fixed;inset:0;background:rgba(0,0,0,.35);align-items:center;justify-content:center;z-index:100; }
  .modal-wrap.open { display:flex; }
  .modal { background:var(--bg);border:.5px solid var(--bd);border-radius:var(--rl);padding:20px;width:460px;max-width:95vw;max-height:90vh;overflow-y:auto; }
  .modal h3 { font-size:15px;font-weight:500;margin-bottom:14px;color:var(--tx); }
  .fr { margin-bottom:12px; }
  .fr label { display:block;font-size:12px;color:var(--tx2);margin-bottom:4px; }
  .fr input,.fr textarea,.fr select { width:100%;font-size:13px;padding:6px 10px;border:.5px solid var(--bd2);border-radius:var(--r);background:var(--bg);color:var(--tx); }
  .fr textarea { height:80px;resize:vertical; }
  .mfoot { display:flex;justify-content:flex-end;gap:8px;margin-top:16px; }
  .dbtn { background:none;border:none;cursor:pointer;color:var(--tx3);padding:2px 4px;border-radius:4px;font-size:15px; }
  .dbtn:hover { color:#E24B4A;background:#FCEBEB; }
  .empty { text-align:center;padding:40px;color:var(--tx3);font-size:13px; }
  .tabrow { display:flex;gap:4px;padding:8px 16px;border-bottom:.5px solid var(--bd); }
  .tab { padding:4px 10px;border-radius:var(--r);font-size:12px;cursor:pointer;border:none;background:none;color:var(--tx2); }
  .tab.active { background:var(--bg2);color:var(--tx);font-weight:500; }
  .cgrid { display:grid;grid-template-columns:1fr 1fr;gap:10px; }
  .ccard { border:.5px solid var(--bd);border-radius:var(--rl);padding:12px 14px;cursor:pointer;transition:border-color .15s; }
  .ccard:hover { border-color:var(--bd2); }
  .ccard.sel { border:1.5px solid var(--tx); }
  .cname { font-size:14px;font-weight:500;color:var(--tx); }
  .cmeta { font-size:12px;color:var(--tx3);margin-top:3px; }
  .cnc { font-size:11px;background:var(--ib);color:var(--it);padding:2px 7px;border-radius:99px;display:inline-block;margin-top:6px; }
  .dpanel { border:.5px solid var(--bd);border-radius:var(--rl);overflow:hidden;margin-top:14px; }
  .dhead { display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:.5px solid var(--bd);background:var(--bg2); }
  .dhead h3 { font-size:14px;font-weight:500;flex:1;color:var(--tx); }
  .cnote { padding:10px 14px;border-bottom:.5px solid var(--bd); }
  .cnote:last-child { border-bottom:none; }
  .cndate { font-size:11px;color:var(--tx3);margin-bottom:3px; }
  .cnbody { font-size:13px;color:var(--tx2);line-height:1.55; }
  .anf { padding:14px;border-top:.5px solid var(--bd);background:var(--bg2);display:flex;gap:8px;align-items:flex-end; }
  .anf textarea { flex:1;font-size:13px;padding:7px 10px;border:.5px solid var(--bd2);border-radius:var(--r);resize:none;height:60px;background:var(--bg);color:var(--tx); }
  .swrap { position:relative;margin-bottom:12px; }
  .swrap .ti { position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--tx3);font-size:15px;pointer-events:none; }
  .sbox { width:100%;font-size:13px;padding:6px 10px 6px 32px;border:.5px solid var(--bd2);border-radius:var(--r);background:var(--bg);color:var(--tx); }
</style>
</head>
<body>
<div style="max-width:900px;width:100%;margin-bottom:12px;display:flex;align-items:baseline;gap:10px">
  <h1 style="font-size:20px;font-weight:500;color:#1a1a1a">Work Notes &amp; Tasks</h1>
  <span style="font-size:13px;color:#9ca3af" id="today"></span>
  <a href="/logout" style="margin-left:auto;font-size:12px;color:#9ca3af;text-decoration:none;display:flex;align-items:center;gap:4px"><i class="ti ti-logout"></i> Sign out</a>
</div>
<div class="app">
  <div class="sidebar">
    <p class="stitle">Views</p>
    <button class="nitem active" onclick="sv('notes')" id="nav-notes"><i class="ti ti-notes"></i> Notes <span class="badge" id="nc">0</span></button>
    <button class="nitem" onclick="sv('tasks')" id="nav-tasks"><i class="ti ti-checkbox"></i> Tasks <span class="badge" id="tc">0</span></button>
    <button class="nitem" onclick="sv('customers')" id="nav-customers"><i class="ti ti-users"></i> Customers <span class="badge" id="cc">0</span></button>
    <p class="stitle">Filter</p>
    <button class="nitem" onclick="ft('work')" id="fw"><i class="ti ti-briefcase"></i> Work</button>
    <button class="nitem" onclick="ft('personal')" id="fp"><i class="ti ti-user"></i> Personal</button>
    <button class="nitem" onclick="ft('urgent')" id="fu"><i class="ti ti-alert-circle"></i> Urgent</button>
    <div style="flex:1"></div>
    <button class="nitem" onclick="cf()"><i class="ti ti-filter-off"></i> Clear filter</button>
  </div>
  <div class="main">
    <div class="topbar">
      <h2 id="vtitle">Notes</h2>
      <button class="btn btn-p" onclick="om()" id="addbtn"><i class="ti ti-plus"></i> Add note</button>
    </div>
    <div class="tabrow" id="ttabs" style="display:none">
      <button class="tab active" onclick="st('all')" id="tab-all">All</button>
      <button class="tab" onclick="st('todo')" id="tab-todo">To do</button>
      <button class="tab" onclick="st('done')" id="tab-done">Done</button>
    </div>
    <div class="content" id="content"></div>
  </div>
</div>
<div class="modal-wrap" id="modal">
  <div class="modal">
    <h3 id="mtitle">New note</h3>
    <div class="fr"><label>Title</label><input type="text" id="ft" placeholder="e.g. Meeting recap"/></div>
    <div class="fr" id="br"><label>Body</label><textarea id="fb" placeholder="Write your note here..."></textarea></div>
    <div class="fr" id="dr" style="display:none"><label>Due date</label><input type="date" id="fd"/></div>
    <div class="fr" id="pr" style="display:none"><label>Priority</label>
      <select id="fpri"><option value="low">Low</option><option value="med" selected>Medium</option><option value="high">High</option></select>
    </div>
    <div class="fr"><label>Tag</label>
      <select id="ftag"><option value="">None</option><option value="work">Work</option><option value="personal">Personal</option><option value="urgent">Urgent</option></select>
    </div>
    <div class="mfoot"><button class="btn" onclick="cm()">Cancel</button><button class="btn btn-p" onclick="si()">Save</button></div>
  </div>
</div>
<div class="modal-wrap" id="cmodal">
  <div class="modal">
    <h3>Add customer</h3>
    <div class="fr"><label>Company / Name *</label><input type="text" id="cn" placeholder="e.g. Acme Corp"/></div>
    <div class="fr"><label>Contact person</label><input type="text" id="cct" placeholder="e.g. Jane Smith"/></div>
    <div class="fr"><label>Phone</label><input type="text" id="cph" placeholder="e.g. 555-123-4567"/></div>
    <div class="fr"><label>Email</label><input type="email" id="cem" placeholder="e.g. jane@acme.com"/></div>
    <div class="fr"><label>Initial notes</label><textarea id="cno" placeholder="Any context..."></textarea></div>
    <div class="mfoot"><button class="btn" onclick="ccm()">Cancel</button><button class="btn btn-p" onclick="sc()">Save customer</button></div>
  </div>
</div>
<script>
let view='notes',ttab='all',af=null,eid=null,selCu=null,csrch='';
let notes=[],tasks=[],customers=[];
async function api(method,url,body){const opts={method,headers:{'Content-Type':'application/json'}};if(body)opts.body=JSON.stringify(body);const r=await fetch(url,opts);if(r.status===401){window.location='/login';return {};}return r.json();}
async function loadAll(){[notes,tasks,customers]=await Promise.all([api('GET','/api/notes'),api('GET','/api/tasks'),api('GET','/api/customers')]);render();}
function fd(d){if(!d)return'';const dt=new Date(d+'T00:00:00');return dt.toLocaleDateString('en-US',{month:'short',day:'numeric'});}
function ov(d){if(!d)return false;return new Date(d+'T00:00:00')<new Date(new Date().toDateString());}
function esc(s){return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function sv(v){view=v;af=null;document.querySelectorAll('.nitem').forEach(el=>el.classList.remove('active'));document.getElementById('nav-'+v).classList.add('active');document.getElementById('vtitle').textContent={notes:'Notes',tasks:'Tasks',customers:'Customers'}[v];document.getElementById('addbtn').innerHTML='<i class="ti ti-plus"></i> '+{notes:'Add note',tasks:'Add task',customers:'Add customer'}[v];document.getElementById('ttabs').style.display=v==='tasks'?'flex':'none';render();}
function ft(tag){if(view==='customers')return;af=af===tag?null:tag;document.querySelectorAll('#fw,#fp,#fu').forEach(el=>el.classList.remove('active'));if(af)document.getElementById('f'+af[0]).classList.add('active');render();}
function cf(){af=null;document.querySelectorAll('#fw,#fp,#fu').forEach(el=>el.classList.remove('active'));render();}
function st(t){ttab=t;document.querySelectorAll('.tab').forEach(el=>el.classList.remove('active'));document.getElementById('tab-'+t).classList.add('active');render();}
function render(){const c=document.getElementById('content');document.getElementById('nc').textContent=notes.length;document.getElementById('tc').textContent=tasks.filter(t=>!t.done).length;document.getElementById('cc').textContent=customers.length;if(view==='notes')rNotes(c);else if(view==='tasks')rTasks(c);else rCustomers(c);}
function rNotes(c){let items=af?notes.filter(n=>n.tag===af):notes;if(!items.length){c.innerHTML='<div class="empty"><i class="ti ti-notes" style="font-size:32px;display:block;margin-bottom:8px"></i>No notes yet. Add one!</div>';return;}c.innerHTML=items.map(n=>`<div class="entry"><div style="display:flex;align-items:flex-start;gap:8px"><div style="flex:1"><div class="etitle">${esc(n.title)}</div><div class="emeta">${fd(n.date)}${n.tag?' &nbsp;<span class="tag t'+n.tag[0]+'">'+n.tag+'</span>':''}</div></div><button class="dbtn" onclick="enote(${n.id})"><i class="ti ti-edit"></i></button><button class="dbtn" onclick="dn('note',${n.id})"><i class="ti ti-trash"></i></button></div><div class="ebody">${esc(n.body)}</div></div>`).join('');}
function rTasks(c){let items=af?tasks.filter(t=>t.tag===af):tasks;if(ttab==='todo')items=items.filter(t=>!t.done);if(ttab==='done')items=items.filter(t=>t.done);if(!items.length){c.innerHTML='<div class="empty"><i class="ti ti-checkbox" style="font-size:32px;display:block;margin-bottom:8px"></i>No tasks here.</div>';return;}c.innerHTML='<div style="border:.5px solid var(--bd);border-radius:var(--rl);overflow:hidden">'+items.map(t=>`<div class="trow" onclick="tog(${t.id})"><div class="tchk ${t.done?'done':''}">${t.done?'<i class="ti ti-check" style="font-size:11px;color:#fff"></i>':''}</div><div class="pdot p${(t.priority||'m')[0]}"></div><div class="ttxt ${t.done?'done':''}">${esc(t.title)}</div>${t.tag?`<span class="tag t${t.tag[0]}">${t.tag}</span>`:''}<span class="tdue ${!t.done&&ov(t.due)?'ov':''}">${fd(t.due)}</span><button class="dbtn" onclick="event.stopPropagation();etask(${t.id})"><i class="ti ti-edit"></i></button><button class="dbtn" onclick="event.stopPropagation();dn('task',${t.id})"><i class="ti ti-trash"></i></button></div>`).join('')+'</div>';}
function rCustomers(c){const filt=csrch?customers.filter(cu=>(cu.name||'').toLowerCase().includes(csrch.toLowerCase())||(cu.contact||'').toLowerCase().includes(csrch.toLowerCase())):customers;let h=`<div class="swrap"><i class="ti ti-search"></i><input class="sbox" type="text" placeholder="Search customers..." value="${esc(csrch)}" oninput="csrch=this.value;render()"/></div>`;if(!filt.length){h+='<div class="empty"><i class="ti ti-users" style="font-size:32px;display:block;margin-bottom:8px"></i>No customers yet.</div>';c.innerHTML=h;return;}h+='<div class="cgrid">';filt.forEach(cu=>{h+=`<div class="ccard ${selCu===cu.id?'sel':''}" onclick="selc(${cu.id})"><div class="cname">${esc(cu.name)}</div><div class="cmeta">${esc(cu.contact||'')}${cu.phone?' · '+esc(cu.phone):''}</div><span class="cnc">${(cu.cnotes||[]).length} note${(cu.cnotes||[]).length!==1?'s':''}</span></div>`;});h+='</div>';if(selCu){const cu=customers.find(x=>x.id===selCu);if(cu){h+=`<div class="dpanel"><div class="dhead"><div style="flex:1"><h3>${esc(cu.name)}</h3><div style="font-size:12px;color:var(--tx3)">${cu.contact?esc(cu.contact):''}${cu.email?' · '+esc(cu.email):''}</div></div><button class="dbtn" onclick="delcu(${cu.id})"><i class="ti ti-trash"></i></button></div>`;const cnotes=cu.cnotes||[];if(!cnotes.length){h+=`<div style="padding:14px;font-size:13px;color:var(--tx3)">No notes yet for this customer.</div>`;}else{cnotes.forEach(n=>{h+=`<div class="cnote"><div class="cndate">${fd(n.date)} <button class="dbtn" style="margin-left:6px" onclick="delcn(${cu.id},${n.id})"><i class="ti ti-trash"></i></button></div><div class="cnbody">${esc(n.body)}</div></div>`;});}h+=`<div class="anf"><textarea id="cni" placeholder="Add a note for ${esc(cu.name)}... (Ctrl+Enter)" onkeydown="if(event.key==='Enter'&&(event.ctrlKey||event.metaKey))acn(${cu.id})"></textarea><button class="btn btn-p" onclick="acn(${cu.id})"><i class="ti ti-send"></i> Add</button></div></div>`;}}c.innerHTML=h;}
function selc(id){selCu=selCu===id?null:id;render();if(selCu){setTimeout(()=>{const i=document.getElementById('cni');if(i){i.scrollIntoView({behavior:'smooth',block:'nearest'});i.focus();}},60);}}
async function acn(cid){const inp=document.getElementById('cni');const b=inp?inp.value.trim():'';if(!b)return;const note=await api('POST',`/api/customers/${cid}/notes`,{body:b});const cu=customers.find(x=>x.id===cid);if(cu){cu.cnotes=cu.cnotes||[];cu.cnotes.unshift(note);}render();}
async function delcn(cid,nid){await api('DELETE',`/api/customers/${cid}/notes/${nid}`);const cu=customers.find(x=>x.id===cid);if(cu)cu.cnotes=(cu.cnotes||[]).filter(n=>n.id!==nid);render();}
async function delcu(id){await api('DELETE',`/api/customers/${id}`);customers=customers.filter(x=>x.id!==id);if(selCu===id)selCu=null;render();}
async function tog(id){const t=tasks.find(x=>x.id===id);if(!t)return;t.done=t.done?0:1;render();await api('PUT',`/api/tasks/${id}`,t);}
function om(){if(view==='customers'){document.getElementById('cmodal').classList.add('open');setTimeout(()=>document.getElementById('cn').focus(),50);return;}eid=null;document.getElementById('mtitle').textContent=view==='notes'?'New note':'New task';['ft','fb','fd'].forEach(id=>document.getElementById(id).value='');document.getElementById('fpri').value='med';document.getElementById('ftag').value='';document.getElementById('br').style.display=view==='notes'?'':'none';document.getElementById('dr').style.display=view==='tasks'?'':'none';document.getElementById('pr').style.display=view==='tasks'?'':'none';document.getElementById('modal').classList.add('open');setTimeout(()=>document.getElementById('ft').focus(),50);}
function cm(){document.getElementById('modal').classList.remove('open');eid=null;}
function ccm(){document.getElementById('cmodal').classList.remove('open');}
async function sc(){const name=document.getElementById('cn').value.trim();if(!name){document.getElementById('cn').focus();return;}const cu=await api('POST','/api/customers',{name,contact:document.getElementById('cct').value.trim(),phone:document.getElementById('cph').value.trim(),email:document.getElementById('cem').value.trim(),notes:document.getElementById('cno').value.trim()});customers.push(cu);ccm();render();}
function enote(id){const n=notes.find(x=>x.id===id);if(!n)return;eid=id;document.getElementById('mtitle').textContent='Edit note';document.getElementById('ft').value=n.title;document.getElementById('fb').value=n.body;document.getElementById('ftag').value=n.tag||'';document.getElementById('br').style.display='';document.getElementById('dr').style.display='none';document.getElementById('pr').style.display='none';document.getElementById('modal').classList.add('open');}
function etask(id){const t=tasks.find(x=>x.id===id);if(!t)return;eid=id;document.getElementById('mtitle').textContent='Edit task';document.getElementById('ft').value=t.title;document.getElementById('fd').value=t.due||'';document.getElementById('fpri').value=t.priority||'med';document.getElementById('ftag').value=t.tag||'';document.getElementById('br').style.display='none';document.getElementById('dr').style.display='';document.getElementById('pr').style.display='';document.getElementById('modal').classList.add('open');}
async function si(){const title=document.getElementById('ft').value.trim();if(!title){document.getElementById('ft').focus();return;}const tag=document.getElementById('ftag').value;if(view==='notes'){const body=document.getElementById('fb').value.trim();if(eid){const n=await api('PUT',`/api/notes/${eid}`,{title,body,tag});const idx=notes.findIndex(x=>x.id===eid);if(idx>-1)notes[idx]=n;}else{const n=await api('POST','/api/notes',{title,body,tag});notes.unshift(n);}}else{const due=document.getElementById('fd').value;const priority=document.getElementById('fpri').value;if(eid){const t=await api('PUT',`/api/tasks/${eid}`,{title,due,priority,tag,done:tasks.find(x=>x.id===eid)?.done||0});const idx=tasks.findIndex(x=>x.id===eid);if(idx>-1)tasks[idx]=t;}else{const t=await api('POST','/api/tasks',{title,due,priority,tag});tasks.unshift(t);}}cm();render();}
async function dn(type,id){if(type==='note'){await api('DELETE',`/api/notes/${id}`);notes=notes.filter(x=>x.id!==id);}else{await api('DELETE',`/api/tasks/${id}`);tasks=tasks.filter(x=>x.id!==id);}render();}
document.getElementById('modal').addEventListener('click',function(ev){if(ev.target===this)cm();});
document.getElementById('cmodal').addEventListener('click',function(ev){if(ev.target===this)ccm();});
document.addEventListener('keydown',ev=>{if(ev.key==='Escape'){cm();ccm();}});
document.getElementById('today').textContent=new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
loadAll();
</script>
</body>
</html>"""

@app.route("/")
@login_required
def index():
    return render_template_string(FRONTEND)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
