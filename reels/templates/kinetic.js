// Shared GSAP motion for every reel (seekable, frame-exact): letters of a title rise out of a mask,
// and the closing card animates piece by piece. Templates call K.title(el, start) / K.outro(localTime).
(function () {
  const K = { ok: false, tl: [] };
  // a mask clips the letters as they rise; give it room so descenders (p, g, y) and accents are never cut
  K.roomy = (sp) => (sp.masks || []).forEach((m) => { m.style.padding = '.12em .04em .26em'; m.style.margin = '-.12em -.04em -.26em'; });
  K.init = function () {
    if (K.ok || !window.gsap || !window.SplitText) return; gsap.registerPlugin(SplitText); K.ok = true;
    const o = document.getElementById('outro'); if (!o) return;
    const logo = document.getElementById('outroLogo'), save = document.getElementById('saveChip');
    [logo, save].forEach((e) => { if (e) { e.style.transform = ''; e.style.opacity = ''; } });
    const h2 = o.querySelector('h2'); const sp = h2 ? SplitText.create(h2, { type: 'words,chars' }) : null;
    const tl = gsap.timeline({ paused: true });
    if (logo) tl.from(logo, { scale: 0, rotate: -25, duration: 0.7, ease: 'back.out(2.2)' }, 0.05);
    if (sp) tl.from(sp.chars, { y: 40, opacity: 0, duration: 0.5, ease: 'power3.out', stagger: 0.018 }, 0.25);
    if (o.querySelector('p')) tl.from(o.querySelector('p'), { y: 18, opacity: 0, duration: 0.45, ease: 'power2.out' }, 0.55);
    if (save) tl.from(save, { scale: 0, duration: 0.55, ease: 'back.out(2.6)' }, 0.7);
    if (o.querySelector('.follow')) tl.from(o.querySelector('.follow'), { opacity: 0, y: 14, duration: 0.4 }, 0.85);
    if (o.querySelector('.signature')) tl.from(o.querySelector('.signature'), { letterSpacing: '22px', opacity: 0, duration: 0.8, ease: 'power3.out' }, 0.9);
    K.out = tl;
  };
  K.title = function (el, start) {
    if (!K.ok || !el || el.dataset.k) return; el.dataset.k = '1';
    const sp = SplitText.create(el, { type: 'chars,words', mask: 'chars' }); K.roomy(sp);
    const tl = gsap.timeline({ paused: true }).from(sp.chars, { yPercent: 115, rotate: 7, duration: 0.75, ease: 'expo.out', stagger: 0.028 });
    K.tl.push({ tl, start });
  };
  K.seek = function (t) { K.tl.forEach((x) => x.tl.seek(Math.max(0, Math.min(x.tl.duration(), t - x.start)))); };
  K.outro = function (lt) { if (K.out) K.out.seek(Math.max(0, Math.min(K.out.duration(), lt))); };
  window.K = K;
}());
