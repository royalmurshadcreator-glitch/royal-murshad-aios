(function (root, factory) {
  const client = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = client;
  } else {
    root.AIOSChatClient = client;
    client.attachUI(root);
  }
})(typeof globalThis === 'undefined' ? this : globalThis, function () {
  class ChatClientError extends Error {
    constructor(code, status = 0) {
      super(code);
      this.name = 'ChatClientError';
      this.code = code;
      this.status = status;
    }
  }

  function normalizeBackendUrl(value) {
    let url;
    try {
      url = new URL(value);
    } catch (_) {
      throw new ChatClientError('invalid_backend_url');
    }
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
        !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname.toLowerCase()) ||
        (url.pathname && url.pathname !== '/') || url.search || url.hash) {
      throw new ChatClientError('local_backend_required');
    }
    return url.origin;
  }

  async function getHealth(baseUrl, fetchImpl = fetch, timeoutMs = 5000) {
    const origin = normalizeBackendUrl(baseUrl);
    const response = await requestJson(fetchImpl, origin + '/health', null, timeoutMs);
    if (response.live !== true) throw new ChatClientError('backend_not_live');
    if (response.ready !== true) throw new ChatClientError('backend_not_ready');
    return origin;
  }

  async function login({ baseUrl, username, password, fetchImpl = fetch, timeoutMs = 10000 }) {
    const origin = normalizeBackendUrl(baseUrl);
    if (typeof username !== 'string' || !username.trim() || typeof password !== 'string' || !password) {
      throw new ChatClientError('credentials_required');
    }
    const result = await requestJson(fetchImpl, origin + '/api/auth/login', {
      username: username.trim(), password,
    }, timeoutMs, 'same-origin');
    if (result.ok !== true) throw new ChatClientError('login_failed');
    return result.user || {};
  }

  async function logout({ baseUrl, fetchImpl = fetch, timeoutMs = 5000 }) {
    const origin = normalizeBackendUrl(baseUrl);
    await requestJson(fetchImpl, origin + '/api/auth/logout', {}, timeoutMs, 'same-origin');
  }

  async function sendMessage({ baseUrl, conversationId = '', message, fetchImpl = fetch, timeoutMs = 90000 }) {
    const origin = normalizeBackendUrl(baseUrl);
    if (typeof message !== 'string' || !message.trim()) throw new ChatClientError('empty_message');
    const data = await requestJson(fetchImpl, origin + '/api/chat/send', {
      conversation_id: conversationId || '',
      message: message.trim(),
    }, timeoutMs, 'same-origin');

    if (data.ok !== true) {
      const error = String(data.error || '').toLowerCase();
      if (error.includes('ollama') || error.includes('model')) throw new ChatClientError('model_unavailable');
      if (error.includes('blocked')) throw new ChatClientError('message_blocked');
      throw new ChatClientError('chat_failed');
    }
    const assistant = data.assistant_message;
    const content = typeof assistant === 'string' ? assistant : assistant && assistant.content;
    if (typeof content !== 'string' || !content.trim()) throw new ChatClientError('invalid_chat_response');
    return {
      conversationId: data.conversation_id || conversationId || '',
      message: content,
      model: typeof data.model === 'string' ? data.model : '',
    };
  }

  async function requestJson(fetchImpl, url, body, timeoutMs, credentials = 'omit') {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetchImpl(url, {
        method: body === null ? 'GET' : 'POST',
        headers: body === null ? { Accept: 'application/json' } : {
          Accept: 'application/json', 'Content-Type': 'application/json',
        },
        body: body === null ? undefined : JSON.stringify(body),
        credentials,
        cache: 'no-store',
        signal: controller.signal,
      });
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) throw new ChatClientError('permission_denied', response.status);
        if (response.status === 404) throw new ChatClientError('endpoint_not_found', response.status);
        throw new ChatClientError('backend_http_error', response.status);
      }
      try {
        return await response.json();
      } catch (_) {
        throw new ChatClientError('invalid_backend_response', response.status);
      }
    } catch (error) {
      if (error instanceof ChatClientError) throw error;
      if (error && error.name === 'AbortError') throw new ChatClientError('request_timeout');
      throw new ChatClientError('backend_unavailable');
    } finally {
      clearTimeout(timer);
    }
  }

  function attachUI(root) {
    const document = root.document;
    if (!document) return;
    const form = document.querySelector('#chatForm');
    const status = document.querySelector('#backendStatus');
    const connectButton = document.querySelector('#connectBtn');
    if (!form || !status || !connectButton) return;

    let backendBase = null;
    let conversationId = '';
    let busy = false;
    status.textContent = 'Preview only · connect a local backend for AI chat';

    // Replacing the form detaches the prototype's predetermined-answer handler.
    const connectedForm = form.cloneNode(true);
    form.replaceWith(connectedForm);
    const input = connectedForm.querySelector('#chatInput');
    const sendButton = connectedForm.querySelector('button');

    connectedForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text || busy) return;
      if (!backendBase) {
        root.addMessage('Connect a local backend to send this message to AI. Preview replies are disabled.', 'assistant');
        return;
      }
      root.addMessage(text, 'user');
      input.value = '';
      busy = true;
      if (sendButton) sendButton.disabled = true;
      status.textContent = 'Local AI is responding…';
      try {
        const result = await sendMessage({
          baseUrl: backendBase,
          conversationId,
          message: text,
          fetchImpl: root.fetch.bind(root),
        });
        conversationId = result.conversationId;
        root.addMessage(result.message, 'assistant');
        status.textContent = 'Connected · local chat active';
      } catch (error) {
        status.textContent = 'Connected · chat request needs attention';
        root.addMessage(friendlyError(error), 'assistant');
      } finally {
        busy = false;
        if (sendButton) sendButton.disabled = false;
      }
    });

    connectButton.onclick = () => {
      if (backendBase) {
        status.textContent = 'Signing out…';
        void logout({ baseUrl: backendBase, fetchImpl: root.fetch.bind(root) }).then(() => {
          backendBase = null;
          conversationId = '';
          connectButton.textContent = 'Connect backend';
          status.textContent = 'Preview only · connect a local backend for AI chat';
          if (typeof root.toast === 'function') root.toast('Signed out of local AIOS chat.');
        }).catch((error) => {
          status.textContent = 'Sign-out failed · session may still be active';
          if (typeof root.toast === 'function') root.toast(friendlyError(error));
        });
        return;
      }
      if (typeof root.showModal !== 'function') return;
      root.showModal(
        'Connect local AI backend',
        '<p>Connect this browser to the local Royal Murshad AIOS service. Only loopback addresses are accepted; this page does not store credentials.</p>' +
          '<label for="backendUrl">Local backend URL</label><input id="backendUrl" value="' +
          (root.location && /^https?:\/\//.test(root.location.origin) ? root.location.origin : 'http://127.0.0.1:9000') +
          '" style="display:block;width:100%;margin-top:8px;padding:11px;border:1px solid #3a4554;background:#080d14;color:white;border-radius:8px">' +
          '<label for="authUsername">Administrator username</label><input id="authUsername" autocomplete="username" style="display:block;width:100%;margin-top:8px;padding:11px;border:1px solid #3a4554;background:#080d14;color:white;border-radius:8px">' +
          '<label for="authPassword">Administrator password</label><input id="authPassword" type="password" autocomplete="current-password" style="display:block;width:100%;margin-top:8px;padding:11px;border:1px solid #3a4554;background:#080d14;color:white;border-radius:8px">' +
          '<p>Credentials are sent only to the loopback backend and are not stored by this page.</p>',
        'Connect',
        () => {
          const field = document.querySelector('#backendUrl');
          void (async () => {
            try {
              status.textContent = 'Checking local backend readiness…';
              const checkedBase = await getHealth(field && field.value, root.fetch.bind(root));
              if (root.location && root.location.origin !== checkedBase) throw new ChatClientError('same_origin_backend_required');
              const usernameField = document.querySelector('#authUsername');
              const passwordField = document.querySelector('#authPassword');
              const password = passwordField && passwordField.value;
              if (passwordField) passwordField.value = '';
              await login({
                baseUrl: checkedBase,
                username: usernameField && usernameField.value,
                password,
                fetchImpl: root.fetch.bind(root),
              });
              backendBase = checkedBase;
              conversationId = '';
              connectButton.textContent = 'Sign out';
              status.textContent = 'Connected · local chat ready';
              if (typeof root.toast === 'function') root.toast('Local backend is ready for chat.');
            } catch (error) {
              backendBase = null;
              status.textContent = 'Not connected · local backend unavailable';
              if (typeof root.toast === 'function') root.toast(friendlyError(error));
            }
          })();
        },
      );
    };

    const clearButton = document.querySelector('#clearChat');
    if (clearButton) clearButton.addEventListener('click', () => {
      conversationId = '';
      root.setTimeout(() => {
        const messages = document.querySelector('#chatMessages');
        const last = messages && messages.lastElementChild;
        if (last && last.classList.contains('assistant')) {
          last.textContent = 'New chat started. Earlier conversations remain saved on the backend.';
        }
      }, 0);
    });
  }

  function friendlyError(error) {
    const code = error && error.code;
    if (code === 'request_timeout') return 'The request timed out. The backend may still be processing; check before retrying.';
    if (code === 'backend_not_ready') return 'The backend is running, but chat dependencies are not ready. Check Ollama and the chat database.';
    if (code === 'permission_denied') return 'The backend denied this request. Check the configured account or permission requirements.';
    if (code === 'credentials_required' || code === 'login_failed') return 'Local administrator sign-in failed. Check the account or provision the first administrator locally.';
    if (code === 'same_origin_backend_required') return 'Open this UI from the local backend address so the session cookie stays same-origin.';
    if (code === 'model_unavailable') return 'The local model could not complete this request. Check Ollama and the selected model.';
    if (code === 'message_blocked') return 'The backend safety checks declined this message.';
    if (code === 'invalid_backend_url' || code === 'local_backend_required') return 'Use a local loopback backend URL such as http://127.0.0.1:9000.';
    return 'The local chat request failed. Check the backend status and try again.';
  }

  return { ChatClientError, normalizeBackendUrl, getHealth, login, logout, sendMessage, requestJson, attachUI, friendlyError };
});
