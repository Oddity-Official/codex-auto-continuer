// Install transport observation before VS Code's automatic extension activation.
const fs = require('node:fs');
const path = require('node:path');
const vscode = require('vscode');
const driver = require('./vscode_driver.cjs');
driver.prepare();
const originalRoot = process.env.CAC_VSCODE_EXTENSION;
const manifest = JSON.parse(fs.readFileSync(path.join(originalRoot, 'package.json'), 'utf8'));
const original = require(path.join(originalRoot, manifest.main));
exports.activate = context => original.activate(new Proxy(context, {
  get(target, property) {
    if (property === 'extensionPath') return originalRoot;
    if (property === 'extensionUri') return vscode.Uri.file(originalRoot);
    return Reflect.get(target, property);
  },
}));
exports.deactivate = original.deactivate;
