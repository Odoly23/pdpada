/* Teks Tetun untuk semua tabel DataTables (dipasang sekali di layout). */
$.extend(true, $.fn.dataTable.defaults, {
	language: {
		search: 'Buka:',
		searchPlaceholder: 'Hakerek naran, nu. ka seluk…',
		lengthMenu: 'Hatudu _MENU_ rejistu',
		info: "Hatudu _START_ to'o _END_ husi _TOTAL_ rejistu",
		infoEmpty: 'Laiha rejistu',
		infoFiltered: '(filtra husi rejistu _MAX_)',
		zeroRecords: "Laiha rejistu ne'ebé hetan",
		emptyTable: 'Laiha dadus',
		loadingRecords: 'Hein…',
		paginate: { first: 'Dahuluk', previous: 'Molok', next: 'Tuir mai', last: 'Ikus' }
	}
});
