(() => {
  "use strict";

  const script = document.currentScript;
  if (!script || document.querySelector("[data-geotask-case-navigation]")) {
    return;
  }

  const siteRoot = new URL("../", script.src);
  const catalogUrl = new URL("cases.json", siteRoot);
  const slugMatch = window.location.pathname.match(/\/(gt\d{2})(?:\/|\/index\.html)?$/i);
  if (!slugMatch) {
    return;
  }
  const currentSlug = slugMatch[1].toLowerCase();

  function createLink({ href, text, className, title }) {
    const link = document.createElement("a");
    link.className = `gt-case-navigation__link ${className}`;
    link.href = href;
    link.textContent = text;
    if (title) {
      link.title = title;
    }
    return link;
  }

  function createDisabled(text) {
    const item = document.createElement("span");
    item.className = "gt-case-navigation__disabled";
    item.textContent = text;
    item.setAttribute("aria-disabled", "true");
    return item;
  }

  function titleFor(entries, slug) {
    const item = entries.find(entry => entry.slug === slug);
    return item ? item.title_zh : "";
  }

  function renderNavigation(payload) {
    if (!payload || !Array.isArray(payload.cases)) {
      return;
    }
    const current = payload.cases.find(entry => entry.slug === currentSlug);
    if (!current || document.querySelector("[data-geotask-case-navigation]")) {
      return;
    }

    const navigation = document.createElement("nav");
    navigation.className = "gt-case-navigation";
    navigation.dataset.geotaskCaseNavigation = "ready";
    navigation.setAttribute("aria-label", "案例序列导航");

    navigation.append(
      current.previous
        ? createLink({
            href: new URL(`${current.previous}/`, siteRoot).href,
            text: `← ${current.previous.toUpperCase()} 上一例`,
            className: "gt-case-navigation__link--previous",
            title: titleFor(payload.cases, current.previous),
          })
        : createDisabled("已经是第一例")
    );

    navigation.append(
      createLink({
        href: new URL("#cases", siteRoot).href,
        text: `全部 ${payload.case_count} 个参考例`,
        className: "gt-case-navigation__link--index",
        title: "返回GeoTask公开参考例目录",
      })
    );

    navigation.append(
      current.next
        ? createLink({
            href: new URL(`${current.next}/`, siteRoot).href,
            text: `${current.next.toUpperCase()} 下一例 →`,
            className: "gt-case-navigation__link--next",
            title: titleFor(payload.cases, current.next),
          })
        : createDisabled("已经是最新案例")
    );

    const footer = document.querySelector("footer");
    if (footer && footer.parentNode) {
      footer.parentNode.insertBefore(navigation, footer);
    } else {
      document.body.appendChild(navigation);
    }
  }

  fetch(catalogUrl, { credentials: "same-origin" })
    .then(response => {
      if (!response.ok) {
        throw new Error(`case catalog request failed: ${response.status}`);
      }
      return response.json();
    })
    .then(renderNavigation)
    .catch(() => {
      document.documentElement.dataset.caseNavigation = "unavailable";
    });
})();
