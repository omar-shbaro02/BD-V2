import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const venvPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.PYTHON || (existsSync(venvPython) ? venvPython : process.platform === 'win32' ? 'python' : 'python3');
const child = spawn(python, [
  '-m', 'uvicorn', 'vai_bd.main:app', '--app-dir', 'src', '--reload',
  ...process.argv.slice(2),
], { cwd: root, stdio: 'inherit' });

child.on('error', (error) => {
  console.error(`Could not start Python: ${error.message}`);
  console.error('Install the Python dependencies described in README.md, or set PYTHON to your Python executable.');
  process.exitCode = 1;
});
child.on('exit', (code, signal) => {
  process.exitCode = code ?? (signal === 'SIGINT' ? 0 : 1);
});
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal));
}
