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

document.addEventListener("DOMContentLoaded", decorateNavigation);
