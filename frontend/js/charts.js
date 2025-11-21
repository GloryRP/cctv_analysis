// ===== CHART CONFIGURATION =====
let activityChart = null;
let eventChart = null;

// ===== INITIALIZE CHARTS WITH REAL DATA =====
async function initializeCharts() {
    await createActivityChart();
    await createEventChart();
    
    // Update charts when theme changes
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class') {
                updateChartsTheme();
            }
        });
    });
    
    observer.observe(document.body, { attributes: true });
}

// ===== ACTIVITY TIMELINE CHART WITH REAL DATA =====
async function createActivityChart() {
    const ctx = document.getElementById('activityChart').getContext('2d');
    
    try {
        // Fetch real activity data from backend
        const response = await fetch(`${API_BASE_URL}/analytics/activity`);
        if (!response.ok) throw new Error('Failed to fetch activity data');
        
        const activityData = await response.json();
        
        const labels = activityData.hours || generateDefaultHours();
        const motionData = activityData.motion_events || Array(24).fill(0);
        const anomalyData = activityData.anomalies || Array(24).fill(0);
        
        renderActivityChart(ctx, labels, motionData, anomalyData);
        
    } catch (error) {
        console.error('Failed to load activity chart data:', error);
        // Fallback: show empty chart
        createEmptyActivityChart(ctx);
    }
}

function generateDefaultHours() {
    const hours = [];
    for (let i = 0; i < 24; i++) {
        hours.push(`${i}:00`);
    }
    return hours;
}

function renderActivityChart(ctx, labels, motionData, anomalyData) {
    const isDark = document.body.classList.contains('dark-theme');
    const textColor = isDark ? '#e8eaed' : '#202124';
    const gridColor = isDark ? '#3c4043' : '#dadce0';
    
    activityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Motion Events',
                    data: motionData,
                    borderColor: '#1a73e8',
                    backgroundColor: 'rgba(26, 115, 232, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    borderWidth: 2
                },
                {
                    label: 'Anomalies',
                    data: anomalyData,
                    borderColor: '#ea4335',
                    backgroundColor: 'rgba(234, 67, 53, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: textColor,
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12,
                            family: 'Inter'
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: isDark ? '#2a2a2a' : '#ffffff',
                    titleColor: textColor,
                    bodyColor: textColor,
                    borderColor: gridColor,
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y + ' events';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: textColor,
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 12
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: textColor,
                        callback: function(value) {
                            return Number.isInteger(value) ? value : '';
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// ===== EVENT DISTRIBUTION CHART WITH REAL DATA =====
async function createEventChart() {
    const ctx = document.getElementById('eventChart').getContext('2d');
    
    try {
        // Fetch real event distribution data from backend
        const response = await fetch(`${API_BASE_URL}/analytics/events`);
        if (!response.ok) throw new Error('Failed to fetch event data');
        
        const eventData = await response.json();
        
        const eventTypes = eventData.labels || ['No Data Available'];
        const eventCounts = eventData.counts || [1];
        
        renderEventChart(ctx, eventTypes, eventCounts);
        
    } catch (error) {
        console.error('Failed to load event chart data:', error);
        // Fallback: show empty chart
        createEmptyEventChart(ctx);
    }
}

function renderEventChart(ctx, eventTypes, eventCounts) {
    const isDark = document.body.classList.contains('dark-theme');
    const textColor = isDark ? '#e8eaed' : '#202124';
    
    eventChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: eventTypes,
            datasets: [{
                data: eventCounts,
                backgroundColor: [
                    'rgba(52, 168, 83, 0.8)',   // Green - Normal
                    'rgba(26, 115, 232, 0.8)',  // Blue - Motion
                    'rgba(66, 133, 244, 0.8)',  // Light Blue - Person
                    'rgba(251, 188, 4, 0.8)',   // Yellow - Loitering
                    'rgba(234, 67, 53, 0.8)',   // Red - Intrusion
                    'rgba(158, 158, 158, 0.8)'  // Gray - Other
                ],
                borderColor: [
                    'rgba(52, 168, 83, 1)',
                    'rgba(26, 115, 232, 1)',
                    'rgba(66, 133, 244, 1)',
                    'rgba(251, 188, 4, 1)',
                    'rgba(234, 67, 53, 1)',
                    'rgba(158, 158, 158, 1)'
                ],
                borderWidth: 2,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.5,
            plugins: {
                legend: {
                    display: true,
                    position: 'right',
                    labels: {
                        color: textColor,
                        padding: 15,
                        font: {
                            size: 12,
                            family: 'Inter'
                        },
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                return data.labels.map((label, i) => {
                                    const value = data.datasets[0].data[i];
                                    const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                    return {
                                        text: `${label} (${percentage}%)`,
                                        fillStyle: data.datasets[0].backgroundColor[i],
                                        hidden: false,
                                        index: i
                                    };
                                });
                            }
                            return [];
                        }
                    }
                },
                tooltip: {
                    backgroundColor: isDark ? '#2a2a2a' : '#ffffff',
                    titleColor: textColor,
                    bodyColor: textColor,
                    borderColor: isDark ? '#3c4043' : '#dadce0',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${label}: ${value} events (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '65%',
            animation: {
                animateRotate: true,
                animateScale: true
            }
        }
    });
}

// ===== FALLBACK EMPTY CHARTS =====
function createEmptyActivityChart(ctx) {
    const isDark = document.body.classList.contains('dark-theme');
    const textColor = isDark ? '#e8eaed' : '#202124';
    const gridColor = isDark ? '#3c4043' : '#dadce0';
    
    activityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: generateDefaultHours(),
            datasets: [
                {
                    label: 'Motion Events',
                    data: Array(24).fill(0),
                    borderColor: '#1a73e8',
                    backgroundColor: 'rgba(26, 115, 232, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0
                },
                {
                    label: 'Anomalies',
                    data: Array(24).fill(0),
                    borderColor: '#ea4335',
                    backgroundColor: 'rgba(234, 67, 53, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: textColor }
                },
                tooltip: {
                    backgroundColor: isDark ? '#2a2a2a' : '#ffffff',
                    titleColor: textColor,
                    bodyColor: textColor
                }
            },
            scales: {
                x: { 
                    grid: { color: gridColor },
                    ticks: { color: textColor } 
                },
                y: { 
                    grid: { color: gridColor },
                    ticks: { color: textColor } 
                }
            }
        }
    });
}

function createEmptyEventChart(ctx) {
    const isDark = document.body.classList.contains('dark-theme');
    const textColor = isDark ? '#e8eaed' : '#202124';
    
    eventChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['No Data'],
            datasets: [{
                data: [1],
                backgroundColor: ['rgba(158, 158, 158, 0.8)'],
                borderColor: ['rgba(158, 158, 158, 1)'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: textColor }
                },
                tooltip: {
                    backgroundColor: isDark ? '#2a2a2a' : '#ffffff',
                    titleColor: textColor,
                    bodyColor: textColor
                }
            }
        }
    });
}

// ===== UPDATE CHARTS THEME =====
function updateChartsTheme() {
    const isDark = document.body.classList.contains('dark-theme');
    const textColor = isDark ? '#e8eaed' : '#202124';
    const gridColor = isDark ? '#3c4043' : '#dadce0';
    
    if (activityChart) {
        activityChart.options.plugins.legend.labels.color = textColor;
        activityChart.options.plugins.tooltip.backgroundColor = isDark ? '#2a2a2a' : '#ffffff';
        activityChart.options.plugins.tooltip.titleColor = textColor;
        activityChart.options.plugins.tooltip.bodyColor = textColor;
        activityChart.options.plugins.tooltip.borderColor = gridColor;
        activityChart.options.scales.x.grid.color = gridColor;
        activityChart.options.scales.x.ticks.color = textColor;
        activityChart.options.scales.y.grid.color = gridColor;
        activityChart.options.scales.y.ticks.color = textColor;
        activityChart.update('none');
    }
    
    if (eventChart) {
        eventChart.options.plugins.legend.labels.color = textColor;
        eventChart.options.plugins.tooltip.backgroundColor = isDark ? '#2a2a2a' : '#ffffff';
        eventChart.options.plugins.tooltip.titleColor = textColor;
        eventChart.options.plugins.tooltip.bodyColor = textColor;
        eventChart.options.plugins.tooltip.borderColor = gridColor;
        eventChart.update('none');
    }
}

// ===== REFRESH CHART DATA =====
async function refreshCharts() {
    if (activityChart) {
        activityChart.destroy();
        activityChart = null;
    }
    if (eventChart) {
        eventChart.destroy();
        eventChart = null;
    }
    await initializeCharts();
}

// Export for use in other files
window.refreshCharts = refreshCharts;
window.updateChartsTheme = updateChartsTheme;