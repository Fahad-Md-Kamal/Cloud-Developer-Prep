---
title: "CMS Platforms"
---

# CMS Platforms

**Status: placeholder.** Flagged from the Svea Solar Senior Fullstack
Engineer (Django) JD gap analysis (2026-09-23) — bonus point for
"experience with a CMS platform." No existing coverage anywhere on
this site. Not yet given the full Q&A deep-dive treatment this site's
other chapters have.

**Topics to cover when this gets deep-dived:**

- Headless vs. traditional/coupled CMS — architecture difference and
  when each fits.
- Django-native option: Wagtail — page-tree model, StreamField, admin
  editing experience.
- Headless options: Contentful, Strapi, Sanity — API-driven content
  delivery, decoupled from the rendering frontend.
- When a CMS is the right call vs. a custom admin/DB-backed content
  model — the actual decision criteria, not just "CMS is easier."
- Content modeling and editorial workflows: drafts, preview/staging,
  approval flows non-technical editors need.
- Integration pattern: CMS as content source feeding a separate
  frontend (JAMstack-style) vs. server-rendered pages pulling from it
  directly.
- Performance/caching considerations for CMS-backed pages.
- Interview framing: "how would you let a non-technical marketing team
  edit landing pages without needing a deploy."
