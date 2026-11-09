/* DataTables standar SGDM-PDPADA: tombol ekspor berwarna (Excel/PDF/Print/Kolona), scroll horizontal, teks Tetun.
   Pencarian sederhana (kotak "Buka"); tidak memakai Search Builder agar mudah bagi pengguna awam. */
$(document).ready(function () {
	var $t = $('#example');
	if (!$t.length) { return; }
	var exportCols = { columns: ':not(.no-export)' };
	$t.DataTable({
		scrollX: true,
		autoWidth: false,
		paging: true,
		pageLength: 25,
		deferRender: true,
		columnDefs: [{ targets: 'no-export', orderable: false }],
		buttons: [
			{ extend: 'excelHtml5', text: '<i class="fa fa-file-excel-o"></i> Excel', className: 'btn btn-sm btn-success', autoFilter: true, sheetName: 'Membru', exportOptions: exportCols },
			{ extend: 'pdfHtml5', text: '<i class="fa fa-file-pdf-o"></i> PDF', className: 'btn btn-sm btn-danger', orientation: 'landscape', pageSize: 'A4', exportOptions: exportCols },
			{ extend: 'print', text: '<i class="fa fa-print"></i> Imprime', className: 'btn btn-sm btn-primary', exportOptions: exportCols },
			{ extend: 'colvis', text: '<i class="fa fa-columns"></i> Kolona', className: 'btn btn-sm btn-outline-primary' }
		],
		dom: "<'row'<'col-md-7'B><'col-md-5'f>>rt<'row'<'col-md-5'i><'col-md-7'p>><'row'<'col-12'l>>"
	});
});
