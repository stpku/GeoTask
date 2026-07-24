# GeoTask mobile experience page

This directory contains the static mobile page used by the `GeoTask 每周一例` series.
It has no backend, analytics, cookies, account system, model key, or external JavaScript dependency.

## Current cases

- `GT01`: distance between `(0, 0)` and `(3, 4)`; expected result `ab_distance = 5.0 meter`
- `GT02`: distance between `(0, 0)` and `(120, 80)`; compare a model result with the browser-local deterministic result `144.22 meter`
- `GT03`: four-point route where only the final segment intersects a rectangular restricted zone; expected result `route_intersects_zone = true`
- `GT04`: identical 2D footprints with vertically separated altitude ranges `[100, 150]` and `[300, 500]`; expected result `altitude_conflict = false`
- `GT05`: identical position and altitude but separated time windows `08:00–09:00` and `15:00–17:00`; expected result `temporal_conflict = false`
- `GT06`: route intersection and altitude overlap are true, time overlap is false; explicit `AND` rule produces `full_conflict = false`
- `GT07`: route and altitude checks are true, but the required schedule condition is unverifiable; three-valued `AND` propagates `unknown`
- `GT08`: an unverifiable schedule condition triggers a structured evidence request, blocks unsafe outputs, and defines a resume condition
- `GT09`: two verified temporary no-fly notices for the same UAV mission produce incompatible temporal results; a conflict review task blocks unsafe source selection
- Public repository: <https://github.com/stpku/GeoTask>

Primary experience URLs:

- <https://skyswind.tailf4fad8.ts.net/geotask/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt02/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt03/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt04/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt05/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt06/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt07/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt08/>
- <https://skyswind.tailf4fad8.ts.net/geotask/gt09/>

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

For Nginx, deploy the complete `site/` tree. Copying only the root `index.html` leaves nested cases
such as `gt02/index.html` unavailable:

```bash
sudo rsync -a --delete site/ /var/www/geotask-experience/
test -f /var/www/geotask-experience/index.html
test -f /var/www/geotask-experience/gt02/index.html
test -f /var/www/geotask-experience/gt03/index.html
test -f /var/www/geotask-experience/gt04/index.html
test -f /var/www/geotask-experience/gt05/index.html
test -f /var/www/geotask-experience/gt06/index.html
test -f /var/www/geotask-experience/gt07/index.html
test -f /var/www/geotask-experience/gt08/index.html
test -f /var/www/geotask-experience/gt09/index.html
```

The repository also includes `site/deploy-nginx.sh`, which performs the recursive sync, checks
GT01 through GT09, validates Nginx, and reloads the service.

Use a static location that serves directory index files and does not rewrite every missing nested
path back to GT01:

```nginx
location = /geotask {
    return 301 /geotask/;
}

location /geotask/ {
    alias /var/www/geotask-experience/;
    index index.html;
    autoindex off;
    add_header Cache-Control "no-cache";
}
```

After deployment:

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -I https://skyswind.tailf4fad8.ts.net/geotask/gt09/
```

Each nested response must come from its matching directory index. Do not configure a fallback to
`/geotask/index.html`, because that masks missing nested files by showing GT01.

Clipboard access is most reliable on HTTPS. Do not put model API keys or other secrets into this
static directory.

## Publishing recommendation

- Use GitHub Pages first for immediate validation and as a permanent backup.
- Use a Huawei Cloud custom HTTPS domain as the primary WeChat entry after the domain and filing
  requirements are ready.
- Point the WeChat keyword reply `GT01` and the article's `阅读原文` to the primary experience URL.
