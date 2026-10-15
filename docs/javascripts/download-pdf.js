(function () {
  "use strict";

  // Resolve the site root from this script's own URL, so it works
  // regardless of page depth (chapter-36/2-1-.../) or a GitHub Pages
  // subpath -- entirely client-side, no server required.
  var scriptUrl = document.currentScript.src;
  var siteRoot = scriptUrl.replace(/javascripts\/download-pdf\.js.*$/, "");

  // Buttons live in the header instead of floating over the page, so
  // they don't sit on top of the nav/ToC. Several scripts share one
  // #header-custom-actions row -- whichever loads first creates it.
  function getActionsContainer() {
    var existing = document.getElementById("header-custom-actions");
    if (existing) {
      return existing;
    }
    var headerInner = document.querySelector(".md-header__inner");
    if (!headerInner) {
      return null;
    }
    var container = document.createElement("div");
    container.id = "header-custom-actions";
    var source = headerInner.querySelector(".md-header__source");
    if (source) {
      headerInner.insertBefore(container, source);
    } else {
      headerInner.appendChild(container);
    }
    return container;
  }

  function injectButton() {
    if (document.getElementById("download-pdf-btn")) {
      return;
    }
    var container = getActionsContainer();
    if (!container) {
      return;
    }
    var btn = document.createElement("button");
    btn.id = "download-pdf-btn";
    btn.type = "button";
    btn.className = "md-header__button header-action-btn";
    btn.title = "Download the whole site as a PDF";
    btn.textContent = "PDF";
    btn.addEventListener("click", downloadPdf);
    container.appendChild(btn);
  }

  // This site uses instant navigation (page content swaps via fetch, no
  // full reload) -- if that swap ever replaces the header itself, this
  // button would silently vanish. Re-check on every navigation and
  // re-inject if needed.
  var lastHref = location.href;
  if ("MutationObserver" in window) {
    new MutationObserver(function () {
      if (location.href === lastHref) {
        return;
      }
      lastHref = location.href;
      injectButton();
    }).observe(document.body, { childList: true, subtree: true });
  }

  function extractContent(htmlText) {
    var doc = new DOMParser().parseFromString(htmlText, "text/html");
    var article = doc.querySelector(".md-content__inner");
    return article ? article.innerHTML : "";
  }

  async function downloadPdf() {
    var btn = document.getElementById("download-pdf-btn");
    var originalText = btn.textContent;
    btn.disabled = true;

    try {
      var manifestRes = await fetch(siteRoot + "nav-order.json");
      if (!manifestRes.ok) {
        throw new Error("nav-order.json fetch failed: " + manifestRes.status);
      }
      var pages = await manifestRes.json();

      var container = document.createElement("div");
      container.id = "print-all-pages";

      for (var i = 0; i < pages.length; i++) {
        btn.textContent = "Loading " + (i + 1) + "/" + pages.length + "…";
        var page = pages[i];
        var res = await fetch(siteRoot + page.url);
        if (!res.ok) {
          console.warn("Skipping page that failed to load:", page.url);
          continue;
        }
        var text = await res.text();
        var html = extractContent(text);

        var section = document.createElement("section");
        section.className = "print-page";
        section.innerHTML = html;
        container.appendChild(section);
      }

      document.body.appendChild(container);
      document.body.classList.add("print-pdf-mode");

      btn.textContent = originalText;
      btn.disabled = false;

      // Calling window.print() immediately after injecting this much DOM
      // can capture the page before the browser has actually laid out
      // and painted the new content (syntax-highlighted code especially),
      // producing blank gaps in the printed output. Wait for web fonts
      // plus a couple of paint cycles before printing.
      await document.fonts.ready;
      await new Promise(function (resolve) {
        requestAnimationFrame(function () {
          requestAnimationFrame(resolve);
        });
      });

      window.print();
    } catch (err) {
      console.error("PDF export failed:", err);
      alert("PDF export failed — see browser console for details.");
      btn.textContent = originalText;
      btn.disabled = false;
    }
  }

  // Clean up after the print dialog closes (or is cancelled) so the
  // page is back to normal, not left with the injected content.
  window.addEventListener("afterprint", function () {
    var container = document.getElementById("print-all-pages");
    if (container) {
      container.remove();
    }
    document.body.classList.remove("print-pdf-mode");
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectButton);
  } else {
    injectButton();
  }
})();
