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
  // 主脚本本地；字体仍走 CDN（异步，不堵导航）
  chtml: {
    fontURL:
      "https://cdn.bootcdn.net/ajax/libs/mathjax/3.2.2/es5/output/chtml/fonts/woff-v2"
  }
};
