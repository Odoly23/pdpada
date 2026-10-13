// Opsi bersama grafik Chart.js (home). Chart.js dimuat lokal dari js_custom/Chart.min.js
var PD_COLORS = ['#0b1e8a', '#f0ad00', '#1a8a3c', '#c0392b', '#6f7fd6', '#0b7285', '#6f42c1', '#fd7e14', '#20c997', '#adb5bd'];
Chart.defaults.global.defaultFontFamily = "'Segoe UI', Tahoma, sans-serif";
Chart.defaults.global.defaultFontSize = 11;

var pdPieOptions = {
	responsive: true, maintainAspectRatio: false,
	legend: { position: 'right', labels: { boxWidth: 12 } },
};
var pdBarOptions = {
	responsive: true, maintainAspectRatio: false,
	legend: { display: false },
	scales: {
		yAxes: [{ ticks: { beginAtZero: true, precision: 0 } }],
		xAxes: [{ gridLines: { display: false } }]
	}
};

// type: 'doughnut' | 'pie' | 'bar'; colorFor: {label: warna} (opsional untuk pie/doughnut)
function pdChart(canvasId, endpoint, type, title, colorFor) {
	$.ajax({
		method: "GET",
		url: endpoint,
		success: function (data) {
			var round = (type === 'doughnut' || type === 'pie');
			var colors = round
				? data.label.map(function (l, i) { return (colorFor && colorFor[l]) || PD_COLORS[i % PD_COLORS.length]; })
				: PD_COLORS[0];
			new Chart(document.getElementById(canvasId).getContext('2d'), {
				type: type,
				data: {
					labels: data.label,
					datasets: [{ label: title, data: data.obj, backgroundColor: colors, borderWidth: round ? 1 : 0 }]
				},
				options: round ? pdPieOptions : pdBarOptions
			});
		},
		error: function (error_data) {
			console.log("error");
			console.log(error_data);
		}
	});
}
