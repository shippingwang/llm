const BOOK_DIRS = ["01-architecture", "02-systems", "03-post-training"];

const BOOK_TITLES = {
  "01-architecture": "第一册 · 现代大模型架构",
  "02-systems": "第二册 · 训练与推理系统",
  "03-post-training": "第三册 · 后训练与智能体系统",
};

function currentBookDir() {
  const path = window.location.pathname;
  return BOOK_DIRS.find((dir) => path.includes(`/${dir}/`) || path.endsWith(`/${dir}`));
}

function linkTargetsBook(href, dir) {
  if (!href) return false;
  return href.includes(`/${dir}/`) || href.endsWith(`/${dir}`) || href.endsWith(`/${dir}/`);
}

/** 进入某一册后，侧栏只保留该册 + 回书架入口 */
function scopePrimaryNav() {
  const dir = currentBookDir();
  if (!dir) return;

  const rootList = document.querySelector(".md-nav--primary > .md-nav__list");
  if (!rootList) return;

  rootList.querySelectorAll(":scope > .md-nav__item").forEach((item) => {
    const anchors = item.querySelectorAll("a.md-nav__link");
    let href = "";
    anchors.forEach((a) => {
      if (!href) href = a.getAttribute("href") || "";
    });

    const isShelf =
      href === ".." ||
      href === "../" ||
      href === "./.." ||
      /\/book\/llm\/?$/.test(href) ||
      /\/llm\/?$/.test(href);

    const isThisBook = linkTargetsBook(href, dir) || item.querySelector(`a[href*="/${dir}/"], a[href$="/${dir}/"], a[href$="/${dir}"]`);

    if (isThisBook) {
      item.classList.add("book-nav-current");
      // 把英文目录名换成中文册名
      const title = BOOK_TITLES[dir];
      item.querySelectorAll(":scope > .md-nav__link .md-ellipsis, :scope > .md-nav__container .md-ellipsis").forEach((el) => {
        if (title && /^(01|02|03)\b/.test(el.textContent.trim())) {
          el.textContent = title;
        }
      });
      return;
    }

    if (isShelf) {
      item.classList.add("book-nav-shelf");
      const ellipsis = item.querySelector(".md-ellipsis");
      if (ellipsis) ellipsis.textContent = "← 书架";
      return;
    }

    item.classList.add("book-nav-hidden");
  });
}

function decorateNavigation() {
  const sectionPattern = /^第([一二三四五])部分/;
  const sectionNumber = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5 };

  document.querySelectorAll(".md-nav--primary .md-nav__item").forEach((item) => {
    const label = item.querySelector(":scope > .md-nav__link .md-ellipsis");
    if (!label) return;

    const title = label.textContent.trim();
    const match = title.match(sectionPattern);
    if (match) {
      item.classList.add("book-section-start", `book-section-${sectionNumber[match[1]]}`);
    } else if (/^附录 A\b/.test(title)) {
      item.classList.add("book-section-start", "book-section-appendix");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  scopePrimaryNav();
  decorateNavigation();
});
