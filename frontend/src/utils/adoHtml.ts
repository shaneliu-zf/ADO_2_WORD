/** 預覽／導出用：連結新分頁、補字型；導出時可把相對路徑轉成絕對網址。 */
export function prepareAdoHtml(html: string, options?: { absolutizeOrigin?: string }): string {
  if (!html) return html
  const origin = (options?.absolutizeOrigin || '').replace(/\/$/, '')
  if (typeof DOMParser === 'undefined') {
    return html.replace(/<a\b(?![^>]*\btarget=)/gi, '<a target="_blank" rel="noopener noreferrer" ')
  }
  const doc = new DOMParser().parseFromString(html, 'text/html')
  for (const anchor of doc.querySelectorAll('a[href]')) {
    const href = (anchor.getAttribute('href') || '').trim()
    const lower = href.toLowerCase()
    if (lower.startsWith('javascript:') || lower.startsWith('data:')) {
      anchor.removeAttribute('href')
      continue
    }
    if (origin && href.startsWith('/')) {
      anchor.setAttribute('href', `${origin}${href}`)
    }
    anchor.setAttribute('target', '_blank')
    anchor.setAttribute('rel', 'noopener noreferrer')
  }
  if (origin) {
    for (const img of doc.querySelectorAll('img[src]')) {
      const src = (img.getAttribute('src') || '').trim()
      if (src.startsWith('/')) img.setAttribute('src', `${origin}${src}`)
    }
  }
  if (!doc.querySelector('base')) {
    const base = doc.createElement('base')
    base.setAttribute('target', '_blank')
    ;(doc.head ?? doc.documentElement).prepend(base)
  }
  // 舊預覽若沒有 .page，導出時包一層並補版面樣式
  if (!doc.querySelector('main.page') && doc.body) {
    const page = doc.createElement('main')
    page.className = 'page'
    while (doc.body.firstChild) page.appendChild(doc.body.firstChild)
    doc.body.appendChild(page)
  }
  if (!doc.getElementById('ado-page-layout')) {
    const style = doc.createElement('style')
    style.id = 'ado-page-layout'
    style.textContent = [
      'html,body{margin:0;min-height:100%;background:#eef1f5;color:#1f2937;',
      'font-family:"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.55}',
      '.page{max-width:880px;margin:0 auto;padding:1.75rem 1.5rem 2.5rem;background:#fff;',
      'min-height:100vh;box-shadow:0 0 0 1px rgba(15,23,42,.04),0 12px 40px rgba(15,23,42,.06)}',
      '@media(min-width:920px){body{padding:1.5rem 1rem 2rem;background:#e8ecf1}',
      '.page{min-height:auto;border-radius:12px;padding:2rem 2.25rem 2.75rem}}',
      'img{max-width:100%;height:auto}',
    ].join('')
    ;(doc.head ?? doc.documentElement).append(style)
  }
  return '<!DOCTYPE html>\n' + doc.documentElement.outerHTML
}

export function downloadHtmlFile(filename: string, html: string): void {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
