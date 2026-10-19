/**
 * Hover curated display formulas → stagger fake tensors through each op.
 * Lives on the website only; manuscripts stay clean.
 */
(function () {
  "use strict";

  var FLOWS = [
    {
      id: "softmax",
      test: function (src) {
        return (
          /z_i\s*\/\s*\\tau|z_i\/\\tau/.test(src) &&
          /exp/.test(src) &&
          /sum_j|sum_\{j\}/.test(src) &&
          !/Attention/.test(src)
        );
      },
      title: "Softmax",
      subtitle: "V = 3 · z = (2.0, 1.0, 0.1)（示意）",
      steps: [
        {
          label: "logits",
          tex: "z",
          shape: "ℝ³",
          values: ["2.0", "1.0", "0.1"],
          note: "任意实数；尚未归一化",
        },
        {
          label: "τ = 1",
          tex: "softmax(z)",
          shape: "ℝ³",
          values: ["≈0.66", "≈0.24", "≈0.10"],
          note: "标准温度；和为 1",
        },
        {
          label: "τ = 2",
          tex: "softmax(z/2)",
          shape: "ℝ³",
          values: ["≈0.51", "≈0.31", "≈0.18"],
          note: "温度升高 → 分布变平",
        },
        {
          label: "τ = 0.5",
          tex: "softmax(z/0.5)",
          shape: "ℝ³",
          values: ["≈0.86", "≈0.12", "≈0.02"],
          note: "温度降低 → 质量更集中到最大项",
        },
      ],
    },
    {
      id: "kl",
      test: function (src) {
        return (
          /mathrm\{KL\}|D_\{\\mathrm\{KL\}\}|D_\{KL\}/.test(src) &&
          /log/.test(src) &&
          /p_i/.test(src)
        );
      },
      title: "KL 散度",
      subtitle: "V = 3 · 自然对数（示意）",
      steps: [
        {
          label: "目标分布",
          tex: "p",
          shape: "ℝ³",
          values: ["0.70", "0.20", "0.10"],
          note: "真实或教师分布",
        },
        {
          label: "近似分布",
          tex: "q",
          shape: "ℝ³",
          values: ["0.50", "0.30", "0.20"],
          note: "模型或学生分布",
        },
        {
          label: "逐项",
          tex: "pᵢ log(pᵢ/qᵢ)",
          shape: "ℝ³",
          values: ["≈0.24", "≈−0.08", "≈−0.07"],
          note: "正负可以并存；最后再求和",
        },
        {
          label: "求和",
          tex: "D_KL(p∥q)",
          shape: "标量",
          values: ["≈0.09"],
          note: "非负；p=q 时为 0；对调 p、q 一般得另一个数",
        },
      ],
    },
    {
      id: "autoregressive",
      test: function (src) {
        return (
          /p\s*\(\s*x_1/.test(src) &&
          /\\prod|prod_\{t/.test(src) &&
          /x_t/.test(src) &&
          /x_\{t-1\}|x_1,\s*\\ldots,\s*x_\{t-1\}/.test(src) &&
          !/Birds|mathrm\{Birds\}/.test(src)
        );
      },
      title: "自回归连乘",
      subtitle: "n = 6 · Birds sing up in the tree（接 1.1）",
      wide: true,
      steps: [
        {
          label: "t = 1",
          tex: "p(x₁)",
          shape: "前缀 ∅",
          values: ["Birds"],
          note: "桌上还空着，先猜第一张",
        },
        {
          label: "t = 2",
          tex: "p(x₂ | x₁)",
          shape: "前缀长 1",
          values: ["Birds", "→ sing"],
          note: "已有 Birds，猜下一张",
        },
        {
          label: "t = 3",
          tex: "p(x₃ | x₁:₂)",
          shape: "前缀长 2",
          values: ["Birds", "sing", "→ up"],
          note: "前缀变长，条件变长",
        },
        {
          label: "t = 4",
          tex: "p(x₄ | x₁:₃)",
          shape: "前缀长 3",
          values: ["…", "up", "→ in"],
          note: "每一步只多猜一张",
        },
        {
          label: "t = 5",
          tex: "p(x₅ | x₁:₄)",
          shape: "前缀长 4",
          values: ["…", "in", "→ the"],
          note: "与 1.1 拼到 Birds sing up in the 同一时刻",
        },
        {
          label: "t = 6",
          tex: "p(x₆ | x₁:₅)",
          shape: "前缀长 5",
          values: ["…", "the", "→ tree"],
          note: "在 tree 与 water 之间，前文更支持 tree",
        },
        {
          label: "整句得分",
          tex: "∏ t=1…6",
          shape: "标量",
          values: ["六项相乘"],
          note: "整句分 = 六次 next-token 概率之积；生成逐步猜，训练用这个分",
        },
      ],
    },
    {
      id: "attention",
      test: function (src) {
        // TeX is \operatorname{Attention}(Q,K,V) → "Attention}(Q"
        return (
          /Attention\}?\s*\(\s*Q\s*,\s*K\s*,\s*V\s*\)/.test(src) &&
          /softmax/.test(src) &&
          /sqrt/.test(src)
        );
      },
      title: "Attention",
      subtitle: "n = 3 · d = 4 · d_h = 2 · 因果掩码（示意）",
      wide: true,
      steps: [
        {
          label: "输入",
          tex: "X",
          shape: "3×4",
          matrix: [
            ["0.50", "0.10", "−0.20", "0.30"],
            ["0.20", "0.40", "0.10", "−0.10"],
            ["0.00", "0.30", "0.50", "0.20"],
          ],
          note: "三个位置，每个隐藏维 d = 4",
        },
        {
          label: "三个投影矩阵",
          tex: "W_Q, W_K, W_V",
          shape: "各 4×2",
          matrices: [
            {
              name: "W_Q",
              matrix: [
                ["0.40", "0.10"],
                ["0.20", "−0.30"],
                ["−0.10", "0.50"],
                ["0.30", "0.20"],
              ],
            },
            {
              name: "W_K",
              matrix: [
                ["0.30", "−0.20"],
                ["0.10", "0.40"],
                ["0.50", "0.10"],
                ["−0.20", "0.30"],
              ],
            },
            {
              name: "W_V",
              matrix: [
                ["0.20", "0.40"],
                ["−0.10", "0.30"],
                ["0.40", "0.10"],
                ["0.10", "−0.20"],
              ],
            },
          ],
          note: "同一 X 分别乘三块权重，得到 Q、K、V",
        },
        {
          label: "得到 Q、K、V",
          tex: "Q=XW_Q …",
          shape: "各 3×2",
          matrices: [
            {
              name: "Q",
              matrix: [
                ["0.35", "0.12"],
                ["0.22", "0.05"],
                ["0.18", "0.28"],
              ],
            },
            {
              name: "K",
              matrix: [
                ["0.10", "0.25"],
                ["0.30", "0.08"],
                ["0.15", "0.20"],
              ],
            },
            {
              name: "V",
              matrix: [
                ["0.40", "0.10"],
                ["0.20", "0.30"],
                ["0.10", "0.25"],
              ],
            },
          ],
          note: "行 = 位置；列 = 头内维 d_h",
        },
        {
          label: "分数表",
          tex: "QKᵀ / √d_h",
          shape: "3×3",
          matrix: [
            ["1.20", "0.40", "0.55"],
            ["0.35", "1.50", "0.60"],
            ["0.25", "0.70", "1.10"],
          ],
          note: "第 i 行 = 位置 i 对所有位置的原始分数",
        },
        {
          label: "加因果掩码",
          tex: "+ M",
          shape: "3×3",
          matrix: [
            ["1.20", "−∞", "−∞"],
            ["0.35", "1.50", "−∞"],
            ["0.25", "0.70", "1.10"],
          ],
          note: "严格上三角置 −∞，右边位置看不见",
        },
        {
          label: "行内 softmax",
          tex: "α",
          shape: "3×3",
          matrix: [
            ["1.00", "0", "0"],
            ["0.24", "0.76", "0"],
            ["0.18", "0.28", "0.54"],
          ],
          note: "每一行和为 1；被掩码的格子权重为 0",
        },
        {
          label: "加权 Value",
          tex: "α V",
          shape: "3×2",
          matrix: [
            ["0.40", "0.10"],
            ["0.25", "0.25"],
            ["0.19", "0.23"],
          ],
          note: "内容来自 V，比例来自 α；输出仍是 n×d_h",
        },
      ],
    },
    {
      id: "rmsnorm",
      test: function (src) {
        return /RMSNorm/.test(src) && /sum_i|sum_\{i\}/.test(src);
      },
      title: "RMSNorm",
      subtitle: "d = 4 · g = 1（示意）",
      steps: [
        {
          label: "输入",
          tex: "x",
          shape: "ℝ⁴",
          values: ["2.0", "−2.0", "1.0", "0.0"],
          note: "不做减均值，只按模长缩放",
        },
        {
          label: "均方根",
          tex: "rms",
          shape: "标量",
          values: ["≈1.58"],
          note: "√(mean(x²)+ε) ≈ √(2.25)",
        },
        {
          label: "缩放",
          tex: "x / rms",
          shape: "ℝ⁴",
          values: ["≈1.26", "≈−1.26", "≈0.63", "0.00"],
          note: "各维同除一个标量；再乘可学习增益 g",
        },
      ],
    },
    {
      id: "swiglu",
      test: function (src) {
        return /SwiGLU/.test(src) && /SiLU/.test(src) && /(gate|up|down)/.test(src);
      },
      title: "SwiGLU",
      subtitle: "d = 4 → d_ff = 3 → d = 4（示意）",
      steps: [
        {
          label: "输入",
          tex: "x",
          shape: "ℝ⁴",
          values: ["0.50", "−0.20", "0.80", "0.10"],
          note: "一个 token 的隐藏状态",
        },
        {
          label: "门支路",
          tex: "W_gate x",
          shape: "ℝ³",
          values: ["3.00", "−2.00", "1.00"],
          note: "升维后的门 logit",
        },
        {
          label: "内容支路",
          tex: "W_up x",
          shape: "ℝ³",
          values: ["2.00", "2.00", "−1.00"],
          note: "升维后的内容向量 u",
        },
        {
          label: "SiLU 门",
          tex: "SiLU(W_gate x)",
          shape: "ℝ³",
          values: ["≈2.86", "≈−0.24", "≈0.73"],
          note: "z·sigmoid(z)；可大于 1，也可略负",
        },
        {
          label: "逐维相乘",
          tex: "g ⊙ u",
          shape: "ℝ³",
          values: ["≈5.72", "≈−0.48", "≈−0.73"],
          note: "同为 u=2 的两维，门不同 → 一个放大、一个掐掉",
        },
        {
          label: "降维",
          tex: "W_down (g ⊙ u)",
          shape: "ℝ⁴",
          values: ["1.20", "−0.35", "0.90", "0.05"],
          note: "压回隐藏维，残差支路输出",
        },
      ],
    },
    {
      id: "rope",
      test: function (src) {
        return /s_\{3,0\}/.test(src) && /R_3/.test(src) && /R_0/.test(src);
      },
      title: "RoPE 打分",
      subtitle: "当前位置 3 · ω = 30° · d_h = 2（示意）",
      steps: [
        {
          label: "转 Query",
          tex: "R₃ q₃",
          shape: "ℝ²",
          values: ["0.00", "1.00"],
          note: "q₃=(1,0) 转 90° → (0,1)",
        },
        {
          label: "转 Key",
          tex: "R₁ k₁",
          shape: "ℝ²",
          values: ["0.87", "0.50"],
          note: "k₁=(1,0) 转 30°；相对角进点积",
        },
        {
          label: "相对分数",
          tex: "s₃₁",
          shape: "标量",
          values: ["≈0.35"],
          note: "(R₃q₃)ᵀ(R₁k₁)/√2；内容同向但相对距离改了分",
        },
        {
          label: "取内容",
          tex: "α·v",
          shape: "ℝ²",
          values: ["…"],
          note: "Value 不转；RoPE 只改谁分高，不改 v 本身",
        },
      ],
    },
    {
      id: "moe",
      test: function (src) {
        return /MoE\}?\s*\(\s*x\s*\)/.test(src) && /E_i/.test(src) && /g_i/.test(src);
      },
      title: "MoE 路由",
      subtitle: "N = 4 · k = 2（与正文同一组分数）",
      steps: [
        {
          label: "路由分数",
          tex: "s = W_r x",
          shape: "ℝ⁴",
          values: ["1.0", "3.0", "0.2", "2.0"],
          note: "每个专家一个 logit",
        },
        {
          label: "TopK",
          tex: "T(x)",
          shape: "下标",
          values: ["1", "3"],
          note: "只留下分最高的 k 个；0 与 2 本步空闲",
        },
        {
          label: "混合权重",
          tex: "softmax(s_T)",
          shape: "ℝ²",
          values: ["≈0.73", "≈0.27"],
          note: "只在选中的专家上归一化，和为 1",
        },
        {
          label: "加权专家",
          tex: "Σ g_i E_i(x)",
          shape: "ℝᵈ",
          values: ["0.73 E₁", "+", "0.27 E₃"],
          note: "总参随 N 涨，本 token 激活只随 k",
        },
      ],
    },
  ];

  /**
   * Chapter pages (under each book dir) that host at least one flow.
   * Keep in sync when adding FLOWS.
   */
  var FLOW_CHAPTER_PATHS = [
    "/01-architecture/03/", // 第 0 章 Softmax / KL
    "/01-architecture/04/", // 第 1 章 自回归连乘
    "/01-architecture/05/", // 第 2 章 Attention
    "/01-architecture/09/", // 第 5 章 RMSNorm / SwiGLU
    "/01-architecture/10/", // 第 6 章 RoPE
    "/01-architecture/14/", // 第 9 章 MoE / SwiGLU
  ];

  function makeMark() {
    var mark = document.createElement("span");
    mark.className = "formula-flow-mark";
    mark.title = "含数据流";
    mark.setAttribute("aria-label", "含数据流");
    return mark;
  }

  function normalizePath(href) {
    if (!href) return "";
    try {
      var u = new URL(href, window.location.origin);
      var p = u.pathname;
      if (!p.endsWith("/")) p += "/";
      return p;
    } catch (e) {
      return href;
    }
  }

  function pathHasFlow(pathname) {
    var p = normalizePath(pathname);
    for (var i = 0; i < FLOW_CHAPTER_PATHS.length; i++) {
      if (p.indexOf(FLOW_CHAPTER_PATHS[i]) !== -1) return true;
    }
    return false;
  }

  /** Left / drawer chapter nav: mark chapters that have formula flows. */
  function markChapterNav() {
    document
      .querySelectorAll(".md-sidebar--primary .md-nav__link[href]")
      .forEach(function (link) {
        if (!pathHasFlow(link.getAttribute("href"))) return;
        if (link.querySelector(".formula-flow-mark")) return;
        link.classList.add("has-formula-flow");
        var label = link.querySelector(".md-ellipsis") || link;
        label.appendChild(makeMark());
      });
  }

  function headingIdBefore(el) {
    var headings = document.querySelectorAll(
      ".md-typeset h2[id], .md-typeset h3[id], .md-typeset h4[id]"
    );
    var best = null;
    for (var i = 0; i < headings.length; i++) {
      var h = headings[i];
      if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) {
        best = h;
      }
    }
    return best ? best.id : null;
  }

  /** Right on-page TOC: mark headings that contain a bound flow. */
  function markPageToc() {
    var ids = {};
    document.querySelectorAll(".formula-flow-host").forEach(function (host) {
      var id = headingIdBefore(host);
      if (id) ids[id] = true;
    });
    document
      .querySelectorAll(".md-sidebar--secondary .md-nav__link[href^='#']")
      .forEach(function (link) {
        var href = link.getAttribute("href") || "";
        var id = href.charAt(0) === "#" ? href.slice(1) : "";
        if (!id || !ids[id]) return;
        if (link.querySelector(".formula-flow-mark")) return;
        link.classList.add("has-formula-flow");
        var label = link.querySelector(".md-ellipsis") || link;
        label.appendChild(makeMark());
      });
  }

  function snapshotSources() {
    document.querySelectorAll(".arithmatex").forEach(function (el) {
      if (el.getAttribute("data-ff-src")) return;
      el.setAttribute("data-ff-src", el.textContent || "");
    });
  }

  function sourceOf(el) {
    return el.getAttribute("data-ff-src") || el.textContent || "";
  }

  function findFlow(src) {
    for (var i = 0; i < FLOWS.length; i++) {
      if (FLOWS[i].test(src)) return FLOWS[i];
    }
    return null;
  }

  function chipsHtml(values) {
    return (
      '<span class="formula-flow-chips">' +
      values
        .map(function (v) {
          return '<span class="formula-flow-chip">' + v + "</span>";
        })
        .join("") +
      "</span>"
    );
  }

  function matrixHtml(matrix, name) {
    if (!matrix || !matrix.length) return "";
    var cols = matrix[0].length;
    var rows = matrix
      .map(function (row) {
        return (
          '<div class="formula-flow-matrix__row">' +
          row
            .map(function (cell) {
              return (
                '<span class="formula-flow-matrix__cell">' + cell + "</span>"
              );
            })
            .join("") +
          "</div>"
        );
      })
      .join("");
    return (
      '<div class="formula-flow-matrix" style="--ff-cols:' +
      cols +
      '">' +
      (name
        ? '<div class="formula-flow-matrix__name">' + name + "</div>"
        : "") +
      '<div class="formula-flow-matrix__body">' +
      rows +
      "</div></div>"
    );
  }

  function stepValuesHtml(step) {
    if (step.matrices && step.matrices.length) {
      return (
        '<div class="formula-flow-matrices">' +
        step.matrices
          .map(function (m) {
            return matrixHtml(m.matrix, m.name);
          })
          .join("") +
        "</div>"
      );
    }
    if (step.matrix) return matrixHtml(step.matrix, null);
    if (step.values) return chipsHtml(step.values);
    return "";
  }

  function buildPopover(flow) {
    var root = document.createElement("div");
    root.className =
      "formula-flow-pop" + (flow.wide ? " formula-flow-pop--wide" : "");
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-label", flow.title);

    root.innerHTML =
      '<div class="formula-flow-pop__head">' +
      '<div class="formula-flow-pop__title">' +
      flow.title +
      "</div>" +
      '<div class="formula-flow-pop__sub">' +
      flow.subtitle +
      "</div>" +
      "</div>";

    var rail = document.createElement("ol");
    rail.className = "formula-flow-pop__rail";
    flow.steps.forEach(function (step, idx) {
      var li = document.createElement("li");
      li.className = "formula-flow-pop__step";
      li.style.setProperty("--step-i", String(idx));
      li.innerHTML =
        '<div class="formula-flow-pop__step-top">' +
        '<span class="formula-flow-pop__label">' +
        step.label +
        "</span>" +
        '<code class="formula-flow-pop__tex">' +
        step.tex +
        "</code>" +
        '<span class="formula-flow-pop__shape">' +
        step.shape +
        "</span>" +
        "</div>" +
        stepValuesHtml(step) +
        '<div class="formula-flow-pop__note">' +
        step.note +
        "</div>";
      rail.appendChild(li);
    });
    root.appendChild(rail);

    var foot = document.createElement("div");
    foot.className = "formula-flow-pop__foot";
    foot.textContent = "悬停查看 · 示意数值";
    root.appendChild(foot);
    return root;
  }

  function bindHost(el, flow) {
    if (el.closest(".formula-flow-host")) return;

    var wrap = document.createElement("div");
    wrap.className = "formula-flow-host";
    wrap.setAttribute("data-ff-id", flow.id);
    el.parentNode.insertBefore(wrap, el);
    wrap.appendChild(el);

    var badge = document.createElement("button");
    badge.type = "button";
    badge.className = "formula-flow-badge";
    badge.textContent = "数据流";
    badge.setAttribute("aria-expanded", "false");
    wrap.appendChild(badge);

    var pop = buildPopover(flow);
    wrap.appendChild(pop);

    var hideTimer = null;
    function show() {
      if (hideTimer) {
        clearTimeout(hideTimer);
        hideTimer = null;
      }
      wrap.classList.add("is-open");
      badge.setAttribute("aria-expanded", "true");
      pop.querySelectorAll(".formula-flow-pop__step").forEach(function (step) {
        step.classList.remove("is-in");
        void step.offsetWidth;
        step.classList.add("is-in");
      });
    }
    function scheduleHide() {
      hideTimer = setTimeout(function () {
        wrap.classList.remove("is-open");
        badge.setAttribute("aria-expanded", "false");
      }, 140);
    }

    wrap.addEventListener("mouseenter", show);
    wrap.addEventListener("mouseleave", scheduleHide);
    badge.addEventListener("click", function (e) {
      e.preventDefault();
      if (wrap.classList.contains("is-open")) scheduleHide();
      else show();
    });
  }

  function run() {
    snapshotSources();
    var seen = {};
    document.querySelectorAll(".arithmatex").forEach(function (el) {
      // display math only
      if (el.tagName !== "DIV") return;
      var src = sourceOf(el);
      var flow = findFlow(src);
      if (!flow || seen[flow.id]) return;
      seen[flow.id] = true;
      bindHost(el, flow);
    });
    markChapterNav();
    markPageToc();
  }

  snapshotSources();

  function afterMathJax(fn) {
    if (window.MathJax && MathJax.startup && MathJax.startup.promise) {
      MathJax.startup.promise.then(fn).catch(fn);
      return;
    }
    // MathJax defer 尚未就绪时别空等 450ms 堵交互；短轮询几次即可
    var n = 0;
    (function wait() {
      if (window.MathJax && MathJax.startup && MathJax.startup.promise) {
        MathJax.startup.promise.then(fn).catch(fn);
        return;
      }
      if (++n > 40) {
        fn();
        return;
      }
      setTimeout(wait, 50);
    })();
  }

  // 目录小圆点不依赖公式排版，立刻标，别跟 MathJax 绑死
  function boot() {
    markChapterNav();
    afterMathJax(function () {
      run();
    });
    if (typeof document$ !== "undefined" && document$.subscribe) {
      document$.subscribe(function () {
        markChapterNav();
        setTimeout(function () {
          snapshotSources();
          run();
        }, 0);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
