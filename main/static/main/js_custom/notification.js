/* Notifikasaun: polling badge lonceng tiap 5 detik (berhenti saat tab tersembunyi). */
(function () {
	var bell = document.getElementById('notifDropdown');
	if (!bell || !window.jQuery) { return; }
	var url = bell.getAttribute('data-url');

	function show(data) {
		var v = data.value > 0 ? data.value : '';
		['notifbadge', 'notifbadge-sb'].forEach(function (id) {
			var el = document.getElementById(id);
			if (el) { el.textContent = v; }
		});
		['pendente', 'rejeitadu'].forEach(function (k) {
			$('[data-notif-key="' + k + '"]').text(data[k]);
		});
	}
	function poll() {
		if (document.hidden) { return; }
		$.get(url, show);
	}
	setInterval(poll, 5000);
	document.addEventListener('visibilitychange', poll);
})();
