(function () {
  "use strict";

  // Zensical/Material renders each collapsible sidebar section as
  // <li class="md-nav__item--nested"> wrapping a checkbox
  // (.md-nav__toggle) that shows/hides that section's own <ul> -- every
  // checkbox is independent by default, so with enough sections (this
  // site's nav has grown a lot) they stack up expanded at once and the
  // sidebar turns into a wall of links. This makes opening one section
  // close its siblings, at every nesting level, so at most one branch
  // per level is ever open.
  //
  // Delegated on document instead of attached to specific nav nodes --
  // this site uses instant navigation (page content swaps via fetch),
  // and a delegated listener keeps working even if the sidebar markup
  // gets replaced, with nothing to re-attach after a page change.
  document.addEventListener("change", function (event) {
    var input = event.target;
    if (!input.matches || !input.matches("input.md-nav__toggle")) {
      return;
    }
    if (!input.checked) {
      return;
    }
    var item = input.closest("li.md-nav__item--nested");
    if (!item || !item.parentElement) {
      return;
    }
    var siblingToggles = item.parentElement.querySelectorAll(
      ":scope > li.md-nav__item--nested > input.md-nav__toggle"
    );
    for (var i = 0; i < siblingToggles.length; i++) {
      if (siblingToggles[i] !== input) {
        siblingToggles[i].checked = false;
      }
    }
  });
})();
