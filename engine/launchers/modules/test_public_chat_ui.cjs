const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const uiRoot = path.resolve(__dirname, '../../../LAUNCH_PUBLIC/public/royal_murshad_public_ui');
const client = require(path.join(uiRoot, 'chat_client.js'));

class FakeElement {
  constructor(id, children = {}) {
    this.id = id;
    this.children = children;
    this.listeners = {};
    this.value = '';
    this.textContent = '';
    this.disabled = false;
  }
  addEventListener(name, callback) {
    (this.listeners[name] ||= []).push(callback);
  }
  querySelector(selector) { return this.children[selector] || null; }
  cloneNode() {
    const copy = new FakeElement(this.id, {
      '#chatInput': new FakeElement('chatInput'),
      button: new FakeElement('submitButton'),
    });
    return copy;
  }
  replaceWith(replacement) { this.replacement = replacement; }
  async dispatch(name, event = {}) {
    for (const callback of this.listeners[name] || []) await callback({ preventDefault() {}, ...event });
  }
}

test('chat UI removes prototype submit handling and uses the local API after connection', async () => {
  const oldForm = new FakeElement('chatForm', {
    '#chatInput': new FakeElement('chatInput'),
    button: new FakeElement('submitButton'),
  });
  let prototypeResponses = 0;
  oldForm.addEventListener('submit', () => { prototypeResponses += 1; });
  const status = new FakeElement('backendStatus');
  const connect = new FakeElement('connectBtn');
  const clear = new FakeElement('clearChat');
  const username = new FakeElement('authUsername');
  username.value = 'local-admin';
  const password = new FakeElement('authPassword');
  password.value = require('node:crypto').randomBytes(24).toString('base64url');
  const messages = [];
  let modalAction;
  let posts = 0;
  let loginCalls = 0;
  let logoutCalls = 0;
  const document = {
    querySelector(selector) {
      if (selector === '#chatForm') return oldForm;
      if (selector === '#backendStatus') return status;
      if (selector === '#connectBtn') return connect;
      if (selector === '#clearChat') return clear;
      if (selector === '#backendUrl') return { value: 'http://127.0.0.1:9000' };
      if (selector === '#authUsername') return username;
      if (selector === '#authPassword') return password;
      return null;
    },
  };
  const root = {
    document,
    location: { origin: 'http://127.0.0.1:9000' },
    fetch: async (url, options) => {
      if (url.endsWith('/health')) return { ok: true, status: 200, json: async () => ({ live: true, ready: true }) };
      if (url.endsWith('/api/auth/login')) {
        loginCalls += 1;
        assert.equal(options.credentials, 'same-origin');
        assert.equal(JSON.parse(options.body).username, 'local-admin');
        return { ok: true, status: 200, json: async () => ({ ok: true, user: { role: 'admin' } }) };
      }
      if (url.endsWith('/api/auth/logout')) {
        logoutCalls += 1;
        assert.equal(options.credentials, 'same-origin');
        return { ok: true, status: 200, json: async () => ({ ok: true }) };
      }
      if (url.endsWith('/api/chat/send')) {
        posts += 1;
        assert.equal(options.credentials, 'same-origin');
        const sent = JSON.parse(options.body);
        return { ok: true, status: 200, json: async () => ({
          ok: true,
          conversation_id: sent.conversation_id || 'conv_local',
          assistant_message: { content: 'Real backend answer' },
        }) };
      }
      throw new Error('unexpected request');
    },
    addMessage: (text, who) => messages.push({ text, who }),
    showModal: (_title, _body, _primary, onPrimary) => { modalAction = onPrimary; },
    toast: () => {},
    setTimeout,
  };

  client.attachUI(root);
  const form = oldForm.replacement;
  assert.equal(status.textContent, 'Preview only · connect a local backend for AI chat');
  form.querySelector('#chatInput').value = 'hello';
  await form.dispatch('submit');
  assert.equal(posts, 0);
  assert.match(messages.at(-1).text, /Connect a local backend/);

  connect.onclick();
  await modalAction();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(loginCalls, 1);
  assert.equal(password.value, '');
  assert.equal(status.textContent, 'Connected · local chat ready');

  form.querySelector('#chatInput').value = '  ask the local model  ';
  await form.dispatch('submit');
  assert.equal(posts, 1);
  assert.equal(messages.at(-1).text, 'Real backend answer');
  assert.equal(messages.at(-1).who, 'assistant');
  assert.equal(prototypeResponses, 0);
  assert.equal(connect.textContent, 'Sign out');
  connect.onclick();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(logoutCalls, 1);
  assert.equal(status.textContent, 'Preview only · connect a local backend for AI chat');
});

test('public UI loads the connected chat client after its existing app script', () => {
  const html = fs.readFileSync(path.join(uiRoot, 'index.html'), 'utf8');
  assert.ok(html.indexOf('src="app.js"') < html.indexOf('src="chat_client.js"'));
});
