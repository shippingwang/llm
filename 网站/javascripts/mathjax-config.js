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
  // 字体与主脚本同属 bootcdn；主脚本挂了时见 overrides 里的本地回退
  chtml: {
    fontURL:
      "https://cdn.bootcdn.net/ajax/libs/mathjax/3.2.2/es5/output/chtml/fonts/woff-v2"
  }
};

// Material 换页 / 脚本晚到时补排一次，避免一直露 \( \) 源码
(function () {
  function typeset() {
    if (!window.MathJax || !MathJax.typesetPromise) return;
    MathJax.typesetPromise().catch(function () {});
  }
  if (typeof document$ !== "undefined" && document$.subscribe) {
    document$.subscribe(typeset);
  }
  // CDN 慢时：首屏可能先出源码，等 MathJax 就绪再排
  var n = 0;
  (function wait() {
    if (window.MathJax && MathJax.typesetPromise) {
      typeset();
      return;
    }
    if (++n < 80) setTimeout(wait, 100);
  })();
})();
