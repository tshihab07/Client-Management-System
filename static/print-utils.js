(function () {
  // store original title once on load
  const originalTitle = document.title;

  // monkey-patch window.print() to clean title before printing
  const originalPrint = window.print;
  window.print = function () {
    // temporarily blank the title
    document.title = "Payment Status";

    // trigger native print
    originalPrint.apply(window, arguments);

    // restore title after a short delay
    setTimeout(() => {
      document.title = originalTitle;
    }, 1000);
  };

  // handle Ctrl+P / Cmd+P system print shortcut
  document.addEventListener('keydown', function (e) {
    // Ctrl+P or Cmd+P
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
      e.preventDefault();
      window.print();
    }
  });

})();