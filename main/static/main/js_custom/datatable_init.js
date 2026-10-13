/* DataTables standar SGDM-PDPADA: ekspor Excel/PDF/Print, searchBuilder, scroll horizontal. */
$(document).ready(function () {
	var $t = $('#example');
	if (!$t.length) { return; }
	var exportCols = { columns: ':not(.no-export)' };
	var table = $t.removeAttr('width').DataTable({
		scrollX: true,
		paging: true,
		pageLength: 25,
		deferRender: true,
		searchBuilder: true,
		columnDefs: [{ targets: 'no-export', orderable: false }],
		buttons: [
			{ extend: 'excelHtml5', autoFilter: true, sheetName: 'Membru', exportOptions: exportCols },
			{ extend: 'pdfHtml5', orientation: 'landscape', pageSize: 'A4', exportOptions: exportCols },
			{ extend: 'print', exportOptions: exportCols },
			'colvis'
		],
		dom: 'Bfrtip'
	});
	table.searchBuilder.container().prependTo(table.table().container());
});
