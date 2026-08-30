// Headless D3 renderer. Reads {code, data, width, height} as JSON on stdin,
// executes the model's D3 in Chromium, and writes a base64 PNG of the <svg> to
// stdout. The one JavaScript step in the Python harness, because D3 is JS.
// Requires: npx playwright install chromium.
import { chromium } from 'playwright'

const input = JSON.parse(await new Promise((res) => {
  let s = ''
  process.stdin.on('data', (d) => (s += d))
  process.stdin.on('end', () => res(s))
}))

const { code, data, width = 720, height = 460 } = input
const html = `<!doctype html><meta charset="utf8"><body style="margin:0;background:#fff">
<div id="c"></div><script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script>
  const data = ${JSON.stringify(data)};
  try {
    const render = new Function('svg','data','d3','dims', ${JSON.stringify(code)});
    render(document.getElementById('c'), data, d3, { width: ${width}, height: ${height} });
  } catch (e) { document.body.innerHTML = '<pre>'+e.message+'</pre>'; }
</script></body>`

const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width, height } })
  await page.setContent(html, { waitUntil: 'networkidle' })
  const svg = await page.$('#c svg')
  const buf = svg ? await svg.screenshot({ type: 'png' }) : await page.screenshot({ type: 'png' })
  process.stdout.write(buf.toString('base64'))
} finally {
  await browser.close()
}
