document.addEventListener("DOMContentLoaded", function() {
    // Get currency symbol from meta tag or use default
    const currency = document.querySelector('meta[name="currency"]')?.getAttribute('content') || '₹';
    
    function isEmpty(obj) { 
        return Object.keys(obj).length === 0; 
    }

    // Category Pie Chart
    const ctx1 = document.getElementById('categoryChart');
    if (ctx1) {
        if (isEmpty(categoryData)) {
            ctx1.getContext('2d').font = "16px 'Segoe UI', Arial, sans-serif";
            ctx1.getContext('2d').fillStyle = "#ffffff";
            ctx1.getContext('2d').textAlign = "center";
            ctx1.getContext('2d').fillText("No data to display", ctx1.width / 2, ctx1.height / 2);
        } else {
            new Chart(ctx1, {
                type: 'pie',
                data: {
                    labels: Object.keys(categoryData),
                    datasets: [{
                        data: Object.values(categoryData),
                        backgroundColor: [
                            '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', 
                            '#14b8a6', '#ec4899', '#f97316', '#84cc16', '#06b6d4'
                        ],
                        borderColor: '#1e293b',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { 
                            position: 'bottom', 
                            labels: { 
                                color: '#f1f5f9', 
                                font: { size: 12 },
                                padding: 20
                            } 
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    return `${label}: ${currency}${value.toFixed(2)}`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    // Monthly Trend Line Chart
    const ctx2 = document.getElementById('monthChart');
    if (ctx2) {
        if (isEmpty(monthData)) {
            ctx2.getContext('2d').font = "16px 'Segoe UI', Arial, sans-serif";
            ctx2.getContext('2d').fillStyle = "#ffffff";
            ctx2.getContext('2d').textAlign = "center";
            ctx2.getContext('2d').fillText("No data to display", ctx2.width / 2, ctx2.height / 2);
        } else {
            new Chart(ctx2, {
                type: 'line',
                data: {
                    labels: Object.keys(monthData),
                    datasets: [{
                        label: `Monthly Spending (${currency})`,
                        data: Object.values(monthData),
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#3b82f6',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { 
                            labels: { 
                                color: '#f1f5f9',
                                font: { size: 12 }
                            } 
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${currency}${context.raw.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { 
                                display: true, 
                                text: `Amount (${currency})`, 
                                color: '#f1f5f9' 
                            },
                            grid: { 
                                color: 'rgba(255, 255, 255, 0.1)' 
                            },
                            ticks: { 
                                color: '#94a3b8',
                                callback: function(value) {
                                    return currency + value;
                                }
                            }
                        },
                        x: {
                            title: { 
                                display: true, 
                                text: 'Month', 
                                color: '#f1f5f9' 
                            },
                            grid: { 
                                color: 'rgba(255, 255, 255, 0.1)' 
                            },
                            ticks: { 
                                color: '#94a3b8' 
                            }
                        }
                    }
                }
            });
        }
    }

    // Payment Methods Chart
    const ctx3 = document.getElementById('paymentChart');
    if (ctx3) {
        new Chart(ctx3, {
            type: 'doughnut',
            data: {
                labels: Object.keys(paymentData).map(key => 
                    key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' ')
                ),
                datasets: [{
                    data: Object.values(paymentData),
                    backgroundColor: [
                        '#10b981', '#6366f1', '#f59e0b', '#ec4899', '#8b5cf6'
                    ],
                    borderColor: '#1e293b',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#f1f5f9',
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${currency}${context.raw.toFixed(2)}`;
                            }
                        }
                    }
                }
            }
        });
    }
});