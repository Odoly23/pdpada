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

/* Modal konfirmasi: hanya untuk form bertanda data-confirm (logout dan hapus data). */
(function () {
	var modal = document.getElementById('confirmModal');
	if (!modal || !window.jQuery) { return; }
	var pending = null;
	document.addEventListener('submit', function (ev) {
		var form = ev.target;
		if (!form.hasAttribute || !form.hasAttribute('data-confirm')) { return; }
		ev.preventDefault();
		pending = form;
		document.getElementById('confirmModalText').textContent = form.getAttribute('data-confirm');
		document.getElementById('confirmModalOk').firstChild.nodeValue = (form.getAttribute('data-confirm-ok') || 'Sim') + ' ';
		window.jQuery(modal).modal('show');
	});
	document.getElementById('confirmModalOk').addEventListener('click', function () {
		if (pending) { var f = pending; pending = null; f.submit(); }  // submit() tidak memicu event submit lagi
	});
	window.jQuery(modal).on('hidden.bs.modal', function () { pending = null; });
})();
