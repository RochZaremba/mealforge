// PWA service-worker checks require a real production build, as in deployment.
import { spawn, spawnSync } from 'node:child_process';

const build = spawnSync('pnpm', ['build'], { stdio: 'inherit', env: process.env });
if (build.error) throw build.error;
if (build.status !== 0) process.exit(build.status ?? 1);

const server = spawn('pnpm', ['start', '--hostname', '127.0.0.1', '--port', '3000'], {
  stdio: 'inherit',
  env: process.env,
});
server.on('error', (error) => {
  console.error(error);
  process.exit(1);
});
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.kill(signal));
}
server.on('exit', (code, signal) => {
  process.exit(code ?? (signal ? 1 : 0));
});
