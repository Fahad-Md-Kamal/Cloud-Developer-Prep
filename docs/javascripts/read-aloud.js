(function () {
  "use strict";

  // Graceful degradation -- some browsers (notably older mobile ones)
  // don't implement the Web Speech API at all. Don't inject anything
  // rather than show a button that does nothing.
  if (!("speechSynthesis" in window)) {
    return;
  }

  var STATE_IDLE = "idle";
  var STATE_READING = "reading";
  var STATE_PAUSED = "paused";

  var state = STATE_IDLE;
  var btn = null;
  var speedBtn = null;
  var speedWrap = null;
  var speedMenu = null;
  var autoBtn = null;
  var queue = [];
  var queueIndex = 0;
  var autoContinue = false;
  var navigationTimer = null;
  var activeEl = null;
  var ACTIVE_CLASS = "read-aloud-active";
  var lastHref = location.href;
  var navigationObserverAttached = false;

  // Bumped on every stop/start/jump. Utterance callbacks capture the
  // token at creation time and ignore themselves if it's gone stale --
  // this is what lets startReadingFrom() cancel an in-flight utterance
  // without its "interrupted" error firing after the new one started.
  var readToken = 0;

  // Ascending order -- this is also the order the speed menu lists them in.
  // Capped at 1.25x -- anything faster reads too fast to follow comfortably.
  var SPEED_STEPS = [0.5, 0.75, 1, 1.25];
  var currentRate = 1;

  function safeGet(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function safeSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      // Private browsing / disabled storage -- preference just won't persist.
    }
  }

  (function restorePreferences() {
    var storedRate = parseFloat(safeGet("readAloudRate"));
    if (!isNaN(storedRate) && SPEED_STEPS.indexOf(storedRate) !== -1) {
      currentRate = storedRate;
    }
    autoContinue = safeGet("readAloudAutoContinue") === "true";
  })();

  var MARKER_CLASS = "read-aloud-marker";
  // Table cells don't get a "read from here" marker -- absolutely
  // positioning one in a narrow cell breaks the table layout -- but
  // they're still included in the reading queue itself.
  var MARKER_EXCLUDE_SELECTOR = "td, th";

  // Elements to strip before extracting text -- decorative heading-anchor
  // icons or our own UI aloud is worse than skipping them. "pre" (real
  // multi-line code blocks) is here for clarity, though it's redundant:
  // BLOCK_SELECTOR below never descends into one in the first place.
  // Inline "code" spans (like `prefetch_related`) are deliberately NOT
  // skipped -- those are just formatted terms the reader wants read,
  // not code to suppress.
  var SKIP_SELECTOR = [
    "pre", "script", "style",
    ".headerlink", ".md-icon",
    "#read-aloud-toolbar", "." + MARKER_CLASS,
    "#download-pdf-btn", "#print-all-pages",
  ].join(", ");

  // One chunk per block-level element rather than one giant utterance --
  // this keeps pause/resume granular and sidesteps a long-standing
  // Chrome bug where very long single utterances can silently stop.
  var BLOCK_SELECTOR = "h1, h2, h3, h4, h5, h6, p, li, td, th, blockquote";

  // Returns {el, text} pairs instead of plain strings so markers can be
  // attached to the real elements and a click can look up "which chunk
  // is this" by element identity.
  function getReadableBlocks() {
    var article = document.querySelector(".md-content__inner");
    if (!article) {
      return [];
    }
    var rawBlocks = article.querySelectorAll(BLOCK_SELECTOR);
    var blocks = [];
    for (var i = 0; i < rawBlocks.length; i++) {
      var el = rawBlocks[i];
      if (el.closest(SKIP_SELECTOR)) {
        continue;
      }
      var clone = el.cloneNode(true);
      var toRemove = clone.querySelectorAll(SKIP_SELECTOR);
      for (var j = 0; j < toRemove.length; j++) {
        toRemove[j].remove();
      }
      var text = clone.textContent.replace(/\s+/g, " ").trim();
      if (text) {
        blocks.push({ el: el, text: text });
      }
    }
    return blocks;
  }

  function updateButton() {
    if (!btn) {
      return;
    }
    if (state === STATE_IDLE) {
      btn.textContent = "🔊 Read Aloud";
    } else if (state === STATE_READING) {
      btn.textContent = "⏸ Pause";
    } else {
      btn.textContent = "▶ Resume";
    }
  }

  function updateSpeedButton() {
    if (!speedBtn) {
      return;
    }
    speedBtn.textContent = currentRate + "×";
  }

  function updateSpeedMenu() {
    if (!speedMenu) {
      return;
    }
    var items = speedMenu.querySelectorAll("button");
    for (var i = 0; i < items.length; i++) {
      items[i].classList.toggle("active", parseFloat(items[i].dataset.rate) === currentRate);
    }
  }

  function updateAutoButton() {
    if (!autoBtn) {
      return;
    }
    autoBtn.classList.toggle("active", autoContinue);
  }

  // Error codes that mean "a real TTS engine/voice problem," worth a
  // short, specific, user-facing message instead of a console-only log
  // the average reader will never open devtools to see.
  var ERROR_MESSAGES = {
    "not-allowed": "Click the button directly to allow audio",
    "synthesis-failed": "No text-to-speech voice available on this device",
    "synthesis-unavailable": "No text-to-speech voice available on this device",
    "language-unavailable": "No voice available for this page's language",
    "voice-unavailable": "No text-to-speech voice available on this device",
  };

  // Error codes meaning "no working speech engine/voice at all" -- these
  // need the reader to actually go fix something on their system, not
  // just click again, so they get the one-time detailed instructions
  // below instead of only the brief on-button message.
  var NO_VOICE_ERRORS = ["synthesis-failed", "synthesis-unavailable", "voice-unavailable"];
  var noVoiceHelpShown = false;

  function detectPlatform() {
    var ua = navigator.userAgent || "";
    if (/Android/.test(ua)) {
      return "android";
    }
    if (/iPhone|iPad|iPod/.test(ua)) {
      return "ios";
    }
    if (/Windows/.test(ua)) {
      return "windows";
    }
    if (/Mac OS X/.test(ua)) {
      return "mac";
    }
    if (/Linux/.test(ua)) {
      return "linux";
    }
    return "unknown";
  }

  function showNoVoiceHelp() {
    // Only interrupt with the full instructions once per page load --
    // an environment problem doesn't change between clicks, so repeating
    // the same alert every time would just be annoying.
    if (noVoiceHelpShown) {
      return;
    }
    noVoiceHelpShown = true;

    var platform = detectPlatform();
    var message;
    if (platform === "linux") {
      message =
        "No text-to-speech voice was found on this Linux system.\n\n" +
        "Chrome relies on a system speech engine it doesn't ship itself " +
        "-- most Linux desktops don't have one installed by default. " +
        "Install one and reload the page:\n\n" +
        "  Debian/Ubuntu:  sudo apt install speech-dispatcher espeak-ng\n" +
        "  Fedora:         sudo dnf install speech-dispatcher espeak-ng\n" +
        "  Arch:           sudo pacman -S speech-dispatcher espeak-ng\n\n" +
        "Then fully restart your browser (not just reload the tab) and " +
        "try again. Windows, macOS, iOS, and Android all ship a working " +
        "voice by default -- this is specifically a Linux gap. If it " +
        "still fails after that, some Chrome builds on Linux never pick " +
        "up the system voice at all -- try Firefox, which generally has " +
        "better support for this.";
    } else {
      message =
        "No text-to-speech voice was found, which is unusual on " +
        platform + ". Try:\n\n" +
        "  - Fully closing and reopening the browser (not just the tab)\n" +
        "  - Checking your system's accessibility/speech settings have " +
        "a voice installed and enabled\n" +
        "  - Trying a different browser (Chrome, Edge, or Safari)";
    }
    alert(message);
  }

  function showFailureMessage(errorCode) {
    if (!btn) {
      return;
    }
    btn.textContent = "⚠ " + (ERROR_MESSAGES[errorCode] || "Read-aloud failed — see console");
    btn.disabled = true;
    setTimeout(function () {
      if (btn) {
        btn.disabled = false;
        updateButton();
      }
    }, 5000);

    if (NO_VOICE_ERRORS.indexOf(errorCode) !== -1) {
      showNoVoiceHelp();
    }
  }

  // Lets the reader follow along visually -- lights up whichever block is
  // currently being spoken and dims the previous one. Left on through a
  // pause (so it still shows where reading stopped); cleared in stopReading().
  function setActiveHighlight(el) {
    if (activeEl && activeEl !== el) {
      activeEl.classList.remove(ACTIVE_CLASS);
    }
    activeEl = el || null;
    if (activeEl) {
      activeEl.classList.add(ACTIVE_CLASS);
    }
  }

  function speakNext(token) {
    if (token !== readToken) {
      return;
    }
    if (queueIndex >= queue.length) {
      stopReading();
      return;
    }
    setActiveHighlight(queue[queueIndex].el);
    var utterance = new SpeechSynthesisUtterance(queue[queueIndex].text);
    utterance.rate = currentRate;
    utterance.onend = function () {
      if (token !== readToken) {
        return;
      }
      // A manual stop/cancel also fires "end" -- only advance the
      // queue if we're still actually supposed to be reading.
      if (state === STATE_READING) {
        queueIndex++;
        speakNext(token);
      }
    };
    utterance.onerror = function (event) {
      if (token !== readToken) {
        return;
      }
      // "interrupted"/"canceled" fire when WE call speechSynthesis.cancel()
      // ourselves -- expected behavior, not a real failure.
      if (event.error === "interrupted" || event.error === "canceled") {
        return;
      }
      console.error("Read-aloud error:", event.error);
      stopReading();
      showFailureMessage(event.error);
    };
    window.speechSynthesis.speak(utterance);
  }

  function startReading() {
    readToken++;
    var token = readToken;
    window.speechSynthesis.cancel();
    queue = getReadableBlocks();
    queueIndex = 0;
    if (queue.length === 0) {
      return;
    }
    state = STATE_READING;
    updateButton();
    speakNext(token);
  }

  // Jumps the queue to whichever block the reader clicked a marker on,
  // cancelling anything already in progress.
  function startReadingFrom(targetEl) {
    readToken++;
    var token = readToken;
    window.speechSynthesis.cancel();
    queue = getReadableBlocks();
    if (queue.length === 0) {
      return;
    }
    var idx = 0;
    for (var i = 0; i < queue.length; i++) {
      if (queue[i].el === targetEl) {
        idx = i;
        break;
      }
    }
    queueIndex = idx;
    state = STATE_READING;
    updateButton();
    speakNext(token);
  }

  // A SpeechSynthesisUtterance's rate can't be changed once it's
  // speaking, so a speed change takes effect by re-speaking the current
  // chunk at the new rate instead of waiting for the next one.
  function restartCurrentChunk() {
    if (state !== STATE_READING) {
      return;
    }
    readToken++;
    var token = readToken;
    window.speechSynthesis.cancel();
    speakNext(token);
  }

  function pauseReading() {
    window.speechSynthesis.pause();
    state = STATE_PAUSED;
    updateButton();
  }

  function resumeReading() {
    window.speechSynthesis.resume();
    state = STATE_READING;
    updateButton();
  }

  function stopReading() {
    readToken++;
    window.speechSynthesis.cancel();
    state = STATE_IDLE;
    queueIndex = 0;
    queue = [];
    setActiveHighlight(null);
    updateButton();
  }

  function handleClick() {
    if (state === STATE_IDLE) {
      startReading();
    } else if (state === STATE_READING) {
      pauseReading();
    } else {
      resumeReading();
    }
  }

  function selectSpeed(rate) {
    if (SPEED_STEPS.indexOf(rate) === -1) {
      return;
    }
    currentRate = rate;
    safeSet("readAloudRate", String(currentRate));
    updateSpeedButton();
    updateSpeedMenu();
    restartCurrentChunk();
  }

  function toggleSpeedMenu() {
    if (speedWrap) {
      speedWrap.classList.toggle("open");
    }
  }

  function closeSpeedMenu() {
    if (speedWrap) {
      speedWrap.classList.remove("open");
    }
  }

  function toggleAutoContinue() {
    autoContinue = !autoContinue;
    safeSet("readAloudAutoContinue", String(autoContinue));
    updateAutoButton();
  }

  function markerKeydown(el) {
    return function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        startReadingFrom(el);
      }
    };
  }

  // Inserts a small clickable "▶" before every readable block so a
  // reader can jump straight to a paragraph/heading/list item instead
  // of always starting from the top of the page.
  function attachMarkers() {
    var blocks = getReadableBlocks();
    for (var i = 0; i < blocks.length; i++) {
      var el = blocks[i].el;
      if (el.matches(MARKER_EXCLUDE_SELECTOR) || el.dataset.readAloudMarked) {
        continue;
      }
      el.dataset.readAloudMarked = "true";
      el.classList.add("read-aloud-markable");

      var marker = document.createElement("span");
      marker.className = MARKER_CLASS;
      marker.textContent = "▶";
      marker.title = "Read from here";
      marker.setAttribute("role", "button");
      marker.setAttribute("tabindex", "0");
      marker.addEventListener("click", (function (targetEl) {
        return function (e) {
          e.stopPropagation();
          startReadingFrom(targetEl);
        };
      })(el));
      marker.addEventListener("keydown", markerKeydown(el));
      el.insertBefore(marker, el.firstChild);
    }
  }

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

  function injectToolbar() {
    if (document.getElementById("read-aloud-btn")) {
      return;
    }
    var container = getActionsContainer();
    if (!container) {
      return;
    }

    btn = document.createElement("button");
    btn.id = "read-aloud-btn";
    btn.type = "button";
    btn.className = "md-header__button header-action-btn";
    updateButton();
    btn.addEventListener("click", handleClick);
    container.appendChild(btn);

    speedWrap = document.createElement("div");
    speedWrap.id = "read-aloud-speed-wrap";

    speedBtn = document.createElement("button");
    speedBtn.id = "read-aloud-speed-btn";
    speedBtn.type = "button";
    speedBtn.className = "md-header__button header-action-btn";
    speedBtn.title = "Reading speed -- hover to pick one";
    updateSpeedButton();
    // Hover reveals the menu via CSS (:hover / :focus-within below) --
    // the click handler is only there for touch screens, which have no
    // hover state to trigger it.
    speedBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleSpeedMenu();
    });
    speedWrap.appendChild(speedBtn);

    speedMenu = document.createElement("div");
    speedMenu.id = "read-aloud-speed-menu";
    for (var s = 0; s < SPEED_STEPS.length; s++) {
      var rate = SPEED_STEPS[s];
      var item = document.createElement("button");
      item.type = "button";
      item.textContent = rate + "×";
      item.dataset.rate = String(rate);
      item.addEventListener("click", function (e) {
        e.stopPropagation();
        selectSpeed(parseFloat(this.dataset.rate));
        closeSpeedMenu();
      });
      speedMenu.appendChild(item);
    }
    updateSpeedMenu();
    speedWrap.appendChild(speedMenu);
    container.appendChild(speedWrap);

    autoBtn = document.createElement("button");
    autoBtn.id = "read-aloud-auto-btn";
    autoBtn.type = "button";
    autoBtn.className = "md-header__button header-action-btn";
    autoBtn.title = "Keep reading automatically when you move to a new page";
    autoBtn.textContent = "↻ Auto";
    updateAutoButton();
    autoBtn.addEventListener("click", toggleAutoContinue);
    container.appendChild(autoBtn);

    attachMarkers();

    // This site uses instant navigation (page content swaps via fetch,
    // no full reload) -- and the swap can replace the whole
    // .md-content__inner element (and, potentially, the header) rather
    // than mutating it in place, so an observer bound to one specific
    // element can go dead and silently stop firing the moment the
    // reader navigates once. document.body is never replaced, so watch
    // that instead, and use the URL itself (not "did something change
    // under body") to decide whether a real navigation happened --
    // that's what tells a page change apart from incidental DOM noise,
    // including our own marker insertions below.
    //
    // injectToolbar() can re-enter this function (see the no-op guard
    // at its top) if the header buttons ever get wiped out by the same
    // swap -- guard against attaching a second observer each time that
    // happens.
    if (navigationObserverAttached || !("MutationObserver" in window)) {
      return;
    }
    navigationObserverAttached = true;
    var observer = new MutationObserver(function () {
      // The header buttons may have been wiped out by the same swap --
      // cheap to check every time, and injectToolbar() no-ops if
      // they're still there.
      injectToolbar();
      if (location.href === lastHref) {
        return;
      }
      lastHref = location.href;
      var wasReading = state !== STATE_IDLE;
      if (wasReading) {
        stopReading();
      }
      attachMarkers();
      if (wasReading && autoContinue) {
        if (navigationTimer) {
          clearTimeout(navigationTimer);
        }
        navigationTimer = setTimeout(function () {
          startReading();
        }, 400);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Stop narrating if the tab is hidden/closed rather than leave speech
  // running against a page the user has navigated away from.
  document.addEventListener("visibilitychange", function () {
    if (document.hidden && state !== STATE_IDLE) {
      stopReading();
    }
  });

  // Touch-screen fallback: the speed menu opens via toggleSpeedMenu() on
  // tap, and since there's no hover to dismiss it again, any other tap
  // on the page closes it.
  document.addEventListener("click", closeSpeedMenu);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectToolbar);
  } else {
    injectToolbar();
  }
})();
