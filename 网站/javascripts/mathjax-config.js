window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  },
  chtml: {
    fontURL:
      "https://cdn.bootcdn.net/ajax/libs/mathjax/3.2.2/es5/output/chtml/fonts/woff-v2"
  }
};

// Material 换页后补排一次
if (typeof document$ !== "undefined" && document$.subscribe) {
  document$.subscribe(function () {
    if (window.MathJax && MathJax.typesetPromise) {
      MathJax.typesetPromise().catch(function () {});
    }
  });
}
