document.addEventListener("DOMContentLoaded", function() {
    function isEmpty(obj) { return Object.keys(obj).length === 0; }

    // CATEGORY PIE CHART
    const ctx1 = document.getElementById('categoryChart').getContext('2d');
    if (isEmpty(categoryData)) {
        ctx1.font = "16px Arial";
        ctx1.fillText("No data to display", 50, 50);
    } else {
        new Chart(ctx1, {
            type: 'pie',
            data: {
                labels: Object.keys(categoryData),
                datasets: [{
                    data: Object.values(categoryData),
                    backgroundColor: ['#5A31F4','#34C759','#FF9F0A','#FF375F','#64D2FF','#AF52DE'],
                    borderWidth: 1
                }]
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
        });
    }

    // MONTH BAR CHART
    const ctx2 = document.getElementById('monthChart').getContext('2d');
    if (isEmpty(monthData)) {
        ctx2.font = "16px Arial";
        ctx2.fillText("No data to display", 50, 50);
    } else {
        new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: Object.keys(monthData),
                datasets: [{
                    label: 'Amount (₹)',
                    data: Object.values(monthData),
                    backgroundColor: '#5A31F4'
                }]
            },
            options: { responsive: true, scales: { y: { beginAtZero: true } } }
        });
    }
});
