#!/usr/bin/env node
// 自托管的 Star History 生成器：零第三方依赖，只用 Node.js 标准库和内置 fetch。
//
// 背景：GitHub 在 2026-06-30 收紧了 stargazers 列表接口，依赖它的在线图表服务集体挂掉；
// GitHub 随后提供了只含数量、不含用户信息的隐私安全接口（2026-09-04）：
//   GET /repos/{owner}/{repo}/stargazers/history
// 本脚本用它把 star 历史抓下来，渲染成一张静态 SVG 提交到 star-history 分支，
// README 直接引用 raw 文件即可，不再依赖任何在线图表服务，也不会再被限流。
//
// 用法：
//   GITHUB_TOKEN=xxx node .github/scripts/star-history.mjs <输出目录> [owner/repo]
//   STAR_HISTORY_CACHE=raw-weeks.json node .github/scripts/star-history.mjs <输出目录>   # 离线渲染，便于本地验证
//
// 产物：<输出目录>/history.json（日期 + 累计 star 数）和 <输出目录>/star-history.svg
// 说明：抓取失败时若输出目录已有旧图，会保留旧图并以 0 退出，避免把 CI 弄红、把好数据覆盖掉。

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const API_ROOT = process.env.GITHUB_API_URL ?? 'https://api.github.com';
const API_VERSION = '2026-03-10';
const MAX_PAGES = 100; // GitHub 侧上限，约 57 年，够用了
const DAY_MS = 24 * 60 * 60 * 1000;

const outDir = path.resolve(process.argv[2] ?? process.env.STAR_HISTORY_DIR ?? 'star-history-data');
const repository =
  process.argv[3] ??
  process.env.STAR_HISTORY_REPO ??
  process.env.GITHUB_REPOSITORY ??
  'miaojiuqing/MAA_bbb';
const token =
  process.env.STAR_HISTORY_TOKEN ?? process.env.GH_TOKEN ?? process.env.GITHUB_TOKEN ?? '';
const cacheFile = process.env.STAR_HISTORY_CACHE ?? '';

const log = (...args) => console.log('[star-history]', ...args);

/** 按周取回完整 star 历史（新的一周在前）。 */
async function fetchWeeklyHistory(repo, authToken) {
  let url = `${API_ROOT}/repos/${repo}/stargazers/history?per_page=100`;
  const weeks = [];
  let sendApiVersion = true; // 少数情况下版本头不被接受时，去掉它再试一次

  for (let page = 1; page <= MAX_PAGES && url; page++) {
    let res;
    try {
      res = await requestPage(url, authToken, sendApiVersion);
    } catch (error) {
      if (sendApiVersion && [400, 406, 415].includes(error.status)) {
        log(`带 X-GitHub-Api-Version 请求被拒（${error.status}），改为不带版本头重试`);
        sendApiVersion = false;
        res = await requestPage(url, authToken, sendApiVersion);
      } else {
        throw error;
      }
    }

    const body = await res.json();
    if (!Array.isArray(body)) {
      throw new Error(`接口返回了预期之外的数据：${JSON.stringify(body).slice(0, 200)}`);
    }
    weeks.push(...body);
    log(`第 ${page} 页：${body.length} 周`);

    url = nextPageUrl(res.headers.get('link'));
    if (body.length === 0) break;
  }

  return weeks;
}

async function requestPage(url, authToken, sendApiVersion) {
  const headers = {
    Accept: 'application/vnd.github+json',
    'User-Agent': 'star-history-generator',
    ...(sendApiVersion ? { 'X-GitHub-Api-Version': API_VERSION } : {}),
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
  };

  const res = await fetch(url, { headers });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    const error = new Error(`GitHub API ${res.status} ${res.statusText} (${url}) ${detail.slice(0, 200)}`);
    error.status = res.status;
    throw error;
  }
  return res;
}

/** 从 Link 头里取出 rel="next"。 */
function nextPageUrl(linkHeader) {
  if (!linkHeader) return null;
  for (const part of linkHeader.split(',')) {
    const match = /<([^>]+)>\s*;\s*rel="next"/.exec(part.trim());
    if (match) return match[1];
  }
  return null;
}

const isoDate = (unixSeconds) => new Date(unixSeconds * 1000).toISOString().slice(0, 10);

/** 把「每周一条、days 从周日开始」的原始数据压成「有变化的日期 + 当日累计 star 数」。 */
function toPoints(weeks) {
  const sorted = [...weeks]
    .filter((w) => w && Number.isFinite(w.week))
    .sort((a, b) => a.week - b.week);

  const points = [];
  let cumulative = 0;

  for (const week of sorted) {
    const days = Array.isArray(week.days) && week.days.length === 7 ? week.days : null;

    if (!days) {
      // 理论上不会走到这里；真遇到没有 days 的响应就用周总量兜底。
      const total = Number(week.total) || 0;
      if (total > 0) {
        cumulative += total;
        points.push({ date: isoDate(week.week), stars: cumulative });
      }
      continue;
    }

    for (let i = 0; i < 7; i++) {
      const delta = Number(days[i]) || 0;
      if (delta <= 0) continue;
      cumulative += delta;
      points.push({ date: isoDate(week.week + i * 86400), stars: cumulative });
    }
  }

  return points;
}

/** 取一个好看的刻度间隔（1/2/5/10 × 10^n，和 d3 的取法一致）。 */
function niceStep(raw) {
  if (!Number.isFinite(raw) || raw <= 0) return 1;
  const exponent = Math.floor(Math.log10(raw));
  const base = 10 ** exponent;
  const error = raw / base;
  const factor = error >= 7.07 ? 10 : error >= 3.16 ? 5 : error >= 1.41 ? 2 : 1;
  return factor * base;
}

function formatCount(n) {
  if (n < 1000) return String(n);
  if (n < 10000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}K`;
  if (n < 1e6) return `${Math.round(n / 1000)}K`;
  return `${(n / 1e6).toFixed(1).replace(/\.0$/, '')}M`;
}

function formatTick(ts, spanDays) {
  const d = new Date(ts);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return spanDays >= 150 ? `${y}-${m}` : `${m}-${day}`;
}

const escapeXml = (value) =>
  String(value).replace(
    /[<>&'"]/g,
    (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' })[c],
  );

/** 渲染自包含的 SVG：浅色/深色跟随 README 主题。 */
function renderSvg(repo, points) {
  const W = 800;
  const H = 500;
  const pad = { top: 78, right: 44, bottom: 58, left: 82 };
  const plotW = W - pad.left - pad.right;
  const plotH = H - pad.top - pad.bottom;

  const first = Date.parse(`${points[0].date}T00:00:00Z`);
  const lastRaw = Date.parse(`${points.at(-1).date}T00:00:00Z`);
  const last = lastRaw > first ? lastRaw : first + DAY_MS;
  const spanDays = Math.max(1, Math.round((last - first) / DAY_MS));

  const stars = points.at(-1).stars;
  const step = Math.max(1, niceStep(Math.max(1, stars) / 4)); // star 数是整数，刻度间隔不取小数
  const yMax = Math.max(step, Math.ceil(stars / step) * step);

  const px = (ts) => pad.left + ((ts - first) / (last - first)) * plotW;
  const py = (v) => pad.top + plotH - (v / yMax) * plotH;

  const line = points
    .map((p, i) => {
      const x = px(Date.parse(`${p.date}T00:00:00Z`)).toFixed(1);
      const y = py(p.stars).toFixed(1);
      return `${i === 0 ? 'M' : 'L'}${x} ${y}`;
    })
    .join(' ');
  const area = `${line} L${(pad.left + plotW).toFixed(1)} ${(pad.top + plotH).toFixed(1)} L${pad.left} ${(pad.top + plotH).toFixed(1)} Z`;

  const yTicks = [];
  for (let v = 0; v <= yMax + 1e-9; v += step) {
    yTicks.push(
      `<g class="tick"><line x1="${pad.left}" y1="${py(v).toFixed(1)}" x2="${(pad.left + plotW).toFixed(1)}" y2="${py(v).toFixed(1)}"/>` +
        `<text x="${pad.left - 12}" y="${py(v).toFixed(1)}" dy="0.32em" text-anchor="end">${escapeXml(formatCount(Math.round(v)))}</text></g>`,
    );
  }

  const xTickCount = 5;
  const xTicks = [];
  const seenLabels = new Set();
  for (let i = 0; i < xTickCount; i++) {
    const ts = first + ((last - first) * i) / (xTickCount - 1);
    const label = formatTick(ts, spanDays);
    if (seenLabels.has(label)) continue; // 时间跨度很短时避免重复刻度
    seenLabels.add(label);
    xTicks.push(
      `<text x="${px(ts).toFixed(1)}" y="${(pad.top + plotH + 24).toFixed(1)}" text-anchor="middle">${escapeXml(label)}</text>`,
    );
  }

  const endX = px(last);
  const endY = py(stars);
  const labelAnchor = endX > pad.left + plotW - 90 ? 'end' : 'start';
  const labelX = labelAnchor === 'end' ? endX - 12 : Math.min(endX + 12, pad.left + plotW);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="star-history-title">
  <title id="star-history-title">${escapeXml(repo)} Star History</title>
  <desc>${escapeXml(`${repo} 的 GitHub star 增长曲线，截至 ${points.at(-1).date} 共 ${stars} 个 star。`)}</desc>
  <style>
    .bg { fill: #ffffff; }
    .panel { fill: #ffffff; }
    .title { fill: #24292f; font: 600 22px "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
    .subtitle { fill: #57606a; font: 400 14px "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
    .tick { fill: #57606a; font: 400 12px "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
    .tick line { stroke: #d8dee4; stroke-width: 1; }
    .axis { stroke: #d0d7de; stroke-width: 1; }
    .axis-label { fill: #57606a; font: 400 13px "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
    .area { fill: rgba(221, 69, 40, 0.14); }
    .line { fill: none; stroke: #dd4528; stroke-width: 2.5; stroke-linejoin: round; stroke-linecap: round; }
    .dot { fill: #dd4528; }
    .value { fill: #dd4528; font: 600 13px "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
    .badge { fill: #dd4528; }
    .badge-text { fill: #ffffff; font: 600 13px "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
    @media (prefers-color-scheme: dark) {
      .bg, .panel { fill: #0d1117; }
      .title { fill: #e6edf3; }
      .subtitle, .tick, .axis-label { fill: #8b949e; }
      .tick line { stroke: #21262d; }
      .axis { stroke: #30363d; }
      .area { fill: rgba(255, 123, 90, 0.15); }
      .line { stroke: #ff7b5a; }
      .dot { fill: #ff7b5a; }
      .value { fill: #ff7b5a; }
      .badge { fill: #ff7b5a; }
      .badge-text { fill: #0d1117; }
    }
  </style>
  <rect class="bg" x="0" y="0" width="${W}" height="${H}"/>
  <text class="title" x="${pad.left}" y="40">Star History</text>
  <text class="subtitle" x="${pad.left}" y="62">${escapeXml(repo)}</text>
  <g class="ticks">${yTicks.join('\n    ')}</g>
  <line class="axis" x1="${pad.left}" y1="${(pad.top + plotH).toFixed(1)}" x2="${(pad.left + plotW).toFixed(1)}" y2="${(pad.top + plotH).toFixed(1)}"/>
  <line class="axis" x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${(pad.top + plotH).toFixed(1)}"/>
  <path class="area" d="${area}"/>
  <path class="line" d="${line}"/>
  <g class="xaxis" text-anchor="middle">${xTicks.join('\n    ')}</g>
  <circle class="dot" cx="${endX.toFixed(1)}" cy="${endY.toFixed(1)}" r="4"/>
  <text class="value" x="${labelX.toFixed(1)}" y="${(endY - 12).toFixed(1)}" text-anchor="${labelAnchor}">${
    escapeXml(`${stars} star${stars === 1 ? '' : 's'}`)
  }</text>
  <text class="axis-label" x="${(pad.left + plotW / 2).toFixed(1)}" y="${H - 14}" text-anchor="middle">Date</text>
  <text class="axis-label" transform="rotate(-90)" x="${-(pad.top + plotH / 2).toFixed(1)}" y="24" text-anchor="middle">GitHub Stars</text>
</svg>
`;
}

async function main() {
  await mkdir(outDir, { recursive: true });
  const svgPath = path.join(outDir, 'star-history.svg');
  const jsonPath = path.join(outDir, 'history.json');

  let weeks;
  if (cacheFile) {
    log(`离线模式：读取 ${cacheFile}`);
    weeks = JSON.parse(await readFile(cacheFile, 'utf8'));
  } else {
    log(`抓取 ${repository} 的 star 历史`);
    weeks = await fetchWeeklyHistory(repository, token);
  }

  const points = toPoints(weeks);
  if (points.length === 0) {
    throw new Error('没有解析出任何 star 数据点，保留旧图不覆盖');
  }

  const history = {
    repository,
    updated: new Date().toISOString().slice(0, 10),
    stars: points.at(-1).stars,
    points,
  };

  await writeFile(jsonPath, `${JSON.stringify(history, null, 2)}\n`, 'utf8');
  await writeFile(svgPath, renderSvg(repository, points), 'utf8');
  log(`已生成：${svgPath}（${points.length} 个数据点，共 ${history.stars} star）`);
}

main().catch(async (error) => {
  log(`失败：${error.message}`);
  try {
    await readFile(path.join(outDir, 'star-history.svg'), 'utf8');
    log('输出目录已有旧图，保留旧图并以 0 退出');
    process.exit(0);
  } catch {
    process.exit(1);
  }
});
