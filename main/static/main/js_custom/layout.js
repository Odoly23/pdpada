/* Sidebar mobile: geser dari kiri dan dorong konten (CSS: body.sb-open). */
(function () {
	var btn = document.getElementById('btn-ham');
	var sb = document.getElementById('sidebar');
	if (!btn || !sb) { return; }
	function setOpen(open) {
		sb.classList.toggle('active', open);
		document.body.classList.toggle('sb-open', open);
		btn.setAttribute('aria-expanded', open ? 'true' : 'false');
	}
	btn.addEventListener('click', function () { setOpen(!sb.classList.contains('active')); });
	window.addEventListener('resize', function () { if (window.innerWidth >= 992) { setOpen(false); } });
})();
