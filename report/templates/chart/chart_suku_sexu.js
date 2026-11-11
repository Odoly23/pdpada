$.get("{% url 'api-suku-sexu' %}", function (data) {
	Highcharts.chart('chart_suku_sexu', {
		chart: { type: data.label.length > 12 ? 'bar' : 'column', styledMode: true },
		title: { text: '' }, legend: { enabled: true },
		xAxis: { categories: data.label },
		yAxis: { title: { text: 'Total Membru' }, tickInterval: 1, allowDecimals: false },
		plotOptions: { column: { borderRadius: 4 }, bar: { borderRadius: 4 } },
		series: [
			{ name: 'Mane', colorIndex: 0, data: data.mane, tooltip: { valueSuffix: ' Mane' } },
			{ name: 'Feto', colorIndex: 1, data: data.feto, tooltip: { valueSuffix: ' Feto' } }
		]
	});
});
