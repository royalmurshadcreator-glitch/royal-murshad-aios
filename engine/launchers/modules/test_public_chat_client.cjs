const assert = require('node:assert/strict');
const test = require('node:test');

const client = require('../../../LAUNCH_PUBLIC/public/royal_murshad_public_ui/chat_client.js');

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test('only loopback backend URLs are accepted and credentials are rejected', () => {
  assert.equal(client.normalizeBackendUrl('http://127.0.0.1:9000/'), 'http://127.0.0.1:9000');
  assert.equal(client.normalizeBackendUrl('http://localhost:9000'), 'http://localhost:9000');
  assert.throws(() => client.normalizeBackendUrl('https://example.org'), { code: 'local_backend_required' });
  assert.throws(() => client.normalizeBackendUrl('http://user:pass@127.0.0.1:9000'), { code: 'local_backend_required' });
  assert.throws(() => client.normalizeBackendUrl('http://127.0.0.1:9000/private'), { code: 'local_backend_required' });
});

test('health connection requires both live and ready status', async () => {
  let requested;
  const base = await client.getHealth('http://127.0.0.1:9000', async (url, options) => {
    requested = { url, options };
    return response({ live: true, ready: true, status: 'degraded' });
  });
  assert.equal(base, 'http://127.0.0.1:9000');
  assert.equal(requested.url, 'http://127.0.0.1:9000/health');
  assert.equal(requested.options.credentials, 'omit');
  await assert.rejects(
    client.getHealth('http://127.0.0.1:9000', async () => response({ live: true, ready: false })),
    { code: 'backend_not_ready' },
  );
});

test('chat sends the typed message and returns the real assistant payload', async () => {
  let request;
  const result = await client.sendMessage({
    baseUrl: 'http://127.0.0.1:9000',
    conversationId: 'conv_test',
    message: '  hello local model  ',
    fetchImpl: async (url, options) => {
      request = { url, options, body: JSON.parse(options.body) };
      return response({
        ok: true,
        conversation_id: 'conv_test',
        assistant_message: { content: 'Real response' },
        model: 'qwen2.5:3b',
      });
    },
  });
  assert.equal(request.url, 'http://127.0.0.1:9000/api/chat/send');
  assert.deepEqual(request.body, { conversation_id: 'conv_test', message: 'hello local model' });
  assert.equal(request.options.credentials, 'same-origin');
  assert.equal(result.conversationId, 'conv_test');
  assert.equal(result.message, 'Real response');
});

test('model and permission failures are surfaced as typed errors', async () => {
  await assert.rejects(
    client.sendMessage({
      baseUrl: 'http://127.0.0.1:9000', message: 'hello',
      fetchImpl: async () => response({ ok: false, error: 'ollama offline' }),
    }),
    { code: 'model_unavailable' },
  );
  await assert.rejects(
    client.sendMessage({
      baseUrl: 'http://127.0.0.1:9000', message: 'hello',
      fetchImpl: async () => response({}, 403),
    }),
    { code: 'permission_denied' },
  );
});

test('local administrator login sends credentials only to same-origin session endpoint', async () => {
  let request;
  const password = require('node:crypto').randomBytes(24).toString('base64url');
  const user = await client.login({
    baseUrl: 'http://127.0.0.1:9000',
    username: 'local-admin',
    password,
    fetchImpl: async (url, options) => {
      request = { url, options, body: JSON.parse(options.body) };
      return response({ ok: true, user: { role: 'admin' } });
    },
  });
  assert.equal(request.url, 'http://127.0.0.1:9000/api/auth/login');
  assert.equal(request.options.credentials, 'same-origin');
  assert.equal(request.body.username, 'local-admin');
  assert.equal(request.body.password, password);
  assert.equal(user.role, 'admin');
});

test('logout invalidates the same-origin server session without exposing a token', async () => {
  let request;
  await client.logout({
    baseUrl: 'http://127.0.0.1:9000',
    fetchImpl: async (url, options) => {
      request = { url, options };
      return response({ ok: true });
    },
  });
  assert.equal(request.url, 'http://127.0.0.1:9000/api/auth/logout');
  assert.equal(request.options.method, 'POST');
  assert.equal(request.options.credentials, 'same-origin');
  assert.equal(Object.hasOwn(request.options, 'Authorization'), false);
});

test('timeout is bounded and returned as a retry-aware failure', async () => {
  await assert.rejects(
    client.sendMessage({
      baseUrl: 'http://127.0.0.1:9000', message: 'hello', timeoutMs: 5,
      fetchImpl: (_url, options) => new Promise((_, reject) => {
        options.signal.addEventListener('abort', () => reject({ name: 'AbortError' }), { once: true });
      }),
    }),
    { code: 'request_timeout' },
  );
});
