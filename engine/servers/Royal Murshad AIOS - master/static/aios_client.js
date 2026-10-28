/* Royal AIOS — auto-generated client SDK.
   Each app auto-discovers its slug from the URL path or window.AIOS_APP_SLUG. */
(function(){
  const SLUG = window.AIOS_APP_SLUG || (function(){
    const m = location.pathname.match(/\/app\/([a-z0-9-]+)/i);
    return m ? m[1] : null;
  })() || (document.title.match(/royal[-\s]?([a-z]+)/i) || [])[1] || null;
  const API = 'http://127.0.0.1:9000';
  window.AIOS = {
    slug: SLUG,
    base: API,
    async list(limit=100){ return (await fetch(`${API}/api/apps/${SLUG}/records?limit=${limit}`)).json(); },
    async create(data){ return (await fetch(`${API}/api/apps/${SLUG}/records`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})).json(); },
    async get(id){ return (await fetch(`${API}/api/apps/${SLUG}/records/${id}`)).json(); },
    async update(id,data){ return (await fetch(`${API}/api/apps/${SLUG}/records/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})).json(); },
    async remove(id){ return (await fetch(`${API}/api/apps/${SLUG}/records/${id}`,{method:'DELETE'})).json(); },
    async stats(){ return (await fetch(`${API}/api/apps/${SLUG}/stats`)).json(); },
    async health(){ return (await fetch(`${API}/api/apps/${SLUG}/health`)).json(); },
    async registry(){ return (await fetch(`${API}/api/registry/apps`)).json(); }
  };
  console.log('[AIOS SDK] ready — slug=' + SLUG);
})();