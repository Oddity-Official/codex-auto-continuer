// Runs inside VS Code's official extension test host, not the user's profile.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const childProcess = require('node:child_process');
const { StringDecoder } = require('node:string_decoder');
const vscode = require('vscode');

exports.prepare = function () {
  const directory = process.env.CAC_VSCODE_TEST;
  assert(directory, 'Missing isolated extension-test directory');
  const pending = new Map();
  const completed = [];
  let child;
  let initialization;
  let sequence = -1000000;
  const originalSpawn = childProcess.spawn;
  const save = (name, value) => {
    const target = path.join(directory, name);
    fs.writeFileSync(`${target}.tmp`, JSON.stringify(value));
    fs.renameSync(`${target}.tmp`, target);
  };
  const waitFor = async (condition, label, seconds = 30) => {
    const deadline = Date.now() + seconds * 1000;
    while (Date.now() < deadline) {
      const value = condition();
      if (value) return value;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error(`Extension fixture timed out waiting for ${label}`);
  };
  const request = (method, params) => new Promise((resolve, reject) => {
    const id = sequence--;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Extension fixture RPC timeout: ${method}`));
    }, 10000);
    pending.set(id, message => {
      clearTimeout(timer);
      if (message.error) reject(new Error(`${method}: ${JSON.stringify(message.error)}`));
      else resolve(message.result);
    });
    child.stdin.write(`${JSON.stringify({ id, method, params })}\n`);
  });
  // Read-only taps leave the extension's own initialize, responses and events intact.
  childProcess.spawn = function (file, args, options) {
    const result = originalSpawn.apply(this, arguments);
    if (args?.includes('app-server') && options?.env?.CODEX_INTERNAL_ORIGINATOR_OVERRIDE === 'codex_vscode') {
      assert(!child, 'Expected one VS Code native app-server owner');
      child = result;
      const write = child.stdin.write;
      child.stdin.write = function (data) {
        for (const line of data.toString().split('\n').filter(Boolean)) {
          const message = JSON.parse(line);
          if (message.method === 'initialize') initialization = message.params.clientInfo;
        }
        return write.apply(this, arguments);
      };
      const decoder = new StringDecoder('utf8');
      let buffer = '';
      child.stdout.on('data', bytes => {
        buffer += decoder.write(bytes);
        let end;
        while ((end = buffer.indexOf('\n')) >= 0) {
          const line = buffer.slice(0, end);
          buffer = buffer.slice(end + 1);
          if (!line.trim()) continue;
          const message = JSON.parse(line);
          const reply = pending.get(message.id);
          if (reply) {
            pending.delete(message.id);
            reply(message);
          }
          if (message.method === 'turn/completed') completed.push(message.params);
        }
      });
      save('owner.json', { executable: file, pid: child.pid,
        originator: options.env.CODEX_INTERNAL_ORIGINATOR_OVERRIDE });
    }
    return result;
  };
  exports.run = async function () {
    try {
      const extension = vscode.extensions.getExtension('openai.chatgpt');
      assert(extension, 'Official Codex extension was not loaded');
      await extension.activate();
      await vscode.commands.executeCommand('chatgpt.openSidebar');
      await waitFor(() => child && initialization, 'extension-owned initialized native transport');
      assert.equal(initialization.name, 'VS Code');
      assert.equal(initialization.title, 'Codex Extension');
      const thread = (await request('thread/start', { cwd: directory,
        approvalPolicy: 'never', sandbox: 'read-only',
        baseInstructions: 'Do not use tools. Reply CAC_FIXTURE_OK.' })).thread;
      const first = (await request('turn/start', { threadId: thread.id,
        input: [{ type: 'text', text: 'VS Code quota fixture' }] })).turn;
      await waitFor(() => completed.find(note => note.threadId === thread.id && note.turn.id === first.id),
        'extension quota failure');
      save('failed.json', { threadId: thread.id, failedTurnId: first.id, initialization,
        extensionVersion: extension.packageJSON.version, vscodeVersion: vscode.version });
      const recovered = await waitFor(() => completed.find(note => note.threadId === thread.id
        && note.turn.id !== first.id), 'CAC continuation on extension owner', 90);
      assert.equal(recovered.turn.status, 'completed');
      const history = await request('thread/turns/list', { threadId: thread.id, limit: 100,
        sortDirection: 'asc', itemsView: 'notLoaded' });
      assert.equal(history.data.length, 2);
      save('completed.json', { turnId: recovered.turn.id, status: recovered.turn.status,
        turns: history.data.length });
      await waitFor(() => fs.existsSync(path.join(directory, 'finish')), 'observer assertions', 30);
    } catch (error) {
      save('error.json', { error: String(error) });
      throw error;
    } finally {
      childProcess.spawn = originalSpawn;
    }
  };
};
