// Shared navbar + footer HTML injection for public SI-ISPO pages
(function(){
  const NAV_ITEMS = [
    { id:'beranda',      label:'Beranda',      href:'/' },
    { id:'berita',       label:'Berita',       href:'/berita.html' },
    { id:'regulasi',     label:'Regulasi',     href:'/regulasi.html' },
    { id:'faq',          label:'FAQ',          href:'/faq.html' },
    { id:'peta-sebaran', label:'Peta Sebaran', href:'/peta-sebaran.html' },
  ];

  window.renderPublicNav = function(activeId){
    const links = NAV_ITEMS.map(n =>
      `<a class="nav-link ${n.id===activeId?'active':''}" href="${n.href}" data-testid="nav-${n.id}">${n.label}</a>`
    ).join('');
    return `
      <nav class="nav">
        <div class="wrap nav-inner">
          <a class="brand" href="/" data-testid="brand-home">
            <div class="brand-mark">SI</div>
            <div class="brand-txt"><b>SI-ISPO</b><small>Sistem Informasi ISPO</small></div>
          </a>
          <div class="nav-links">${links}</div>
          <button class="lang-sel" data-testid="lang-sel">🌐 ID <span style="color:var(--t3)">▾</span></button>
          <a class="btn btn-out" href="/si-ispo.html" data-testid="nav-login">Login</a>
          <a class="btn btn-p" href="/si-ispo.html" data-testid="nav-registrasi">Registrasi</a>
        </div>
      </nav>`;
  };

  window.renderPublicFooter = function(){
    return `
      <footer>
        <div class="wrap foot-inner">
          <div class="foot-copy">© 2025 SI-ISPO — Sistem Informasi ISPO</div>
          <div class="foot-links">
            <a href="/si-ispo.html">Tentang Kami</a>
            <a href="/si-ispo.html">Kebijakan Privasi</a>
            <a href="/si-ispo.html">Syarat &amp; Ketentuan</a>
            <a href="/si-ispo.html">Kontak</a>
          </div>
          <div class="foot-social">
            <a href="#" aria-label="Facebook"><svg fill="currentColor" viewBox="0 0 24 24"><path d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987H7.898V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.891h-2.33v6.988C18.343 21.128 22 16.991 22 12z"/></svg></a>
            <a href="#" aria-label="Twitter"><svg fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
            <a href="#" aria-label="Instagram"><svg fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg></a>
          </div>
        </div>
      </footer>`;
  };

  window.mountPublicShell = function(activeId){
    const navSlot = document.getElementById('nav-slot');
    const footSlot = document.getElementById('footer-slot');
    if (navSlot) navSlot.outerHTML = window.renderPublicNav(activeId);
    if (footSlot) footSlot.outerHTML = window.renderPublicFooter();
  };
})();
