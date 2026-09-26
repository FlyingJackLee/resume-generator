/* 预览分页线：在预览（screen 媒体的连续长页）里模拟 Chromium 的 print
 * fragmentation，标出导出 PDF 时的分页位置。
 *
 * 分页规则与导出侧保持一致：
 *  - 页面可用内容高 27.1cm = A4 29.7cm - 0.8cm(上边距) - 1.8cm(下边距)，
 *    对应 awesome-cv.css 的 @page 与 web/build.py export_pdf() 的 margin 参数。
 *    若那边改动，需同步修改 PAGE_H（web/tests/test_page_guides.py 会红起来提醒）。
 *  - break-inside: avoid 的整块（.section.page-break-before、li、表格行、
 *    flex/grid 容器——Chromium 不在 flex/grid 内部分页）整块放置；
 *    超过一页高的 avoid 段照常内部拆分。
 *  - break-after: avoid（.section-title、.entry-head）与后续内容粘连下移。
 *  - 其余文本块按行拆分，受 orphans/widows（Chromium 默认 2）约束。
 *  - 分页处相邻 margin 被截断；border/padding 随原子保留（box-decoration-break: slice）。
 *
 * 原子的 avoid/粘连状态都读 getComputedStyle 计算值，模板包 theme.css 的
 * 覆盖自然生效，不硬编码类名。分页线画在“断点”处（被推下页的内容与
 * 前文之间的间隙中点），而不是整页填充线位置——avoid 推页时页面会提前结束。
 */
(() => {
  "use strict";

  const PX_PER_CM = 96 / 2.54;
  const PAGE_H = 27.1 * PX_PER_CM; // 29.7 - 0.8(top) - 1.8(bottom)
  const EPS = 0.5; // 浮点测量容差（px）

  const page = document.querySelector(".page");
  if (!page) return;

  const isAvoid = (cs, shorthand, legacy) => {
    const a = cs[shorthand];
    const b = cs[legacy];
    return a === "avoid" || a === "avoid-page" || b === "avoid";
  };

  // Chromium 不在 flex/grid/表格行内部 fragmentation，视为不可拆块
  const MONOLITHIC = new Set([
    "flex", "inline-flex", "grid", "inline-grid",
    "table-row", "table-row-group", "table-caption",
  ]);
  const isReplaced = (el) =>
    ["IMG", "SVG", "VIDEO", "CANVAS", "IFRAME"].includes(el.tagName);

  const textOf = (el) =>
    el ? (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 24) : "";

  // --- 原子收集 ------------------------------------------------------------
  // 原子：
  //   { kind:"block", el, rect, glueNext }                  不可拆块
  //   { kind:"lines", el, rect, lines, orphans, widows }    可按行拆分的文本块
  // rect 一律是 border-box 实测（getBoundingClientRect）；行从 Range.getClientRects
  // 按 top 聚类得出，行距 lead 相对上一参考点（块顶或上一行底），各行成本之和恰为块高。
  function hasBlockChildren(el) {
    for (const child of el.children) {
      const d = getComputedStyle(child).display;
      if (d !== "none" && d !== "contents" && !d.startsWith("inline")) return true;
    }
    return false;
  }

  function measureLines(el, rect) {
    const range = document.createRange();
    range.selectNodeContents(el);
    const raw = Array.from(range.getClientRects()).filter((r) => r.height > 0);
    if (!raw.length) return null;
    const rects = [];
    for (const r of raw) {
      const last = rects[rects.length - 1];
      if (last && Math.abs(r.top - last.top) < 1) {
        last.bottom = Math.max(last.bottom, r.bottom); // 同一行多个片段（内联元素）
      } else {
        rects.push({ top: r.top, bottom: r.bottom });
      }
    }
    let ref = rect.top;
    const lines = rects.map((r) => {
      const line = { top: r.top, bottom: r.bottom, lead: r.top - ref, height: r.bottom - r.top };
      ref = r.bottom;
      return line;
    });
    // 块底剩余（padding/末行半行距）计入最后一行，保证行成本之和 = 块高
    lines[lines.length - 1].height += rect.bottom - rects[rects.length - 1].bottom;
    return lines;
  }

  function collectAtoms(root, atoms) {
    for (const el of root.children) {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.position === "absolute" || cs.position === "fixed") {
        continue; // 脱离文档流的元素（如照片）不参与 fragmentation
      }
      const rect = el.getBoundingClientRect();
      if (rect.height <= 0) continue;
      const glueNext = isAvoid(cs, "breakAfter", "pageBreakAfter");
      const insideAvoid = isAvoid(cs, "breakInside", "pageBreakInside");

      if ((insideAvoid && rect.height <= PAGE_H + EPS) || MONOLITHIC.has(cs.display)
          || cs.display === "list-item" || isReplaced(el)) {
        atoms.push({ kind: "block", el, rect, glueNext });
        continue;
      }
      // 超过一页的 break-inside: avoid 段：Chromium 不会就地拆分——只要当前页
      // 已有内容，整段仍推到新页顶部再内部拆分（实验验证见 test_page_guides）。
      // 因此下钻子元素时给组内第一个原子打 freshPage 标记，由 simulate() 强制起新页。

      if (hasBlockChildren(el)) {
        const before = atoms.length;
        collectAtoms(el, atoms);
        if (insideAvoid && atoms.length > before) atoms[before].freshPage = true;
        continue;
      }
      const lines = measureLines(el, rect);
      if (lines) {
        atoms.push({
          kind: "lines", el, rect, lines, glueNext,
          orphans: parseInt(cs.orphans, 10) || 2,
          widows: parseInt(cs.widows, 10) || 2,
        });
      } else {
        atoms.push({ kind: "block", el, rect, glueNext });
      }
    }
  }

  // --- 装箱模拟 ------------------------------------------------------------
  // 返回分页点数组，每个元素 { page, y, nextText }：
  //   page = 分页后新页的序号（第 page+1 页从此处开始，第 1 页从文档顶开始）
  //   y = 分页线位置（屏幕视口坐标，画在断点前后内容的间隙中点）
  function simulate(atoms) {
    const gaps = atoms.map((a, i) =>
      i === 0 ? 0 : Math.max(0, a.rect.top - atoms[i - 1].rect.bottom));
    const breaks = [];
    let used = 0; // 当前页已用高度
    // glued = 已放在当前页页尾、且要求与下一原子粘连的原子（可能要整体下移）
    let glued = null;
    let prevBottom = null; // 屏幕坐标上，当前页最后一个已放置单元的底

    const pushBreak = (nextTop, nextText) => {
      breaks.push({
        page: breaks.length + 2, // 此分页开启的新页（第 1 页无分页线）
        y: prevBottom === null ? nextTop : (prevBottom + nextTop) / 2,
        nextText,
      });
      used = 0;
    };

    for (let i = 0; i < atoms.length; i++) {
      let a = atoms[i];
      let atFreshPage = false;

      // 超页 avoid 段的开头：当前页已有内容时强制换到新页顶（Chromium 行为）
      if (a.freshPage && used > 0) {
        pushBreak(a.kind === "lines" ? a.lines[0].top : a.rect.top, textOf(a.el));
        glued = null;
        atFreshPage = true;
      }

      // 不足 orphans+widows 行的文本块拆不开，按整块处理
      if (a.kind === "lines" && a.lines.length < a.orphans + a.widows) {
        a = { kind: "block", el: a.el, rect: a.rect, glueNext: a.glueNext };
      }

      if (a.kind === "block") {
        const cost = (used > 0 ? gaps[i] : 0) + a.rect.height;
        if (used + cost <= PAGE_H + EPS) {
          used += cost;
          glued = a.glueNext
            ? { height: a.rect.height, rect: a.rect, el: a.el, prevBottom }
            : null;
          prevBottom = a.rect.bottom;
          continue;
        }
        if (glued && used - glued.height > 0) {
          // 上一原子要求粘连：分页点前移到它之前，让它带着本原子下移
          used -= glued.height;
          prevBottom = glued.prevBottom;
          pushBreak(glued.rect.top, textOf(glued.el));
          used = glued.height + gaps[i] + a.rect.height;
          if (used > PAGE_H + EPS) { // 粘连后仍超页（极端情况）：在粘连边界强制分页
            pushBreak(a.rect.top, textOf(a.el));
            used = a.rect.height;
          }
        } else {
          // glued 但上一原子已在页顶（无法再前移）→ avoid 尽力而为，就地分页
          if (!atFreshPage) pushBreak(a.rect.top, textOf(a.el));
          used = a.rect.height;
        }
        glued = a.glueNext
          ? { height: a.rect.height, rect: a.rect, el: a.el, prevBottom }
          : null;
        prevBottom = a.rect.bottom;
        continue;
      }

      // lines：按行装箱
      const lines = a.lines;
      let k = 0; // 本块内下一个待放置的行
      let placed = 0; // 本块在当前页已放置的行数
      let guard = 0;
      while (k < lines.length && guard++ < 1000) {
        const remaining = lines.length - k;
        // 当前页剩余空间内能容纳的行数（首段含块间距）
        let space = PAGE_H + EPS - used;
        if (placed === 0 && used > 0) space -= gaps[i];
        let can = 0;
        let cost = 0;
        while (can < remaining) {
          const c = lines[k + can].height
            + (can === 0 && used === 0 ? lines[k + can].lead / 2 : lines[k + can].lead);
          if (cost + c > space) break;
          cost += c;
          can += 1;
        }

        // orphan/widow 约束下的有效放置行数：
        //  - 本页段最少 minNeeded 行（块首段为 orphans，续段为 1）
        //  - 分页后下一页至少 widows 行，不够则回拉
        let take = can;
        if (take > 0) {
          const minNeeded = placed === 0 ? a.orphans : 1;
          const rest = remaining - take;
          if (placed === 0 && take < minNeeded) {
            take = 0; // 页尾放不下 orphan 行 → 本段整段后移
          } else if (rest > 0 && rest < a.widows) {
            take = Math.min(can, Math.max(minNeeded, remaining - Math.min(a.widows, remaining)));
          }
        }

        if (take > 0) {
          let c = 0;
          for (let j = 0; j < take; j += 1) {
            c += lines[k + j].height
              + (j === 0 && used === 0 ? lines[k + j].lead / 2 : lines[k + j].lead);
          }
          if (placed === 0 && used > 0) c += gaps[i];
          used += c;
          prevBottom = lines[k + take - 1].bottom;
          k += take;
          placed += take;
          continue;
        }

        // 放不下任何有效行 → 分页
        if (placed === 0) {
          if (glued && used - glued.height > 0) {
            // 粘连的上一原子（如标题）与本块开头一起下移
            used -= glued.height;
            prevBottom = glued.prevBottom;
            pushBreak(glued.rect.top, textOf(glued.el));
            used = glued.height;
            glued = null;
            continue; // 在新页顶重试放置本块
          }
          if (!atFreshPage) pushBreak(lines[k].top, textOf(a.el));
          continue;
        }
        pushBreak(lines[k].top, textOf(a.el));
        placed = 0;
      }
      // 块结束：整块放完且要求与下一原子粘连（近似粘连整块；此情形模板中不存在）
      glued = a.glueNext && k === lines.length
        ? { height: a.rect.height, rect: a.rect, el: a.el, prevBottom }
        : null;
      if (k === lines.length) prevBottom = a.rect.bottom;
    }
    return breaks;
  }

  // --- 绘制 ----------------------------------------------------------------
  function draw(breaks) {
    const zh = document.documentElement.lang === "zh";
    const style = document.createElement("style");
    style.textContent = [
      ".page-guides-overlay{position:absolute;inset:0;pointer-events:none;z-index:9;}",
      ".page-guide-line{position:absolute;left:0;right:0;border-top:1px dashed rgba(220,53,34,.55);}",
      ".page-guide-label{position:absolute;right:2px;transform:translateY(4px);",
      "  font:600 9px/1.4 system-ui,sans-serif;color:#fff;background:rgba(220,53,34,.75);",
      "  padding:0 6px;border-radius:3px;letter-spacing:.05em;}",
    ].join("");
    document.head.appendChild(style);
    if (getComputedStyle(page).position === "static") page.style.position = "relative";

    const pageTop = page.getBoundingClientRect().top;
    const overlay = document.createElement("div");
    overlay.className = "page-guides-overlay";
    overlay.setAttribute("aria-hidden", "true");
    for (const b of breaks) {
      const line = document.createElement("div");
      line.className = "page-guide-line";
      line.style.top = `${b.y - pageTop}px`;
      overlay.appendChild(line);
      const label = document.createElement("div");
      label.className = "page-guide-label";
      label.style.top = `${b.y - pageTop}px`;
      label.textContent = zh ? `第 ${b.page} 页` : `Page ${b.page}`;
      overlay.appendChild(label);
    }
    page.appendChild(overlay);
    // 调试与测试钩子：模拟出的总页数与分页点
    window.__pageGuides = {
      pages: breaks.length + 1,
      breaks: breaks.map((b) => ({ page: b.page, y: b.y, nextText: b.nextText })),
    };
  }

  // --- 时机：DOM（defer）+ 字体 + 图片 -------------------------------------
  const loaded = new Promise((resolve) => {
    if (document.readyState === "complete") resolve();
    else window.addEventListener("load", resolve, { once: true });
  });
  Promise.all([document.fonts ? document.fonts.ready : Promise.resolve(), loaded]).then(() => {
    const atoms = [];
    collectAtoms(page, atoms);
    if (!atoms.length) return;
    const breaks = simulate(atoms);
    if (breaks.length) draw(breaks);
    else window.__pageGuides = { pages: 1, breaks: [] };
  });
})();
