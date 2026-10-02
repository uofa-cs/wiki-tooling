// Sortable tables everywhere, plus a filter box on the course index.
// Uses Material's instant-navigation hook so it re-runs on page changes.
document$.subscribe(function () {
  document.querySelectorAll("article table:not([class])").forEach(function (table) {
    new Tablesort(table);
  });

  var marker = document.querySelector("[data-course-filter]");
  if (!marker || marker.dataset.ready) return;
  marker.dataset.ready = "true";

  var input = document.createElement("input");
  input.type = "search";
  input.placeholder = "Filter courses by number, title, difficulty, or term (e.g. 'F26', 'machine', 'Brutal')";
  input.className = "course-filter";
  input.setAttribute("aria-label", "Filter courses");
  marker.appendChild(input);

  var unreviewed = document.createElement("label");
  unreviewed.className = "course-filter-toggle";
  unreviewed.innerHTML = '<input type="checkbox"> Only courses that need reviews';
  marker.appendChild(unreviewed);
  var toggle = unreviewed.querySelector("input");

  function apply() {
    var terms = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    document.querySelectorAll("article table tbody tr").forEach(function (row) {
      var text = row.textContent.toLowerCase();
      var cells = row.querySelectorAll("td");
      var reviewed = cells.length && cells[cells.length - 1].textContent.trim() !== "";
      var match = terms.every(function (t) { return text.indexOf(t) !== -1; });
      row.style.display = match && !(toggle.checked && reviewed) ? "" : "none";
    });
  }
  input.addEventListener("input", apply);
  toggle.addEventListener("change", apply);
});
