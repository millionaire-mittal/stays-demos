"""Screenshot built demos at desktop and phone width, and run quick sanity checks.

Usage:
    python check.py                      # every built demo
    python check.py example-homestay     # one or more slugs

Writes shots/<slug>-desktop.png (1400px) and shots/<slug>-mobile.png (390px),
and reports console errors, horizontal overflow on mobile, and whether the
enquiry form builds the right WhatsApp message.

Needs Playwright:  pip install playwright && python -m playwright install chromium
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
SHOTS = HERE / "shots"

SCROLL_THROUGH = """async () => {
  const step = Math.round(innerHeight * 0.6);
  for (let y = 0; y < document.body.scrollHeight; y += step) {
    scrollTo(0, y); await new Promise(r => setTimeout(r, 120));
  }
  document.querySelectorAll('.reveal').forEach(e => e.classList.add('in'));
  const map = document.querySelector('.map iframe');
  if (map) { map.scrollIntoView(); await new Promise(r => setTimeout(r, 3000)); }
  scrollTo(0, 0); await new Promise(r => setTimeout(r, 400));
}"""

FORM_TEST = """() => {
  let opened = null;
  window.open = (u) => { opened = u; return {}; };
  const d = (n) => { const t = new Date(); t.setDate(t.getDate() + n);
    return t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0'); };
  const set = (id, v) => { const el = document.getElementById(id); el.value = v; el.dispatchEvent(new Event('change')); };
  const submit = () => document.getElementById('form').dispatchEvent(new Event('submit', {cancelable: true}));
  // 1) check-out before check-in must be rejected
  set('fin', d(10)); document.getElementById('fout').value = d(8);
  document.getElementById('fname').value = 'Asha';
  submit();
  const rejected = opened === null && document.getElementById('ferr').textContent;
  // 2) valid enquiry
  document.getElementById('fout').value = d(13);
  document.getElementById('fguests').value = '3';
  submit();
  return {rejected, url: opened && decodeURIComponent(opened)};
}"""


def check(slug: str, browser) -> bool:
    page_path = HERE / "demos" / slug / "index.html"
    if not page_path.is_file():
        print(f"{slug}: not built yet (run python build.py {slug})")
        return False
    ok = True
    SHOTS.mkdir(exist_ok=True)
    for label, width, height, mobile in (("desktop", 1400, 900, False), ("mobile", 390, 844, True)):
        ctx = browser.new_context(viewport={"width": width, "height": height},
                                  device_scale_factor=1 if not mobile else 2,
                                  is_mobile=mobile, has_touch=mobile)
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(page_path.as_uri(), wait_until="load")
        page.evaluate(SCROLL_THROUGH)
        page.wait_for_timeout(600)
        overflow = page.evaluate("document.documentElement.scrollWidth - innerWidth")
        out = SHOTS / f"{slug}-{label}.png"
        page.screenshot(path=str(out), full_page=True)
        # Google Maps iframe errors are outside our control; ignore them.
        errors = [e for e in errors if "google" not in e.lower()]
        print(f"{slug} {label}: {out.relative_to(HERE).as_posix()}")
        if errors:
            ok = False
            print("  console errors:", *errors, sep="\n    ")
        if overflow > 0:
            ok = False
            print(f"  page is {overflow}px wider than the screen (horizontal scroll)")
        if not mobile:
            res = page.evaluate(FORM_TEST)
            if not res["rejected"]:
                ok = False
                print("  form accepted check-out before check-in")
            if not res["url"] or "I'd like to stay at" not in res["url"]:
                ok = False
                print("  form did not open WhatsApp:", res["url"])
            else:
                print("  whatsapp:", res["url"])
        ctx.close()
    return ok


def main(argv):
    slugs = argv[1:] or sorted(p.parent.name for p in (HERE / "demos").glob("*/index.html"))
    if not slugs:
        sys.exit("Nothing built yet. Run python build.py first.")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        results = [check(s, browser) for s in slugs]
        browser.close()
    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
