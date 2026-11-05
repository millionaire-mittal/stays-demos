# stays-demos

Private demo websites for independent places to stay (villas, homestays,
guesthouses, boutique hotels, cottages) that have strong Google reviews but no
website of their own. Each demo is shown privately to the owner to sell them a
website.

Flow: `leads.json` -> `python build.py <slug>` -> `demos/<slug>/index.html`,
deployed on Vercel with each demo served at `/<slug>/`.

The full guide (lead format, building, checking, deploying) arrives with the
template on the `template-v1` branch.
