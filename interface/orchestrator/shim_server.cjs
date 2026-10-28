'use strict';
const http = require('http');
const path = require('path');
const fs = require('fs');

const { Orchestrator } = require('./src/orchestrator.cjs');
const { createApiHandler } = require('./src/api-adapter.cjs');

const dataDir = path.join('D:\\01_PROJECTS\\AIOS', '08_DATA', 'orchestrator');
fs.mkdirSync(dataDir, { recursive: true });

const orchestrator = new Orchestrator({
  dataDir,
  adapter: {
    kind: 'autopilot',
    autopilotPythonPath: 'D:\\01_PROJECTS\\AIOS\\18_ENV\\.venv\\Scripts\\python.exe',
    autopilotScriptPath: 'D:\\01_PROJECTS\\AIOS\\06_TOOLS\\aios_computer_use\\autopilot\\RoyalExecutor.py',
    autopilotTimeoutMs: 120000
  },
  maxConcurrency: 1
});

const handle = createApiHandler(orchestrator);

const server = http.createServer(async (req, res) => {
  try {
    const handled = await handle(req, res);
    if (handled === false) {
      res.statusCode = 404;
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ ok: false, error: 'not_found', path: req.url }));
    }
  } catch (err) {
    if (!res.headersSent) {
      res.statusCode = 500;
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ ok: false, error: String(err && err.message || err) }));
    }
  }
});

server.listen(9180, '127.0.0.1', () => {
  console.log('AIOS_ORCHESTRATOR_READY 9180');
});
