import { execFile } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);
const fixturesDir = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(fixturesDir, '../../../backend');
const scriptPath = path.join(fixturesDir, 'issue_magic_link.py');

function pythonBin(): string {
  const candidates = [
    path.join(backendDir, '.venv', 'Scripts', 'python.exe'),
    path.join(backendDir, 'venv', 'Scripts', 'python.exe'),
  ];
  return candidates.find((candidate) => existsSync(candidate)) ?? 'python';
}

async function runSeed(argument?: string): Promise<string> {
  const args = argument ? [scriptPath, argument] : [scriptPath];
  const { stdout } = await execFileAsync(pythonBin(), args, {
    cwd: backendDir,
    env: {
      ...process.env,
      PYTHONPATH: backendDir,
      TEST_DATABASE_URL:
        process.env.TEST_DATABASE_URL ??
        'postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/postgres',
    },
  });
  return stdout;
}

/** Insert this spec's user, receipt, and magic link. Returns the token. */
export async function issueMagicLink(): Promise<string> {
  const payload = JSON.parse(await runSeed()) as { token: string };
  return payload.token;
}

/** Delete only the user this spec created. */
export async function cleanupMagicLink(): Promise<void> {
  await runSeed('--cleanup');
}
