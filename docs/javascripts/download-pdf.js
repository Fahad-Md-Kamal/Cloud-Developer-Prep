(function () {
  "use strict";

  // Resolve the site root from this script's own URL, so it works
  // regardless of page depth (chapter-36/2-1-.../) or a GitHub Pages
  // subpath -- entirely client-side, no server required.
  var scriptUrl = document.currentScript.src;
  var siteRoot = scriptUrl.replace(/javascripts\/download-pdf\.js.*$/, "");

  function injectButton() {
    var btn = document.createElement("button");
    btn.id = "download-pdf-btn";
    btn.type = "button";
    btn.textContent = "Download PDF";
    btn.addEventListener("click", downloadPdf);
    document.body.appendChild(btn);
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
