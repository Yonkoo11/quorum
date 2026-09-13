/* The next front page: one screen, two states. quorum.js already owns the theme and the memory switch;
   this file owns the morph, the load reveal, and the one-time entrance of the numbers. */
(function () {
  "use strict";
  var html = document.documentElement,
      page = document.querySelector(".page"),
      wash = document.querySelector(".wash"),
      cue = document.querySelector(".morph-cue"),
      cueText = cue && cue.querySelector(".morph-cue__text"),
      numbers = document.getElementById("numbers");
  if (!page || !wash || !cue || !numbers) return;

  var stacked = window.matchMedia("(max-width: 760px), (max-aspect-ratio: 6/7)"),
      reduced = window.matchMedia("(prefers-reduced-motion: reduce)"),
      MORPH_FAILSAFE = 1200, COOLDOWN = 250, WHEEL_MIN = 12, SWIPE_MIN = 40,
      busy = false, entered = false, entranceTimer = null;

  /* ---------- load reveal: each [data-reveal] ramps in on its own delay, then stays ---------- */
  var ready = function () {
    requestAnimationFrame(function () { html.classList.add("is-ready"); });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
  document.addEventListener("animationend", function (e) {
    if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-reveal")) e.target.classList.add("is-revealed");
  });
  setTimeout(function () {
    var els = document.querySelectorAll("[data-reveal]");
    for (var i = 0; i < els.length; i++) els[i].classList.add("is-revealed");
  }, 3200);

  /* ---------- the numbers' entrance: once, on top of the morph, never again ---------- */
  var entrance = function () {
    if (entered) return;
    entered = true;
    if (reduced.matches) return;
    html.classList.add("entrance-active");
    var done = function () { html.classList.remove("entrance-active"); clearTimeout(entranceTimer); };
    entranceTimer = setTimeout(done, 3200);
    var last = numbers.querySelector(".vs tbody tr:last-child");
    if (last) last.addEventListener("animationend", done, { once: true });
  };

  var setCue = function (screen) {
    var b = screen === "numbers";
    if (cueText) cueText.textContent = cueText.getAttribute(b ? "data-b" : "data-a");
    cue.setAttribute("aria-label", b ? "Back to the statement" : "See the numbers");
  };

  /* ---------- the morph ---------- */
  var go = function (screen) {
    if (busy || page.getAttribute("data-screen") === screen) return;
    busy = true;
    page.classList.add("is-morphing");
    page.setAttribute("data-screen", screen);
    setCue(screen);
    if (screen === "numbers") entrance();
    var finished = false;
    var finish = function () {
      if (finished) return;
      finished = true;
      wash.removeEventListener("transitionend", onEnd);
      page.classList.remove("is-morphing");
      setTimeout(function () { busy = false; }, COOLDOWN);
    };
    /* the clip and the paper wash run on the same clock; Chrome reports the wash's end reliably, the clip's not always */
    var onEnd = function (e) {
      if (e.target === wash && (e.propertyName === "clip-path" || e.propertyName === "opacity")) finish();
    };
    wash.addEventListener("transitionend", onEnd);
    setTimeout(finish, MORPH_FAILSAFE);
  };
  var next = function () { go("numbers"); };
  var back = function () { go("hero"); };

  window.addEventListener("wheel", function (e) {
    if (stacked.matches || Math.abs(e.deltaY) <= WHEEL_MIN) return;
    if (e.deltaY > 0) next(); else back();
  }, { passive: true });

  window.addEventListener("keydown", function (e) {
    if (stacked.matches || e.altKey || e.ctrlKey || e.metaKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.key === " " && tag === "BUTTON") return;
    if (e.key === "ArrowDown" || e.key === "PageDown" || e.key === " ") { e.preventDefault(); next(); }
    else if (e.key === "ArrowUp" || e.key === "PageUp" || e.key === "Escape") { e.preventDefault(); back(); }
  });

  var y0 = null;
  window.addEventListener("touchstart", function (e) { y0 = e.touches[0].clientY; }, { passive: true });
  window.addEventListener("touchend", function (e) {
    if (y0 === null || stacked.matches) { y0 = null; return; }
    var dy = e.changedTouches[0].clientY - y0;
    y0 = null;
    if (Math.abs(dy) < SWIPE_MIN) return;
    if (dy < 0) next(); else back();
  }, { passive: true });

  cue.addEventListener("click", function () {
    if (stacked.matches) {
      numbers.scrollIntoView({ behavior: reduced.matches ? "auto" : "smooth", block: "start" });
      return;
    }
    if (page.getAttribute("data-screen") === "numbers") back(); else next();
  });

  /* ---------- stacked: the page scrolls, the cue scrolls with it, the entrance runs on first sight ---------- */
  if ("IntersectionObserver" in window) {
    var seen = new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        if (!stacked.matches) continue;
        cue.hidden = entries[i].isIntersecting;
        if (entries[i].isIntersecting) entrance();
      }
    }, { threshold: 0.2 });
    seen.observe(numbers);
  }
  var onLayoutChange = function () {
    if (!stacked.matches) cue.hidden = false;
    page.classList.remove("is-morphing");
    page.setAttribute("data-screen", "hero");
    setCue("hero");
    busy = false;
  };
  stacked.addEventListener("change", onLayoutChange);
  if (stacked.matches) cue.hidden = false;
})();
