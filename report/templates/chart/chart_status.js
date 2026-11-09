drawChart('chart_status', "{% url 'api-status' %}", { type: 'pie', name: 'Status', colorIndex: { 'Ativu': 2, 'Inativu': 1, 'Falesidu': 9 } });
