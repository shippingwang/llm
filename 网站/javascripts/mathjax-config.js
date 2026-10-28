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
  // 主脚本本地单文件；\boldsymbol 等扩展与字体仍走 CDN
  loader: {
    paths: {
      mathjax: "https://cdn.bootcdn.net/ajax/libs/mathjax/3.2.2/es5"
    }
  },
  chtml: {
    fontURL:
      "https://cdn.bootcdn.net/ajax/libs/mathjax/3.2.2/es5/output/chtml/fonts/woff-v2"
  }
};
