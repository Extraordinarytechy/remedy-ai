// Applies the light/dark choice before the page paints (light is the default).
// Order: ?theme=dark|light in the URL (not saved), then the saved choice.
// The only thing RemedyAI keeps in the browser is this one preference.
(function () {
  try {
    var q = new URLSearchParams(location.search).get('theme');
    var t = q === 'dark' || q === 'light' ? q : localStorage.getItem('remedyai-theme');
    if (t === 'dark') document.documentElement.classList.add('dark');
  } catch (e) {
    /* storage unavailable: stay light */
  }
})();
