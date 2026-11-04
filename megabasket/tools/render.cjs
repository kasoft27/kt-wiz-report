#!/usr/bin/env node
/*
 * 메가바스켓 후킹 릴스 렌더러
 *   node megabasket/tools/render.cjs                 → 전체 렌더 (영상 + 효과음 + 커버)
 *   node megabasket/tools/render.cjs --frames 0,1.2  → 지정 시각 PNG만 저장 (검수용)
 *
 * 1) index.html?render=1 을 1080×1920 헤드리스 크로미움으로 열고
 * 2) window.__seek(t)로 30fps 프레임을 하나씩 캡처해 ffmpeg로 인코딩한 뒤
 * 3) 페이지의 효과음 큐(window.__meta)를 sfx.py로 합성해 영상에 입힙니다.
 * 필요: Node + playwright, ffmpeg, python3 + numpy
 */
const { chromium } = require('playwright');
const { spawn, spawnSync } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const arg = (k, d) => args.includes(k) ? args[args.indexOf(k) + 1] : d;
// --page blog_review/index.html --name 파일이름 --cover 커버시각(초)  (기본값은 26초 후킹 릴스)
const PAGE = arg('--page', 'index.html');
const NAME = arg('--name', 'megabasket_hook_reel_26s');
const COVER_T = parseFloat(arg('--cover', '1.25'));
const OUT = process.env.OUT_DIR ? path.resolve(process.env.OUT_DIR) : path.dirname(path.join(ROOT, PAGE));
const framesArg = args.includes('--frames') ? args[args.indexOf('--frames') + 1] : null;

const MIME = { '.html': 'text/html; charset=utf-8', '.woff2': 'font/woff2', '.jpg': 'image/jpeg', '.png': 'image/png', '.js': 'text/javascript', '.m4a': 'audio/mp4', '.mp4': 'video/mp4' };
function serve() {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(srv));
  });
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const srv = await serve();
  const url = `http://127.0.0.1:${srv.address().port}/${PAGE}?render=1`;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('[page error]', e.message));
  await page.goto(url);
  await page.evaluate(() => window.__ready);
  const meta = await page.evaluate(() => window.__meta);

  if (framesArg) {
    for (const s of framesArg.split(',')) {
      const t = parseFloat(s);
      await page.evaluate(t => window.__seek(t), t);
      const f = path.join(OUT, `frame_${t.toFixed(3)}.png`);
      await page.screenshot({ path: f });
      console.log('saved', f);
    }
    await browser.close(); srv.close(); return;
  }

  const total = Math.round(meta.D * meta.FPS);
  const silent = path.join(OUT, `${NAME}_silent.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(meta.FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(meta.FPS),
    '-movflags', '+faststart', silent], { stdio: ['pipe', 'inherit', 'inherit'] });
  const write = buf => new Promise(r => ff.stdin.write(buf) ? r() : ff.stdin.once('drain', r));
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const t = i / meta.FPS;
    await page.evaluate(t => window.__seek(t), t);
    await write(await page.screenshot({ type: 'jpeg', quality: 96 }));
    if (i % 60 === 0) console.log(`frame ${i}/${total}  (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));

  // 커버(그리드용 9:16)
  await page.evaluate(t => window.__seek(t), COVER_T);
  await page.screenshot({ path: path.join(OUT, `${NAME}_cover.jpg`), type: 'jpeg', quality: 92 });
  await browser.close(); srv.close();

  if (meta.audio === false) {  // 음악·효과음 없는 버전
    fs.renameSync(silent, path.join(OUT, `${NAME}.mp4`));
    console.log('done (no audio):', path.join(OUT, `${NAME}.mp4`), `(${((Date.now() - t0) / 1000).toFixed(0)}s)`);
    return;
  }
  // 효과음 합성 → 영상에 입히기
  const cues = path.join(OUT, `${NAME}_cues.json`);
  const wav = path.join(OUT, `${NAME}.wav`);
  fs.writeFileSync(cues, JSON.stringify(meta, null, 1));
  const py = spawnSync('python3', ['-I', path.join(__dirname, 'sfx.py'), cues, wav], { stdio: 'inherit' });
  if (py.status !== 0) throw new Error('sfx.py failed');
  const final = path.join(OUT, `${NAME}.mp4`);
  spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
    '-shortest', '-movflags', '+faststart', final], { stdio: 'inherit' });
  spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', wav, '-c:a', 'aac', '-b:a', '160k', path.join(OUT, `${NAME}.m4a`)], { stdio: 'inherit' });
  fs.unlinkSync(wav); fs.unlinkSync(cues);
  if (!process.env.KEEP_SILENT) fs.unlinkSync(silent);
  console.log('done:', final, `(${((Date.now() - t0) / 1000).toFixed(0)}s)`);
})().catch(e => { console.error(e); process.exit(1); });
