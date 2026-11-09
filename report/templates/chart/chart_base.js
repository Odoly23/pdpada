// Grafik Highcharts (styledMode, warna dari js_custom/chart.css), tanpa server ekspor luar (offline).
Highcharts.setOptions({
	lang: { noData: 'Laiha data' },
	credits: { enabled: false },
	exporting: { fallbackToExportServer: false },
});

// opts: {type: 'pie'|'column', name: 'Membru', colorIndex: {label: indeksWarna}}
function drawChart(containerId, endpoint, opts) {
	$.ajax({
		method: "GET",
		url: endpoint,
		success: function (data) {
			var pie = (opts.type === 'pie');
			var series = pie
				? data.label.map(function (l, i) {
					var p = { name: l, y: data.obj[i] };
					if (opts.colorIndex && opts.colorIndex[l] !== undefined) { p.colorIndex = opts.colorIndex[l]; }
					return p;
				})
				: data.obj;
			Highcharts.chart(containerId, {
				chart: { type: opts.type, styledMode: true },
				title: { text: '' },
				xAxis: pie ? undefined : { categories: data.label },
				yAxis: pie ? undefined : { title: { text: 'Total ' + (opts.name || 'Membru') }, tickInterval: 1, allowDecimals: false },
				legend: { enabled: pie },
				plotOptions: pie
					? { pie: { allowPointSelect: true, dataLabels: { enabled: true, format: '{point.name}: {point.y}' } } }
					: { column: { borderRadius: 5 } },
				series: [{
					name: opts.name || 'Membru',
					data: series,
					tooltip: { valueSuffix: ' Membru' }
				}]
			});
		},
		error: function (error_data) {
			console.log("error");
			console.log(error_data);
		}
	});
}
