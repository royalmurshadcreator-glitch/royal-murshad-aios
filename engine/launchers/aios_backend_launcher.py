"""Royal AIOS Backend Wrapper - all layers + 4 middleware."""
import sys, os, importlib.util
import pathlib as _pathlib

LEADS = r'D:\01_PROJECTS\AIOS\06_TOOLS\aios_leads'
SERVER = r'D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - SERVERS\Royal Murshad AIOS - master\Royal Murshad AIOS - aios_server.py'
SERVER_DIR = os.path.dirname(SERVER)
AIOS = r'D:\01_PROJECTS\AIOS'
MEM_PATH = r'D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - 04_MEMORY\Royal Murshad AIOS - aios_memory'
MODULES_DIR = r'D:\01_PROJECTS\Royal Murshad AIOS\18_ENV\launchers\modules'
for p in (LEADS, SERVER_DIR, r'D:\01_PROJECTS\Royal Murshad AIOS', AIOS, os.path.join(SERVER_DIR, 'royal_shim'), MEM_PATH, MODULES_DIR):
    if p and p not in sys.path:
        sys.path.insert(0, p)

# Bind the auth API to this project's explicitly named local auth module.
AUTH_SOURCE = r'D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_auth\Royal Murshad AIOS - aios_auth.py'
_auth_spec = importlib.util.spec_from_file_location('auth', AUTH_SOURCE)
if _auth_spec is None or _auth_spec.loader is None:
    raise RuntimeError('Royal Murshad local auth module could not be loaded')
_auth_module = importlib.util.module_from_spec(_auth_spec)
sys.modules['auth'] = _auth_module
_auth_spec.loader.exec_module(_auth_module)
def _storage_path(env, key, fallback):
    value = env.get(key)
    return _pathlib.Path(value) if value else _pathlib.Path(fallback)

_auth_module.MEM_DB = _storage_path(os.environ, 'AIOS_AUTH_DB_PATH', _auth_module.MEM_DB)

# Explicitly load original chat modules to prevent royal_shim shadowing
_MEM_DIR = _pathlib.Path(MEM_PATH)

def _load_real_module(mod_name, file_name):
    _path = _MEM_DIR / file_name
    if not _path.exists():
        print(f'[wrapper] FATAL: {_path} not found', file=sys.stderr)
        return None
    _spec = importlib.util.spec_from_file_location(mod_name, _path)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[mod_name] = _mod
    _spec.loader.exec_module(_mod)
    return _mod

try:
    _chat_db = _load_real_module('aios_chat_db', 'Royal Murshad AIOS - aios_chat_db.py')
    if _chat_db:
        _chat_db.ROOT = _MEM_DIR
        _chat_db.DATA_DIR = _MEM_DIR / 'Royal Murshad AIOS - data'
        _chat_db.CHAT_DB = _storage_path(
            os.environ,
            'AIOS_CHAT_DB_PATH',
            _chat_db.DATA_DIR / 'Royal Murshad AIOS - chat.db',
        )
        _chat_db.DATA_DIR = _chat_db.CHAT_DB.parent
        print(f'[wrapper] Patched aios_chat_db to use {_chat_db.CHAT_DB}')
    
    _chat_engine = _load_real_module('aios_chat_engine', 'Royal Murshad AIOS - aios_chat_engine.py')
except Exception as e:
    print(f'[wrapper] WARNING: Could not pre-load chat modules: {e}', file=sys.stderr)

spec = importlib.util.spec_from_file_location('aios_server_module', SERVER)
mod = importlib.util.module_from_spec(spec)
sys.modules['aios_server_module'] = mod
spec.loader.exec_module(mod)

app = getattr(mod, 'app', None)
if app is None:
    print('[wrapper] FATAL: no app', file=sys.stderr); sys.exit(1)

# Ã¢â€â‚¬Ã¢â€â‚¬ Middleware (mounted BEFORE routes) Ã¢â€â‚¬Ã¢â€â‚¬
MIDDLEWARE = [
    ('aios_cors', 'cors_middleware', 'cors'),
    ('aios_sec_headers', 'security_headers_middleware', 'security_headers'),
    ('aios_correlation', 'correlation_middleware',     'correlation'),
    ('aios_rate_limit',  'rate_limit_middleware',      'rate_limit'),
        ('aios_rbac_middleware', 'rbac_middleware',        'rbac'),
    ('aios_session_identity', 'session_identity_middleware', 'session_identity'),
    ('aios_public_auth',    'basic_auth_middleware',    'basic_auth'),
]
for modname, fname, label in MIDDLEWARE:
    try:
        m = __import__(modname)
        fn = getattr(m, fname)
        app.middleware('http')(fn)
        print(f'[wrapper] OK middleware {label}')
    except Exception as e:
        print(f'[wrapper] FAIL middleware {label}: {e}', file=sys.stderr)

# Ã¢â€â‚¬Ã¢â€â‚¬ Routers Ã¢â€â‚¬Ã¢â€â‚¬
def _mount(label, fn):
    try:
        r = fn()
        if r is None: return
        app.include_router(r)
        print(f'[wrapper] OK {label}')
    except Exception as e:
        print(f'[wrapper] FAIL {label}: {e}', file=sys.stderr)

_mount('static files',    lambda: __import__('aios_static_files_api').router)
_mount('apps registry',   lambda: __import__('aios_apps_registry_api').router)
_mount('master registry', lambda: __import__('aios_master_registry_api').router)

try:
    import aios_business_master_api as biz
    app.include_router(biz.router)
    for r in biz.get_routers(): app.include_router(r)
    print(f'[wrapper] OK business layer: {len(biz.get_routers())} children')
except Exception as e:
    print(f'[wrapper] FAIL business: {e}', file=sys.stderr)

try:
    import aios_royal_master_api as royal
    for r in royal.get_routers(): app.include_router(r)
    app.include_router(royal.router)
    print(f'[wrapper] OK royal cores: {len(royal.get_routers())}')
except Exception as e:
    print(f'[wrapper] FAIL royal cores: {e}', file=sys.stderr)

from fastapi.staticfiles import StaticFiles
sd = os.path.join(SERVER_DIR, 'static')
if os.path.isdir(sd):
    try: app.mount('/static-files', StaticFiles(directory=sd), name='sf')
    except Exception: pass








# === Agent API mount (assembly patch) ===
try:
    import importlib.util as _ilu
    _p = r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_agent_api.py"
    _s = _ilu.spec_from_file_location("aios_agent_api", _p)
    _m = _ilu.module_from_spec(_s)
    sys.modules["aios_agent_api"] = _m
    _s.loader.exec_module(_m)
    app.include_router(_m.router)
    app.include_router(_m.alias_router)
    print("[wrapper] OK agent api mounted")
except Exception as _e:
    print(f"[wrapper] FAIL agent api: {_e}", file=sys.stderr)

# === Agent Daemon Spawn (explicit opt-in only) ===
def _agent_daemon_opted_in():
    return os.environ.get('AIOS_ENABLE_AGENT_DAEMON', '').strip() == '1'

if _agent_daemon_opted_in():
    try:
        import subprocess as _sp
        _daemon = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent_daemon.py')
        if os.path.exists(_daemon):
            _sp.Popen([sys.executable, _daemon],
                      creationflags=0x08000000,
                      stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            print('[wrapper] OK agent daemon spawned by explicit opt-in')
        else:
            print('[wrapper] WARN agent_daemon.py not found', file=sys.stderr)
    except Exception as _e:
        print(f'[wrapper] FAIL daemon spawn: {_e}', file=sys.stderr)
else:
    print('[wrapper] Agent daemon disabled; set AIOS_ENABLE_AGENT_DAEMON=1 to opt in')
# === Dashboard API mount (assembly patch) ===
try:
    import importlib.util as _ilu_dash
    _dp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aios_dashboard_api.py')
    _ds = _ilu_dash.spec_from_file_location('aios_dashboard_api', _dp)
    _dm = _ilu_dash.module_from_spec(_ds)
    sys.modules['aios_dashboard_api'] = _dm
    _ds.loader.exec_module(_dm)
    app.include_router(_dm.router)
    print('[wrapper] OK dashboard api mounted')
except Exception as _e:
    print(f'[wrapper] FAIL dashboard: {_e}', file=sys.stderr)

# === Divisions API mount (assembly patch) ===
try:
    import importlib.util as _ilu_div
    _dp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aios_divisions_api.py')
    _ds = _ilu_div.spec_from_file_location('aios_divisions_api', _dp)
    _dm = _ilu_div.module_from_spec(_ds)
    sys.modules['aios_divisions_api'] = _dm
    _ds.loader.exec_module(_dm)
    app.include_router(_dm.router)
    print('[wrapper] OK divisions api mounted')
except Exception as _e:
    print(f'[wrapper] FAIL divisions: {_e}', file=sys.stderr)


# === Universal Agent Executor mount ===
try:
    import importlib.util as _ilu_ua
    _uap = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aios_universal_agent_api.py')
    _uas = _ilu_ua.spec_from_file_location('aios_universal_agent_api', _uap)
    _uam = _ilu_ua.module_from_spec(_uas)
    sys.modules['aios_universal_agent_api'] = _uam
    _uas.loader.exec_module(_uam)
    app.include_router(_uam.router)
    print('[wrapper] OK universal agent executor mounted')
except Exception as _e:
    print(f'[wrapper] FAIL universal agent executor: {_e}', file=sys.stderr)


# === Extended Data API mount ===
try:
    import importlib.util as _ilu_ext
    _ep = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aios_extended_data_api.py')
    _es = _ilu_ext.spec_from_file_location('aios_extended_data_api', _ep)
    _em = _ilu_ext.module_from_spec(_es)
    sys.modules['aios_extended_data_api'] = _em
    _es.loader.exec_module(_em)
    app.include_router(_em.router)
    print('[wrapper] OK extended data api mounted')
except Exception as _e:
    print(f'[wrapper] FAIL extended data: {_e}', file=sys.stderr)


# === PRE-REGISTER ORIGINAL MODULES (fixes "No module named X" errors) ===
try:
    import importlib.util as _ilu_pre
    _pre_modules = {
        "aios_backup":             r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_backup\Royal Murshad AIOS - aios_backup.py",
        "aios_calendar":           r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_calendar\Royal Murshad AIOS - aios_calendar.py",
        "aios_contacts":           r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_contacts\Royal Murshad AIOS - aios_contacts.py",
        "aios_errorlog":           r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - SERVERS\Royal Murshad AIOS - master\Royal Murshad AIOS - aios_errorlog.py",
        "aios_esim_bridge":        r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - SERVERS\Royal Murshad AIOS - master\Royal Murshad AIOS - aios_esim_bridge.py",
        "aios_executor":           r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - WORKSPACE\Royal Murshad AIOS - aios_executor\Royal Murshad AIOS - aios_executor.py",
        "aios_forum":              r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_forum\Royal Murshad AIOS - aios_forum.py",
        "aios_guardrails_runtime": r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_guardrails\Royal Murshad AIOS - aios_guardrails_runtime.py",
        "aios_knowledge":          r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_knowledge\Royal Murshad AIOS - aios_knowledge.py",
        "aios_maps":               r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_maps\Royal Murshad AIOS - aios_maps.py",
        "aios_meet":               r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_meet\Royal Murshad AIOS - aios_meet.py",
        "aios_news":               r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_news\Royal Murshad AIOS - aios_news.py",
        "aios_photos":             r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_photos\Royal Murshad AIOS - aios_photos.py",
        "aios_sheets":             r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_sheets\Royal Murshad AIOS - aios_sheets.py",
        "aios_slides":             r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_slides\Royal Murshad AIOS - aios_slides.py",
        "aios_social":             r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_social\Royal Murshad AIOS - aios_social.py",
        "aios_stomach":            r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - SERVERS\Royal Murshad AIOS - master\Royal Murshad AIOS - aios_stomach.py",
        "aios_power_control":      r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - CORE\Royal Murshad AIOS - aios_power_control.py",
        "aios_free_stack":         r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - CORE\Royal Murshad AIOS - aios_free_stack.py",
        "aios_vault_crypto": r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - 04_MEMORY\Royal Murshad AIOS - aios_memory\Royal Murshad AIOS - aios_vault_crypto.py",
        "aios_guard": r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - WORKSPACE\Royal Murshad AIOS - aios_executor\Royal Murshad AIOS - aios_guard.py",
    }
    _pre_ok = 0
    _pre_fail = 0
    for _name, _path in _pre_modules.items():
        if not os.path.exists(_path):
            _pre_fail += 1
            continue
        try:
            _spec = _ilu_pre.spec_from_file_location(_name, _path)
            _mod = _ilu_pre.module_from_spec(_spec)
            sys.modules[_name] = _mod
            _spec.loader.exec_module(_mod)
            _pre_ok += 1
        except Exception as _e:
            _pre_fail += 1
            print(f'[pre-register] FAIL {_name}: {_e}', file=sys.stderr)
    print(f'[pre-register] SUMMARY: {_pre_ok} registered, {_pre_fail} failed')
except Exception as _e:
    print(f'[pre-register] FATAL: {_e}', file=sys.stderr)
# === AUTO-MOUNTED DISCOVERED APIs (assembly patch) ===
try:
    import importlib.util as _ilu_auto
    _unmounted_apis = [
        ("aios_backup_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_backup_api.py"),
        ("aios_calendar_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_calendar_api.py"),
        ("aios_causal_diary_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_causal_diary_api.py"),
        ("aios_command_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_command_api.py"),
        ("aios_confidence_integrity_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_confidence_integrity_api.py"),
        ("aios_contacts_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_contacts_api.py"),
        ("aios_copywriter_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_copywriter_api.py"),
        ("aios_dropship_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_dropship_api.py"),
        ("aios_errorlog_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_errorlog_api.py"),
        ("aios_esim_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_esim_api.py"),
        ("aios_executor_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_executor_api.py"),
        ("aios_executor_config_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_executor_config_api.py"),
        ("aios_forum_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_forum_api.py"),
        ("aios_guardrails_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_guardrails_api.py"),
        ("aios_inventions_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_inventions_api.py"),
        ("aios_knowledge_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_knowledge_api.py"),
        ("aios_maps_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_maps_api.py"),
        ("aios_meet_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_meet_api.py"),
        ("aios_news_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_news_api.py"),
        ("aios_passport_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_passport_api.py"),
        ("aios_photos_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_photos_api.py"),
        ("aios_power_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_power_api.py"),
        ("aios_refusal_negotiation_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_refusal_negotiation_api.py"),
        ("aios_regret_ledger_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_regret_ledger_api.py"),
        ("aios_screen_live_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_screen_live_api.py"),
        ("aios_sheets_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_sheets_api.py"),
        ("aios_silence_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_silence_api.py"),
        ("aios_slides_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_slides_api.py"),
        ("aios_social_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_social_api.py"),
        ("aios_stomach_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_stomach_api.py"),
        ("aios_store_auth_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_store_auth_api.py"),
        ("aios_store_categories_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_store_categories_api.py"),
        ("aios_store_earnings_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_store_earnings_api.py"),
        ("aios_store_ratings_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_store_ratings_api.py"),
        ("aios_store_reports_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_store_reports_api.py"),
        ("aios_store_stripe_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_store_stripe_api.py"),
        ("aios_store_verify_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_store_verify_api.py"),
        ("aios_thought_engine_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_thought_engine_api.py"),
        ("aios_vision_eye_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_vision_eye_api.py"),
        ("aios_voice_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_endpoints\Royal Murshad AIOS - aios_voice_api.py"),
        ("saas_agents_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - AGENTS\Royal Murshad AIOS - aios_saas_agents\Royal Murshad AIOS - saas_agents_api.py"),
        ("aios_user_auth_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_auth\Royal Murshad AIOS - aios_user_auth_api.py"),
        ("storage_box_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - API\Royal Murshad AIOS - aios_admin_control\Royal Murshad AIOS - storage_box_api.py"),
        ("royal_ecosystem_registry_api", r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - SERVERS\Royal Murshad AIOS - master\Royal Murshad AIOS - royal_ecosystem_registry_api.py"),
    ]
    _mounted_count = 0
    _skipped_count = 0
    _failed_list = []
    for _name, _path in _unmounted_apis:
        try:
            _spec = _ilu_auto.spec_from_file_location(_name, _path)
            _mod = _ilu_auto.module_from_spec(_spec)
            sys.modules[_name] = _mod
            _spec.loader.exec_module(_mod)
            if hasattr(_mod, 'router'):
                app.include_router(_mod.router)
                _mounted_count += 1
                print(f'[auto-mount] OK {_name}')
            else:
                _skipped_count += 1
                print(f'[auto-mount] SKIP {_name} (no router)')
        except Exception as _e:
            _failed_list.append(_name)
            print(f'[auto-mount] FAIL {_name}: {_e}', file=sys.stderr)
    print(f'[auto-mount] SUMMARY: {_mounted_count} mounted, {_skipped_count} skipped, {len(_failed_list)} failed')
except Exception as _e:
    print(f'[auto-mount] FATAL: {_e}', file=sys.stderr)

# === Master Registry Endpoint mount ===
try:
    import importlib.util as _ilu_mr
    _mrp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aios_master_registry_endpoint.py')
    if os.path.exists(_mrp):
        _mrs = _ilu_mr.spec_from_file_location('aios_master_registry_endpoint', _mrp)
        _mrm = _ilu_mr.module_from_spec(_mrs)
        sys.modules['aios_master_registry_endpoint'] = _mrm
        _mrs.loader.exec_module(_mrm)
        app.include_router(_mrm.router)
        print('[wrapper] OK master registry endpoint')
    else:
        print('[wrapper] WARN master registry endpoint file missing', file=sys.stderr)
except Exception as _e:
    print(f'[wrapper] FAIL master registry endpoint: {_e}', file=sys.stderr)
# === Logs API mount ===
try:
    import importlib.util as _ilu_lg
    _lgp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aios_logs_api.py')
    if os.path.exists(_lgp):
        _lgs = _ilu_lg.spec_from_file_location('aios_logs_api', _lgp)
        _lgm = _ilu_lg.module_from_spec(_lgs)
        sys.modules['aios_logs_api'] = _lgm
        _lgs.loader.exec_module(_lgm)
        app.include_router(_lgm.router)
        print('[wrapper] OK logs api')
except Exception as _e:
    print(f'[wrapper] FAIL logs api: {_e}', file=sys.stderr)
# --- OMNI ENDPOINT INJECTION (CLEAN REALITY) ---
@app.get("/api/omni/summary")
def omni_summary():
    import json
    import os
    import glob
    
    result = {"apps": {}, "master": {}, "unplugged": {}, "inventory": {}}
    
    # 1. Fetch API Data
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:9000/api/apps/summary", timeout=3) as response:
            result["apps"] = json.loads(response.read().decode())
    except: pass
    
    try:
        with urllib.request.urlopen("http://127.0.0.1:9000/api/master/summary", timeout=3) as response:
            result["master"] = json.loads(response.read().decode())
    except: pass

    # 2. Fetch unplugged data
    unplugged_dir = "D:/01_PROJECTS/Royal Murshad AIOS/18_ENV/launchers/unplugged_data"
    if os.path.exists(unplugged_dir):
        for filename in os.listdir(unplugged_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(unplugged_dir, filename), "r", encoding="utf-8") as f:
                        result["unplugged"][filename] = json.load(f)
                except: pass

    # 3. CLEAN REALITY SCAN (Filtering out backups and junk)
    search_paths = ["D:/01_PROJECTS/Royal Murshad AIOS", "D:/ROYAL_MURSHAD_AIOS"]
    bad_keywords = ["quarantine", "backup", "deprecated", "node_modules", "site-packages", "_fix_", "_cleanup_", "migrated"]
    
    inventory = {
        "active_agents": [],
        "active_databases": [],
        "active_apps": [],
        "active_json_data": []
    }

    for base_path in search_paths:
        if not os.path.exists(base_path): continue
        
        for root, dirs, files in os.walk(base_path):
            # Skip bad directories
            if any(bad in root.lower() for bad in bad_keywords):
                dirs[:] = [] # Don't go deeper
                continue
                
            for file in files:
                filepath = os.path.join(root, file).replace("\\", "/")
                
                # Hunt Agents (Python/CJS)
                if ("agent" in file.lower() or "jarvis" in file.lower()) and file.endswith(('.py', '.cjs', '.js')):
                    inventory["active_agents"].append(filepath)
                
                # Hunt Databases (SQLite/DB)
                elif file.endswith(('.db', '.sqlite', '.sqlite3')):
                    inventory["active_databases"].append(filepath)
                    
                # Hunt Inventions (package.json)
                elif file == "package.json":
                    inventory["active_apps"].append(root.replace("\\", "/"))
                    
                # Hunt JSON Data (excluding manifests)
                elif file.endswith('.json') and "manifest" not in file.lower() and "package" not in file.lower():
                    inventory["active_json_data"].append(filepath)

    result["inventory"] = {
        "counts": {
            "agents": len(inventory["active_agents"]),
            "databases": len(inventory["active_databases"]),
            "inventions": len(inventory["active_apps"]),
            "json_data_files": len(inventory["active_json_data"])
        },
        "locations": {
            "top_agent_folders": list(set([os.path.dirname(p) for p in inventory["active_agents"][:50]])),
            "top_db_folders": list(set([os.path.dirname(p) for p in inventory["active_databases"][:50]])),
            "apps": inventory["active_apps"]
        }
    }
                
    return result
# --- END OMNI ENDPOINT INJECTION ---


# --- SAVE ENDPOINT INJECTION ---
APP_SAVE_DATA_DIR = _pathlib.Path(__file__).resolve().parent / "app_data"

@app.post("/api/apps/{slug}/save")
async def save_app_record(slug: str, data: dict):
    import json
    import os
    from datetime import datetime
    from fastapi import HTTPException
    from aios_path_security import resolve_app_save_path

    # Define the single D Drive folder where all app data will live
    data_dir = APP_SAVE_DATA_DIR
    try:
        file_path = resolve_app_save_path(data_dir, slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    os.makedirs(data_dir, exist_ok=True)

    # Read existing data or create a new list
    records = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                if not isinstance(records, list):
                    records = [records]
        except:
            records = []

    # Add timestamp and the new data
    data["timestamp"] = datetime.now().isoformat()
    records.append(data)

    # Save back to D Drive
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    return {"ok": True, "message": "Saved successfully", "total_records": len(records)}
# --- END SAVE ENDPOINT INJECTION ---


# --- SERVE 60 APPS STATIC FILES ---
from fastapi.staticfiles import StaticFiles
import os
from fastapi.responses import HTMLResponse

apps_dir = r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - 60 APPS DEPLOYMENT 20261015"
if os.path.exists(apps_dir):
    from aios_dashboard_security import (
        ApprovedStaticFiles,
        build_app_deploy_allowlist,
        resolve_app_deployment_html,
    )

    _app_deploy_allowed = build_app_deploy_allowlist(apps_dir)
    app.mount(
        "/apps-deploy",
        ApprovedStaticFiles(directory=apps_dir, allowed_paths=_app_deploy_allowed, html=True),
        name="apps-deploy",
    )

    # Add a specific route to handle loading an app
    @app.get("/api/load-app/{slug}")
    async def load_app(slug: str):
        try:
            app_path = resolve_app_deployment_html(apps_dir, slug)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Invalid application slug") from exc
        except (FileNotFoundError, NotADirectoryError):
            return HTMLResponse(content="Application page not found", status_code=404)

        from urllib.parse import quote
        relative_dir = app_path.parent.relative_to(_pathlib.Path(apps_dir).resolve()).as_posix()
        base_tag = f'<base href="http://127.0.0.1:9000/apps-deploy/{quote(relative_dir, safe="/")}/">'
        html_content = app_path.read_text(encoding="utf-8")
        html_content = html_content.replace("<head>", f"<head>{base_tag}", 1)
        return HTMLResponse(content=html_content)
# --- END SERVE 60 APPS ---


# --- UNIVERSAL DASHBOARD LOADER ---
from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from fastapi.responses import FileResponse
from aios_dashboard_security import (
    ApprovedStaticFiles,
    DASHBOARD_ASSET_ALLOWED_FILES,
    DASHBOARD_PUBLIC_ALLOWED_FILES,
    PUBLIC_UI_ALLOWED_FILES,
    resolve_dashboard_html,
)

_PROJECT_ROOT = _pathlib.Path(__file__).resolve().parents[2]
PUBLIC_UI_ROOT = _PROJECT_ROOT / "LAUNCH_PUBLIC" / "public" / "royal_murshad_public_ui"
DASHBOARD_ROOT = _PROJECT_ROOT / "UI-PAGES" / "public"

if PUBLIC_UI_ROOT.is_dir():
    app.mount(
        "/static-workspace",
        ApprovedStaticFiles(directory=PUBLIC_UI_ROOT, allowed_paths=PUBLIC_UI_ALLOWED_FILES),
        name="static-workspace",
    )
else:
    print(f"[wrapper] WARN public UI assets directory missing: {PUBLIC_UI_ROOT}", file=sys.stderr)

if DASHBOARD_ROOT.is_dir():
    app.mount(
        "/dashboard-public",
        ApprovedStaticFiles(directory=DASHBOARD_ROOT, allowed_paths=DASHBOARD_PUBLIC_ALLOWED_FILES),
        name="dashboard-public",
    )
    app.mount(
        "/assets",
        ApprovedStaticFiles(directory=DASHBOARD_ROOT.parent / "assets", allowed_paths=DASHBOARD_ASSET_ALLOWED_FILES),
        name="dashboard-assets",
    )
    _manifest_path = DASHBOARD_ROOT.parent / "manifest.json"
    if _manifest_path.is_file():
        @app.get("/manifest.json", include_in_schema=False)
        def public_ui_manifest():
            return FileResponse(_manifest_path, media_type="application/manifest+json")

@app.get("/api/view-dashboard")
async def view_dashboard(path: str = ""):
    try:
        target = resolve_dashboard_html(DASHBOARD_ROOT, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid dashboard path") from exc
    except (FileNotFoundError, NotADirectoryError):
        raise HTTPException(status_code=404, detail="Dashboard page not found")

    html = target.read_text(encoding="utf-8")
    if "<head>" in html:
        html = html.replace("<head>", '<head><base href="/dashboard-public/">', 1)
    return HTMLResponse(content=html)

@app.get("/api/all-dashboards")
def get_all_dashboards():
    pages = []
    if DASHBOARD_ROOT.is_dir():
        for page in DASHBOARD_ROOT.iterdir():
            if page.is_file() and page.suffix.lower() == ".html" and page.name in DASHBOARD_PUBLIC_ALLOWED_FILES:
                pages.append({"name": page.stem.replace("-", " ").replace("_", " ").title(), "path": page.name})
    pages.sort(key=lambda item: item["name"])
    return {"ok": True, "total": len(pages), "dashboards": pages}
# --- END APPROVED DASHBOARD LOADER ---


# Health separates process liveness from required dependency readiness.
from aios_health_status import collect_health_report
from fastapi.responses import JSONResponse

def _current_health_report():
    chat_db = globals().get("_chat_db")
    chat_engine = globals().get("_chat_engine")
    workforce = getattr(mod, "AGENTS", {}) or {}
    # ASG Core is a separately managed optional proxy target; main chat readiness
    # depends on the local database and Ollama, not the ASG process.
    return collect_health_report(
        database_path=getattr(chat_db, "CHAT_DB", None),
        ollama_url=getattr(chat_engine, "OLLAMA_URL", None),
        workforce_engine_count=len(workforce),
        asg_base_url=getattr(mod, "ASG_CORE_URL", None),
        asg_required=False,
    )

@app.get("/health")
def root_health():
    return _current_health_report()

@app.get("/ready")
def root_readiness():
    report = _current_health_report()
    return JSONResponse(report, status_code=200 if report["ready"] else 503)

import uvicorn
print('[wrapper] starting uvicorn on 127.0.0.1:9000')

# === EXPLICIT CORS (must be LAST to wrap everything) ===
try:
    import importlib.util as _ilu_cors
    _cp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aios_cors_explicit.py')
    if os.path.exists(_cp):
        _cs = _ilu_cors.spec_from_file_location('aios_cors_explicit', _cp)
        _cm = _ilu_cors.module_from_spec(_cs)
        sys.modules['aios_cors_explicit'] = _cm
        _cs.loader.exec_module(_cm)
        _cm.add_cors(app)
    else:
        print('[wrapper] WARN cors_explicit.py not found', file=sys.stderr)
except Exception as _e:
    print(f'[wrapper] FAIL cors_explicit: {_e}', file=sys.stderr)


# --- AIOS Security Middleware Injection (Track E2) ---
try:
    from aios_security import install_security as _aios_install_security
    _aios_install_security(app)
except Exception as _sec_err:
    import sys as _sys
    print(f'[security] WARNING: could not install security middleware: {_sec_err}', file=_sys.stderr)
# --- End AIOS Security Middleware Injection ---

uvicorn.run(app, host='127.0.0.1', port=9000, log_level='info', timeout_keep_alive=120)













