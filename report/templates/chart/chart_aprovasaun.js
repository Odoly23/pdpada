drawChart('chart_aprovasaun', "{% url 'api-aprovasaun' %}", { type: 'pie', name: 'Aprovasaun', colorIndex: { 'Pendente': 1, 'Aprovadu': 2, 'Rejeitadu': 3 } });
