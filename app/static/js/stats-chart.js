/**
 * Stats Chart - Real-time performance metrics charts
 *
 * Uses Chart.js for rendering inference latency and FPS history.
 */

// Chart configuration
const CHART_MAX_POINTS = 60;
const CHART_UPDATE_INTERVAL = 1000; // ms

// Chart color scheme (dark theme)
const CHART_COLORS = {
    primary: '#6366f1',
    secondary: '#22d3ee',
    warning: '#f59e0b',
    danger: '#ef4444',
    grid: '#374151',
    text: '#9ca3af',
};

// --- Latency Chart ---
let latencyChart = null;
const latencyData = {
    labels: [],
    datasets: [{
        label: 'Inference (ms)',
        data: [],
        borderColor: CHART_COLORS.primary,
        backgroundColor: CHART_COLORS.primary + '20',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
    }, {
        label: 'Total (ms)',
        data: [],
        borderColor: CHART_COLORS.secondary,
        backgroundColor: 'transparent',
        borderDash: [5, 5],
        tension: 0.3,
        pointRadius: 0,
    }],
};

function initLatencyChart() {
    const canvas = document.getElementById('latency-chart');
    if (!canvas) return;

    latencyChart = new Chart(canvas, {
        type: 'line',
        data: latencyData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: {
                legend: {
                    labels: { color: CHART_COLORS.text, font: { size: 11 } },
                },
            },
            scales: {
                x: {
                    display: false,
                },
                y: {
                    beginAtZero: true,
                    grid: { color: CHART_COLORS.grid },
                    ticks: {
                        color: CHART_COLORS.text,
                        callback: (v) => v + 'ms',
                    },
                },
            },
        },
    });
}

// --- FPS Chart ---
let fpsChart = null;
const fpsData = {
    labels: [],
    datasets: [{
        label: 'FPS',
        data: [],
        borderColor: CHART_COLORS.secondary,
        backgroundColor: CHART_COLORS.secondary + '20',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
    }],
};

function initFPSChart() {
    const canvas = document.getElementById('fps-chart');
    if (!canvas) return;

    fpsChart = new Chart(canvas, {
        type: 'line',
        data: fpsData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: {
                legend: {
                    labels: { color: CHART_COLORS.text, font: { size: 11 } },
                },
            },
            scales: {
                x: {
                    display: false,
                },
                y: {
                    beginAtZero: true,
                    grid: { color: CHART_COLORS.grid },
                    ticks: {
                        color: CHART_COLORS.text,
                    },
                },
            },
        },
    });
}

// --- Data Update ---
function updateCharts(inferenceMs, totalMs, fps) {
    const now = new Date().toLocaleTimeString();

    // Update latency chart
    if (latencyChart) {
        latencyData.labels.push(now);
        latencyData.datasets[0].data.push(inferenceMs);
        latencyData.datasets[1].data.push(totalMs);

        if (latencyData.labels.length > CHART_MAX_POINTS) {
            latencyData.labels.shift();
            latencyData.datasets[0].data.shift();
            latencyData.datasets[1].data.shift();
        }

        latencyChart.update('none');
    }

    // Update FPS chart
    if (fpsChart) {
        fpsData.labels.push(now);
        fpsData.datasets[0].data.push(fps);

        if (fpsData.labels.length > CHART_MAX_POINTS) {
            fpsData.labels.shift();
            fpsData.datasets[0].data.shift();
        }

        fpsChart.update('none');
    }
}

// --- Polling for stats ---
async function pollStats() {
    try {
        const response = await fetch('/api/system/status');
        if (response.ok) {
            const data = await response.json();

            // Update status cards
            const cpuCard = document.getElementById('cpu-card');
            if (cpuCard) {
                cpuCard.innerHTML = `
                    <p class="text-sm text-gray-400">CPU Usage</p>
                    <p class="text-2xl font-bold text-white mt-1">${data.cpu.usage_percent.toFixed(0)}%</p>
                    <p class="text-xs text-gray-500">${data.cpu.frequency_mhz} MHz</p>
                `;
            }

            const npuCard = document.getElementById('npu-card');
            if (npuCard) {
                npuCard.innerHTML = `
                    <p class="text-sm text-gray-400">NPU Usage</p>
                    <p class="text-2xl font-bold text-white mt-1">${data.npu.available ? data.npu.usage_percent.toFixed(0) + '%' : 'N/A'}</p>
                    <p class="text-xs text-gray-500">${data.npu.available ? data.npu.core_count + ' cores' : 'Not detected'}</p>
                `;
            }

            const memCard = document.getElementById('mem-card');
            if (memCard) {
                memCard.innerHTML = `
                    <p class="text-sm text-gray-400">Memory</p>
                    <p class="text-2xl font-bold text-white mt-1">${data.memory.usage_percent.toFixed(0)}%</p>
                    <p class="text-xs text-gray-500">${data.memory.used_mb.toFixed(0)}MB / ${data.memory.total_mb.toFixed(0)}MB</p>
                `;
            }

            const tempCard = document.getElementById('temp-card');
            if (tempCard) {
                const tempClass = data.temperature.cpu_temp > 75 ? 'text-red-400' :
                                  data.temperature.cpu_temp > 60 ? 'text-yellow-400' : 'text-white';
                tempCard.innerHTML = `
                    <p class="text-sm text-gray-400">Temperature</p>
                    <p class="text-2xl font-bold ${tempClass} mt-1">${data.temperature.cpu_temp.toFixed(0)}&deg;C</p>
                    <p class="text-xs text-gray-500">CPU temp</p>
                `;
            }
        }
    } catch (e) {
        // Silently handle fetch errors
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initLatencyChart();
    initFPSChart();

    // Start polling
    setInterval(pollStats, 3000);
    pollStats();
});
