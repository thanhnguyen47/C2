let ioChart, cpuChart, ramChart, connChart;

function updateCharts(data) {
    const ctx1 = document.getElementById('ioChart').getContext('2d');
    const ctx2 = document.getElementById('cpuChart').getContext('2d');
    const ctx3 = document.getElementById('ramChart').getContext('2d');
    const ctx4 = document.getElementById('connChart').getContext('2d');

    // Khởi tạo biểu đồ nếu chưa có
    if (!ioChart) {
        ioChart = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: data.timestamps || [],
                datasets: [{ label: 'Bytes/s', data: data.bytes_io || [], borderColor: 'green' }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } else {
        ioChart.data.labels = data.timestamps || [];
        ioChart.data.datasets[0].data = data.bytes_io || [];
        ioChart.update();
    }

    if (!cpuChart) {
        cpuChart = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: data.timestamps || [],
                datasets: [{ label: 'CPU %', data: data.cpu_usage || [], borderColor: 'yellow' }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    } else {
        cpuChart.data.labels = data.timestamps || [];
        cpuChart.data.datasets[0].data = data.cpu_usage || [];
        cpuChart.update();
    }

    if (!ramChart) {
        ramChart = new Chart(ctx3, {
            type: 'line',
            data: {
                labels: data.timestamps || [],
                datasets: [{ label: 'RAM MB', data: data.ram_usage || [], borderColor: 'pink' }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } else {
        ramChart.data.labels = data.timestamps || [];
        ramChart.data.datasets[0].data = data.ram_usage || [];
        ramChart.update();
    }

    if (!connChart) {
        connChart = new Chart(ctx4, {
            type: 'line',
            data: {
                labels: data.timestamps || [],
                datasets: [{ label: 'Connections', data: data.connections || [], borderColor: 'blue' }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } else {
        connChart.data.labels = data.timestamps || [];
        connChart.data.datasets[0].data = data.connections || [];
        connChart.update();
    }
}

function drawStaticCharts(timestamps, bytes_io, cpu_usage, ram_usage, connections) {
    const ctx1 = document.getElementById('ioChart').getContext('2d');
    const ctx2 = document.getElementById('cpuChart').getContext('2d');
    const ctx3 = document.getElementById('ramChart').getContext('2d');
    const ctx4 = document.getElementById('connChart').getContext('2d');

    ioChart = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: timestamps || [],
            datasets: [{ label: 'Bytes/s', data: bytes_io || [], borderColor: 'green' }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    cpuChart = new Chart(ctx2, {
        type: 'line',
        data: {
            labels: timestamps || [],
            datasets: [{ label: 'CPU %', data: cpu_usage || [], borderColor: 'yellow' }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });

    ramChart = new Chart(ctx3, {
        type: 'line',
        data: {
            labels: timestamps || [],
            datasets: [{ label: 'RAM MB', data: ram_usage || [], borderColor: 'pink' }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    connChart = new Chart(ctx4, {
        type: 'line',
        data: {
            labels: timestamps || [],
            datasets: [{ label: 'Connections', data: connections || [], borderColor: 'blue' }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Thêm log để kiểm tra reload
    console.log("Charts initialized");
}

// Kiểm tra reload
window.addEventListener('beforeunload', function() {
    console.log("Page is reloading or closing");
});