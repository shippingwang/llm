/* 顶栏栏目；部分色条在 head 里一次性上色。Instant 换页时若 nav 被换掉再补一次。 */

const SITE_LINKS = [
  ["research", "https://shippingwang.com/research/"],
  ["book", "https://shippingwang.com/book/"],
  ["life", "https://shippingwang.com/life/"],
  ["idea", "https://shippingwang.com/idea/"],
];

const BOOK_RE = /\/(01-architecture|02-systems|03-post-training)(?:\/|$)/;
const SECTION = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5 };

function syncBookAttr() {
  const m = location.pathname.match(BOOK_RE);
  if (m) document.documentElement.setAttribute("data-book", m[1]);
  else document.documentElement.removeAttribute("data-book");
}

function injectSiteLinks() {
  const inner = document.querySelector(".md-header__inner");
  if (!inner || inner.querySelector(".sw-header__links")) return;

  const box = document.createElement("div");
  box.className = "sw-header__links";
  for (const [label, href] of SITE_LINKS) {
    const a = document.createElement("a");
    a.href = href;
    a.textContent = label;
    if (label === "book") a.classList.add("is-active");
    box.appendChild(a);
  }
  const title = inner.querySelector(".md-header__title");
  if (title) inner.insertBefore(box, title);
  else inner.appendChild(box);
}

function decorateIfNeeded() {
  const nav = document.querySelector(".md-nav--primary");
  if (!nav || nav.getAttribute("data-sw-decorated") === "1") return;
  nav.querySelectorAll(".md-nav__item").forEach((item) => {
    const label = item.querySelector(":scope > .md-nav__link .md-ellipsis");
    if (!label) return;
    const title = label.textContent.trim();
    const m = title.match(/^第([一二三四五])部分/);
    if (m) {
      item.classList.add("book-section-start", `book-section-${SECTION[m[1]]}`);
    } else if (/^附录 A\b/.test(title)) {
      item.classList.add("book-section-start", "book-section-appendix");
    }
  });
  nav.setAttribute("data-sw-decorated", "1");
}

function enhance() {
  syncBookAttr();
  injectSiteLinks();
  decorateIfNeeded();
}

if (typeof window.document$ !== "undefined" && window.document$.subscribe) {
  window.document$.subscribe(() => {
    // Instant navigation 会换掉 nav 节点，清标记后补色
    const nav = document.querySelector(".md-nav--primary");
    if (nav && !nav.isConnected) {
      /* no-op */
    }
    // 若 Material 换了新 nav，旧标记不在新节点上
    enhance();
  });
} else {
  document.addEventListener("DOMContentLoaded", enhance);
}
