/* Dropdown berantai Suku -> Aldeia (AJAX). Form harus punya atribut data-aldeias-url. */
$(function () {
	var $form = $('form[data-aldeias-url]');
	if (!$form.length) { return; }
	var url = $form.data('aldeias-url');
	$('#id_village').on('change', function () {
		var $aldeia = $('#id_aldeia');
		if ($aldeia.prop('disabled')) { return; }
		$.ajax({
			url: url,
			data: { 'village': $(this).val() },
			success: function (data) { $aldeia.html(data); }
		});
	});
});
