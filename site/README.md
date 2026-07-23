# GeoTask mobile experience page

This directory contains the static mobile page used by the `GeoTask 每周一例` series.
It has no backend, analytics, cookies, account system, model key, or external JavaScript dependency.

## Current case

- Case: `GT01`
- Task: distance between `(0, 0)` and `(3, 4)`
- Expected result: `ab_distance = 5.0 meter`
- Public repository: <https://github.com/stpku/GeoTask>

## GitHub Pages deployment

The workflow `.github/workflows/pages.yml` publishes this directory after a push to `main`.
After the first workflow run, open repository **Settings > Pages** and confirm that the source is
**GitHub Actions**. The expected project-page address is:

```text
https://stpku.github.io/GeoTask/
```

The site uses only relative assets, so the project subpath does not require a base-path rewrite.

## Huawei Cloud deployment

The same directory can be uploaded unchanged to either:

1. an OBS bucket configured for static website hosting and a custom HTTPS domain; or
2. an existing Nginx static directory behind a custom HTTPS domain.

For Nginx, copy `site/index.html` to a directory such as `/var/www/geotask-experience/` and use a
minimal location block:

```nginx
location /geotask/ {
    alias /var/www/geotask-experience/;
    try_files $uri $uri/ /geotask/index.html;
    add_header Cache-Control "public, max-age=300";
}
```

Clipboard access is most reliable on HTTPS. Do not put model API keys or other secrets into this
static directory.

## Publishing recommendation

- Use GitHub Pages first for immediate validation and as a permanent backup.
- Use a Huawei Cloud custom HTTPS domain as the primary WeChat entry after the domain and filing
  requirements are ready.
- Point the WeChat keyword reply `GT01` and the article's `阅读原文` to the primary experience URL.
