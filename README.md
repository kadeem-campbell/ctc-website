# Caribbean Tech Collective Website

Production website for Caribbean Tech Collective (CTC).

This repository contains the Netlify-ready build of the site.

---

## Overview

The site is delivered as a static build for performance, reliability and operational simplicity.

It includes:

- Structured data (JSON-LD)
- Custom SEO configuration
- Sitemap and robots configuration
- Security headers via _headers
- Redirect management via _redirects
- Service worker support
- LLM discovery file (llms.txt)

The goal was to keep the surface area small while maintaining full control over performance and indexing.

---

## Stack

HTML  
Modular CSS  
Vanilla JavaScript  
Netlify configuration  

---

## Deployment

Git-based deployment via Netlify.

Changes are version controlled and deployed through the main branch.

---

## Security

This is a static deployment with no stored user data.

There are:
- No secrets committed
- No environment variables
- No backend processing layer

Security headers are defined in _headers.

If you identify a vulnerability, please contact: hello@caribbeantechcollective.com

---

## Notes

Media assets are intentionally separated from core application logic to keep the repository clean and maintainable.

