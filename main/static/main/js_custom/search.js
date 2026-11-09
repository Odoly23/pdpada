/* Saran pencarian membru (typeahead). Aman dari XSS: hanya textContent, tidak ada innerHTML dari data. */
(function () {
	var input = document.getElementById('search-q');
	var box = document.getElementById('search-suggest');
	if (!input || !box || !window.jQuery) { return; }
	var url = input.getAttribute('data-url');
	var timer = null;

	function hide() { box.style.display = 'none'; box.textContent = ''; }
	function render(items) {
		box.textContent = '';
		if (!items.length) { hide(); return; }
		items.forEach(function (it) {
			var a = document.createElement('a');
			a.className = 'list-group-item list-group-item-action py-2';
			a.href = it.url;
			var strong = document.createElement('strong');
			strong.textContent = it.nome;
			var small = document.createElement('small');
			small.className = 'd-block text-muted';
			small.textContent = it.nu_eleitoral + ' · ' + it.suku + ' / ' + it.aldeia + ' · ' + it.aprovasaun;
			a.appendChild(strong);
			a.appendChild(small);
			box.appendChild(a);
		});
		box.style.display = 'block';
	}
	input.addEventListener('input', function () {
		clearTimeout(timer);
		var q = input.value.trim();
		if (q.length < 2) { hide(); return; }
		timer = setTimeout(function () { $.getJSON(url, { q: q }).done(render); }, 250);
	});
	document.addEventListener('click', function (e) { if (e.target !== input && !box.contains(e.target)) { hide(); } });
	input.addEventListener('keydown', function (e) { if (e.key === 'Escape') { hide(); } });
})();
