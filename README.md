# stays-demos

Private demo websites for independent places to stay: villas, homestays,
guesthouses, boutique hotels and cottages that have strong Google reviews but
no website of their own. Each demo is shown privately to the owner to sell them
a website.

One template, one entry per property, one self-contained page each:

```
leads.json  ->  python build.py <slug>  ->  demos/<slug>/index.html  ->  Vercel, served at /<slug>/
```

The page reads like a small travel magazine: a full-screen photo, big serif
type, an editorial gallery, guest reviews as pull quotes, a map, and an
enquiry form that opens WhatsApp. It shows no prices, takes no payments, uses
no urgency tricks and has no booking-platform logos.

## Repo layout

| Path | What it is |
| --- | --- |
| `leads.json` | One object per property (the only file you edit for a new demo) |
| `template.html` | The page template (HTML, CSS and JS in one file) |
| `build.py` | Validates a lead and renders `demos/<slug>/index.html` |
| `check.py` | Screenshots a demo at 1400px and 390px and runs sanity checks |
| `demos/<slug>/img/` | That property's photos |
| `vercel.json` | Serves `demos/` with clean URLs and a `noindex` header |

## Lead format

Each entry in `leads.json`:

| Field | Example | Notes |
| --- | --- | --- |
| `slug` | `"mistwood-coorg"` | Folder and URL name. Lowercase, digits, dashes |
| `name` | `"Mistwood Homestay"` | Property name as on Google |
| `type` | `"Hill homestay"` | Shown in the hero and footer |
| `town`, `region`, `country` | `"Madikeri"`, `"Coorg, Karnataka"`, `"India"` | |
| `phone` | `"+91 98450 00000"` | Displayed as written; used for the Call button |
| `whatsapp` | `"919845000000"` | Digits only, with country code |
| `rating` | `4.9` | From their Google listing |
| `review_count` | `214` | From their Google listing |
| `maps_link` | `"https://maps.app.goo.gl/..."` | Their Google Maps link. See Map below |
| `checkin`, `checkout` | `"12:00 pm"`, `"11:00 am"` | Shown in the footer |
| `headline` | one sentence | Under the name in the hero |
| `subline` | 2 to 3 sentences | The large intro paragraph |
| `highlights` | 3 strings | Exactly 3 short points, shown as 01 / 02 / 03 |
| `amenities` | list of strings | Each gets a line icon matched by keyword (Wi-Fi, pool, parking, breakfast, AC, bonfire, garden, view, beach, pets, hot water, pickup, scooter and so on). Unmatched ones get a tick |
| `rooms` | optional list of `{name, sleeps, note}` | Leave out (or `[]`) to hide the Rooms section. `sleeps` can be a number (`2` shows "Sleeps 2") or text |
| `reviews` | 3 x `{text, name}` | Real Google reviews, word for word. Only the first name is shown |
| `nearby` | list of strings | "Around you", e.g. `"Abbey Falls, 9 km"` |
| `accent` | `"#2f5d46"` | One hex colour; the whole palette is generated from it |
| `mood` | `"dark"` or `"light"` | `dark` = deep, moody page (forest, heritage). `light` = warm off-white page (beach, garden) |
| `photos` | `6` | How many gallery images (`g1.jpg` to `g6.jpg`) |
| `map_query` | optional | Overrides what the map shows, e.g. `"Mistwood Homestay, Madikeri"` |
| `hosts` | optional `{heading, text, points, alt?}` | "Meet your hosts" section after the highlights. `points` is 1 to 4 short strings. Needs `img/hosts.jpg` |
| `day` | optional `{heading, moments}` | "A day here" timeline. `moments` is 2 to 6 x `{time, text}`, e.g. `{"time": "Morning", "text": "..."}` |
| `local` | optional `{note, heading?, cta?, wa_text?}` | "Local recommendations" section before the map, listing `nearby` with distances and a WhatsApp button. When present, the map section's "Around you" list is hidden so places aren't listed twice |

| `help` | optional `{heading, points}` | "Host-guided help" cards just before Local recommendations. 1 to 6 short strings; icons are matched by keyword (walk, directions, food, transport...) |
| `good_to_know` | optional `{points, heading?}` | "Good to know" list just before the booking section. 1 to 10 short strings. Only list things the owner has confirmed |
| `booking` | optional `{heading, subtext, cta, wa_text, room_wa_text?}` | Turns the page WhatsApp-first: replaces the booking intro with the heading, subtext, a WhatsApp button (`cta`), Call and Get Directions buttons, and check-in/out times. It also adds a WhatsApp button in the hero, an "Ask about this room" link on each room, and a floating WhatsApp button on desktop (the mobile bar already covers phones). Every one of them pre-fills `wa_text`; `room_wa_text` can use `{room}` and `{name}` |
| `review_source` | optional, e.g. `"Airbnb"` | Where the rating and reviews come from. Defaults to `"Google"` |
| `reviews_link` | optional URL | Where the rating badge links. Defaults to `maps_link` |
| `photo_labels` | optional list | One label per gallery photo (e.g. `"Exterior"`), used as alt text and shown in the lightbox |

A review can carry `"placeholder": true`. Its caption then reads "Review
placeholder" instead of "Google review". Replace every placeholder with a real
review before the demo is shown.

Leave out any of `hosts`, `day`, `local`, `help`, `good_to_know` or `booking`
and that section (or behaviour) doesn't appear. In any
`heading`, wrap words in `*asterisks*` to set them in the accent italic, e.g.
`"Life at *Green Haven*"`. For `local`, write `nearby` entries as
`"Tea Museum — 3 km"` (or `"Tea Museum, 3 km"`) so the distance lines up on
the right. `wa_text` is the message the WhatsApp button pre-fills.

### Images

Put them in `demos/<slug>/img/`:

- `hero.jpg`: required. Landscape, about 2000px wide, under about 400 KB. It
  fills the screen, so pick the most atmospheric shot.
- `g1.jpg` ... `gN.jpg`: required, where N is `photos`. A mix of landscape
  and portrait works best. The grid lays out any count without gaps.
- `hosts.jpg`: required only when the lead has `hosts`. A warm photo of the
  family; it shows as a 4:5 portrait on desktop and a square on phones.
- `room1.jpg` ... : optional, one per room in order. A room without its own
  photo borrows a gallery photo.

Keep each gallery image around 1400px on the long side. Everything except the
hero is lazy-loaded.

### Map

The map embed is built from `maps_link` without an API key. It uses the
`q=` / `query=` parameter, the place name in a `/place/...` link, or the
`@lat,lng` in the link. Short `maps.app.goo.gl` links can't be read offline,
so the map falls back to "name, town, region, country". If the pin lands in
the wrong place, set `map_query`.

### Colour

`accent` and `mood` generate the background, surface, text, muted text,
lines, accent and button-text colours. The accent is lightened or darkened
until it is readable on the background, so choose the hue you want rather
than a perfect shade. Muted, natural colours look best: forest green,
terracotta, sand, slate blue, deep teal.

## Add a new property

1. **Qualify it on Google Maps:** strong rating (4.6+), a decent number of
   reviews, a phone number, and no Website button. A Facebook or Instagram
   page counts as no website.
2. **Copy an example entry** in `leads.json` and fill it in from their listing.
   Copy reviews word for word. Write `headline`, `subline` and `highlights`
   from what the listing and reviews actually say.
3. **Add photos** to `demos/<slug>/img/`, taken from the photos on their Google
   listing.
4. **Build:**
   ```
   python build.py <slug>        # one demo
   python build.py               # all demos
   ```
   On macOS or Linux use `python3`. If a field or image is missing, the build
   stops and lists exactly what to fix.
5. **Check it** (see below), then commit and push.

## Check

Preview locally:

```
python -m http.server 8000 -d demos
```

Then open `http://localhost:8000/<slug>/`. Opening `demos/<slug>/index.html`
directly in a browser also works.

Automated check:

```
pip install playwright && python -m playwright install chromium   # once
python check.py <slug>
```

This writes `shots/<slug>-desktop.png` (1400px) and `shots/<slug>-mobile.png`
(390px). It also reports console errors and horizontal scrolling on mobile,
and checks that the enquiry form rejects a check-out before check-in and builds
the right WhatsApp message. Look at both screenshots before you send anything.
`shots/` is git-ignored.

## Deploy

The repo deploys to Vercel as a static site. No build step runs on Vercel;
it serves the committed `demos/` folder.

1. In Vercel, import `millionaire-mittal/stays-demos`. `vercel.json` already
   sets `outputDirectory: "demos"`, clean URLs and a `noindex` header.
2. Every push to `main` redeploys. A demo is live at
   `https://<your-domain>/<slug>/`.
3. Set `BASE_URL` at the top of `build.py` to the real domain, so WhatsApp and
   iMessage link previews show the hero photo. Then rebuild.

## Rules that protect the pitch

- **Real data only.** Rating, review count and reviews come from their own
  Google listing. Never write or edit a review.
- **Demos are private.** Every page has `noindex` and a "Demo site" note in the
  footer. Send the link only to the owner.
- **If they say no, delete their folder and entry** and push. It's their name,
  number, photos and reviews.
- **Paying clients move to their own repo and domain**, not a shared demo link.
