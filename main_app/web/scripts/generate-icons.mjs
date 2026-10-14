// Генерирует набор PNG-иконок PWA из public/favicon.svg.
// Запуск: npm run icons
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Resvg } from '@resvg/resvg-js'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const svgSource = readFileSync(join(root, 'public', 'favicon.svg'), 'utf8')
const outDir = join(root, 'public', 'icons')
mkdirSync(outDir, { recursive: true })

function render(svg, size) {
  const resvg = new Resvg(svg, { fitTo: { mode: 'width', value: size } })
  return resvg.render().asPng()
}

// Маска-безопасная версия: фон на всю площадь, логотип уменьшен до 78%.
function maskableSvg(size) {
  return svgSource
    .replace('rx="112"', 'rx="0"')
    .replace(
      '<g stroke="#ffffff"',
      '<g transform="translate(256 256) scale(0.78) translate(-256 -256)" stroke="#ffffff"',
    )
}

const targets = [
  ['icon-192.png', 192, svgSource],
  ['icon-512.png', 512, svgSource],
  ['apple-touch-icon.png', 180, maskableSvg(180)],
  ['maskable-192.png', 192, maskableSvg(192)],
  ['maskable-512.png', 512, maskableSvg(512)],
]

for (const [name, size, svg] of targets) {
  writeFileSync(join(outDir, name), render(svg, size))
  console.log('generated', name, `(${size}x${size})`)
}
