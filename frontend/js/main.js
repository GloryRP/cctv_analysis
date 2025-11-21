// ===== CONFIGURATION =====
const API_BASE_URL = 'http://localhost:5000/api';
const REFRESH_INTERVAL = 30000; // 30 sec refresh

// ===== STATE =====
const appState = {
    currentSection: 'dashboard',
    darkMode: localStorage.getItem('darkMode') === 'true',
    alerts: [],
    cameras: [],
    reports: []
};

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', async () => {
    await initializeApp();
    setupEventListeners();
    await loadDashboardData();
    await initializeCharts();
    setupPeriodicRefresh();
});

async function initializeApp() {
    if (appState.darkMode) {
        document.body.classList.add('dark-theme');
        updateThemeIcon();
    }
    updateDateTime();
    setInterval(updateDateTime, 60000);
    registerServiceWorker();
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', handleNavigation);
    });

    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('voiceBtn').addEventListener('click', startVoiceCommand);

    document.getElementById('uploadVideoBtn').addEventListener('click', openUploadModal);
    document.getElementById('closeUploadModal').addEventListener('click', closeUploadModal);
    document.getElementById('browseBtn').addEventListener('click', () =>
        document.getElementById('videoFileInput').click()
    );
    document.getElementById('videoFileInput').addEventListener('change', handleFileUpload);

    const uploadArea = document.getElementById('uploadArea');
    uploadArea.addEventListener('dragover', e => {
        e.preventDefault();
        uploadArea.style.borderColor = 'var(--primary-color)';
    });
    uploadArea.addEventListener('dragleave', () =>
        uploadArea.style.borderColor = 'var(--border-color)'
    );
    uploadArea.addEventListener('drop', handleFileDrop);

    document.getElementById('generateReportBtn').addEventListener('click', openReportGenerator);
    document.getElementById('downloadReportBtn').addEventListener('click', generateReport);
    document.getElementById('alertFilter').addEventListener('change', filterAlerts);
    document.getElementById('viewAllAlerts').addEventListener('click', () =>
        navigateToSection('alerts')
    );
}

// ===== NAVIGATION =====
function handleNavigation(e) {
    e.preventDefault();
    const section = e.currentTarget.dataset.section;
    navigateToSection(section);
}

function navigateToSection(section) {
    document.querySelectorAll('.nav-link').forEach(link =>
        link.classList.remove('active')
    );
    document.querySelector(`[data-section="${section}"]`).classList.add('active');

    document.querySelectorAll('.section').forEach(sec =>
        sec.classList.remove('active')
    );
    document.getElementById(section).classList.add('active');

    appState.currentSection = section;

    if (section === 'cameras') loadCameras();
    if (section === 'alerts') loadAllAlerts();
    if (section === 'reports') loadReports();
}

// ===== THEME =====
function toggleTheme() {
    appState.darkMode = !appState.darkMode;
    document.body.classList.toggle('dark-theme');
    localStorage.setItem('darkMode', appState.darkMode);
    updateThemeIcon();
    updateChartsTheme();
}

function updateThemeIcon() {
    const icon = document.querySelector('#themeToggle i');
    icon.className = appState.darkMode ? 'fas fa-sun' : 'fas fa-moon';
}

// ===== DATE & TIME =====
function updateDateTime() {
    const now = new Date();
    document.getElementById('currentDate').textContent =
        now.toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
}

// ===== DATE PICKER VALIDATION =====
function initializeDatePickers() {
    const startDateInput = document.getElementById('reportStartDate');
    const endDateInput = document.getElementById('reportEndDate');
    
    if (!startDateInput || !endDateInput) return;
    
    // Set max date to today for both inputs
    const today = new Date().toISOString().split('T')[0];
    startDateInput.max = today;
    endDateInput.max = today;
    
    // Set default dates (last 7 days)
    const defaultEndDate = new Date();
    const defaultStartDate = new Date();
    defaultStartDate.setDate(defaultStartDate.getDate() - 7);
    
    startDateInput.value = defaultStartDate.toISOString().split('T')[0];
    endDateInput.value = defaultEndDate.toISOString().split('T')[0];
    
    // Set initial min for end date
    endDateInput.min = startDateInput.value;
    
    // Update end date constraints when start date changes
    startDateInput.addEventListener('change', function() {
        if (startDateInput.value) {
            endDateInput.min = startDateInput.value;
            
            // If end date is now invalid, update it
            if (endDateInput.value && endDateInput.value < startDateInput.value) {
                endDateInput.value = startDateInput.value;
                showNotification('End date adjusted to match start date', 'info');
            }
        }
    });
    
    // Validate end date selection
    endDateInput.addEventListener('change', function() {
        if (startDateInput.value && endDateInput.value < startDateInput.value) {
            showNotification('End date cannot be before start date. Date has been corrected.', 'error');
            endDateInput.value = startDateInput.value;
        }
    });
}

// =====================================================================
// ===================== DASHBOARD (REAL API) ==========================
// =====================================================================
async function loadDashboardData() {
    try {
        showLoadingState('dashboard');
        
        const res = await fetch(`${API_BASE_URL}/dashboard/stats`);
        if (!res.ok) throw new Error('Failed to fetch dashboard stats');
        
        const stats = await res.json();
        updateDashboardStats(stats);
        await loadRecentAlerts();
        await loadHeatmap();

    } catch (error) {
        console.error('Dashboard load error:', error);
        showNotification('Failed to load dashboard data', 'error');
        showErrorState('dashboard');
    }
}

function updateDashboardStats(stats) {
    document.getElementById('activeCameras').textContent = stats.activeCameras || 0;
    document.getElementById('normalEvents').textContent = stats.normalEvents || 0;
    document.getElementById('anomaliesDetected').textContent = stats.anomalies || 0;
    document.getElementById('peopleDetected').textContent = stats.peopleDetected || 0;
    document.getElementById('alertBadge').textContent = stats.anomalies || 0;
}

// ===== LOAD RECENT ALERTS (REAL API) =====
async function loadRecentAlerts() {
    try {
        const res = await fetch(`${API_BASE_URL}/alerts?limit=5`);
        if (!res.ok) throw new Error('Failed to fetch alerts');
        
        const data = await res.json();
        updateRecentAlerts(data.alerts || []);
    } catch (error) {
        console.error('Recent alerts load error:', error);
        updateRecentAlerts([]);
    }
}

function updateRecentAlerts(alerts) {
    const container = document.getElementById('recentAlertsList');

    if (alerts.length === 0) {
        container.innerHTML = '<div class="empty-state">No recent alerts</div>';
        return;
    }

    container.innerHTML = alerts.map(alert => `
        <div class="alert-item ${alert.severity}">
            <div class="alert-content">
                <div class="alert-header">
                    <span class="alert-title">${alert.type}</span>
                    <span class="alert-time">${formatTime(new Date(alert.timestamp))}</span>
                </div>
                <p class="alert-description">${alert.description}</p>
            </div>
        </div>
    `).join('');
}

// =====================================================================
// ======================== CAMERAS (REAL API) =========================
// =====================================================================
async function loadCameras() {
    try {
        showLoadingState('cameras');
        
        const res = await fetch(`${API_BASE_URL}/cameras`);
        if (!res.ok) throw new Error('Failed to fetch cameras');
        
        const data = await res.json();
        updateCamerasGrid(data.cameras || []);

    } catch (error) {
        console.error('Cameras load error:', error);
        showNotification('Failed to load cameras', 'error');
        showErrorState('cameras');
    }
}

function updateCamerasGrid(cameras) {
    const cameraGrid = document.getElementById('cameraGrid');

    if (cameras.length === 0) {
        cameraGrid.innerHTML = '<div class="empty-state">No cameras available</div>';
        return;
    }

    cameraGrid.innerHTML = cameras.map(camera => `
        <div class="camera-card">
            <img src="${API_BASE_URL}/cameras/${camera.id}/snapshot" 
                 onerror="this.src='https://via.placeholder.com/800x450/2a2a2a/fff?text=${encodeURIComponent(camera.name)}'"
                 class="camera-video"
                 alt="${camera.name}">
            <div class="camera-info">
                <div class="camera-header">
                    <span class="camera-name">${camera.name}</span>
                    <div class="camera-status">
                        <span class="status-dot ${camera.status || 'active'}"></span>
                        <span>${camera.status || 'Active'}</span>
                    </div>
                </div>
                <small style="color: var(--text-secondary);">Camera ID: ${camera.id}</small>
            </div>
        </div>
    `).join('');
}

// =====================================================================
// ========================= ALERTS PAGE (REAL API) ====================
// =====================================================================
async function loadAllAlerts() {
    try {
        showLoadingState('alerts');
        
        const res = await fetch(`${API_BASE_URL}/alerts`);
        if (!res.ok) throw new Error('Failed to fetch alerts');
        
        const data = await res.json();
        updateAlertsTimeline(data.alerts || []);

    } catch (error) {
        console.error('Alerts load error:', error);
        showNotification('Failed to load alerts', 'error');
        showErrorState('alerts');
    }
}

function updateAlertsTimeline(alerts) {
    const timeline = document.getElementById('alertsTimeline');

    if (alerts.length === 0) {
        timeline.innerHTML = '<div class="empty-state">No alerts found</div>';
        return;
    }

    timeline.innerHTML = alerts.map(alert => `
        <div class="alert-item ${alert.severity}">
            <div class="alert-content">
                <div class="alert-header">
                    <span class="alert-title">${alert.type}</span>
                    <span class="alert-time">${formatTime(new Date(alert.timestamp))}</span>
                </div>
                <p class="alert-description">${alert.description}</p>
                ${alert.camera_id ? `<small>Camera: ${alert.camera_id}</small>` : ''}
            </div>
        </div>
    `).join('');
}

function filterAlerts() {
    const filter = document.getElementById('alertFilter').value;
    const items = document.querySelectorAll('.alert-item');

    items.forEach(item => {
        item.style.display = (filter === 'all' || item.classList.contains(filter)) ? 'flex' : 'none';
    });
}

// =====================================================================
// ========================= VIDEO UPLOAD (REAL API) ===================
// =====================================================================
async function processVideoFile(file) {
    if (!file.type.startsWith('video/')) {
        showNotification('Please upload a valid video file', 'error');
        return;
    }

    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const uploadStatus = document.getElementById('uploadStatus');
    uploadProgress.style.display = 'block';

    const formData = new FormData();
    formData.append('video', file);
    formData.append('camera_id', 'uploaded');
    formData.append('camera_name', 'Uploaded Video');

    try {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_BASE_URL}/videos/upload`, true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded * 100) / e.total);
                progressFill.style.width = percent + '%';
                uploadStatus.textContent = `Uploading... ${percent}%`;
            }
        };

        xhr.onload = () => {
            if (xhr.status === 200) {
                showNotification('Video uploaded & processing!', 'success');
                // Refresh dashboard to show new data
                if (appState.currentSection === 'dashboard') {
                    loadDashboardData();
                }
            } else {
                showNotification('Upload failed', 'error');
            }
            closeUploadModal();
        };

        xhr.onerror = () => {
            showNotification('Upload error', 'error');
            closeUploadModal();
        };

        xhr.send(formData);
    } catch (error) {
        showNotification('Upload error', 'error');
        closeUploadModal();
    }
}

// =====================================================================
// ======================== REPORTS (REAL API) =========================
// =====================================================================
async function loadReports() {
    const list = document.getElementById('reportsList');

    try {
        showLoadingState('reports');
        
        // Initialize date pickers when reports section loads
        initializeDatePickers();
        
        const res = await fetch(`${API_BASE_URL}/reports`);
        if (!res.ok) throw new Error('Failed to fetch reports');
        
        const data = await res.json();
        updateReportsList(data.reports || []);

    } catch (error) {
        console.error('Reports load error:', error);
        showNotification('Failed to load reports', 'error');
        showErrorState('reports');
    }
}

function updateReportsList(reports) {
    const list = document.getElementById('reportsList');

    if (reports.length === 0) {
        list.innerHTML = '<div class="empty-state">No reports generated yet</div>';
        return;
    }

    list.innerHTML = reports.map(report => `
        <div class="report-item">
            <div class="report-info">
                <h4>${report.filename}</h4>
                <p class="report-meta">${report.start_date} → ${report.end_date}</p>
                <small>Type: ${report.report_type}</small>
            </div>
            <a href="${API_BASE_URL}/reports/${report.id}/download" class="btn-secondary" download>
                <i class="fas fa-download"></i>
            </a>
        </div>
    `).join('');
}

function openReportGenerator() {
    navigateToSection('reports');
    showNotification('Select date range and click Download Report', 'info');
}

async function generateReport() {
    const start = document.getElementById('reportStartDate').value;
    const end = document.getElementById('reportEndDate').value;
    const type = document.getElementById('reportType').value;

    if (!start || !end) {
        showNotification("Select valid date range", "error");
        return;
    }

    // Additional date validation
    if (end < start) {
        showNotification("End date cannot be before start date", "error");
        return;
    }
    
    const today = new Date().toISOString().split('T')[0];
    if (start > today || end > today) {
        showNotification("Cannot select future dates", "error");
        return;
    }

    showNotification('Generating report...', 'info');

    try {
        const res = await fetch(`${API_BASE_URL}/reports/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                start_date: start, 
                end_date: end, 
                report_type: type 
            })
        });

        if (!res.ok) throw new Error('Report generation failed');

        const data = await res.json();
        if (data.success) {
            showNotification('Report generated successfully', 'success');
            await loadReports(); // Refresh reports list
        } else {
            showNotification('Report generation failed', 'error');
        }
    } catch (error) {
        console.error('Report generation error:', error);
        showNotification('Failed to generate report', 'error');
    }
}

// =====================================================================
// ========================= HEATMAP (REAL API) ========================
// =====================================================================
async function loadHeatmap() {
    try {
        const res = await fetch(`${API_BASE_URL}/analytics/heatmap`);
        if (!res.ok) return; // Heatmap is optional, don't throw error
        
        const data = await res.json();
        updateHeatmap(data);
    } catch (error) {
        console.error('Heatmap load error:', error);
        // Heatmap is non-critical, so don't show error
    }
}

function updateHeatmap(data) {
    const canvas = document.getElementById('heatmapCanvas');
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;

    canvas.width = container.offsetWidth;
    canvas.height = container.offsetHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Only draw if we have real data
    if (data && data.points && data.points.length > 0) {
        data.points.forEach(point => {
            const x = point.x * canvas.width;
            const y = point.y * canvas.height;
            const radius = point.radius || 40;
            const intensity = point.intensity || 0.5;
            const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
            gradient.addColorStop(0, `rgba(255, 59, 48, ${intensity})`);
            gradient.addColorStop(1, 'rgba(255, 59, 48, 0)');
            ctx.fillStyle = gradient;
            ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
        });
    }
}

// =====================================================================
// ========================= UTILITIES =================================
// =====================================================================
function openUploadModal() {
    document.getElementById('uploadModal').classList.add('active');
}

function closeUploadModal() {
    document.getElementById('uploadModal').classList.remove('active');
    document.getElementById('uploadProgress').style.display = 'none';
    document.getElementById('videoFileInput').value = '';
}

function handleFileDrop(e) {
    e.preventDefault();
    document.getElementById('uploadArea').style.borderColor = 'var(--border-color)';
    processVideoFile(e.dataTransfer.files[0]);
}

function handleFileUpload(e) {
    processVideoFile(e.target.files[0]);
}

function formatTime(date) {
    const now = new Date();
    const diff = (now - date) / 60000;
    if (diff < 1) return 'Just now';
    if (diff < 60) return `${Math.floor(diff)}m ago`;
    if (diff < 1440) return `${Math.floor(diff/60)}h ago`;
    return date.toLocaleDateString();
}

function showNotification(message, type = 'info') {
    const el = document.createElement('div');
    el.className = `notification ${type}`;
    el.textContent = message;
    el.style.cssText = `
        position:fixed;top:80px;right:20px;padding:14px 18px;
        background:var(--bg-primary);box-shadow:var(--shadow-lg);
        border-left:4px solid ${
            type === 'error' ? 'var(--danger-color)' :
            type === 'success' ? 'var(--secondary-color)' :
            'var(--primary-color)'
        };
        border-radius:var(--radius-md);z-index:3000;
        animation:slideIn 0.3s;
    `;
    document.body.appendChild(el);
    setTimeout(() => { 
        el.style.animation='slideOut .3s'; 
        setTimeout(()=>el.remove(),300) 
    }, 3000);
}

function showLoadingState(section) {
    const containers = {
        dashboard: ['recentAlertsList'],
        cameras: ['cameraGrid'],
        alerts: ['alertsTimeline'],
        reports: ['reportsList']
    };

    containers[section]?.forEach(containerId => {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '<div class="loading-state">Loading...</div>';
        }
    });
}

function showErrorState(section) {
    const containers = {
        dashboard: ['recentAlertsList'],
        cameras: ['cameraGrid'],
        alerts: ['alertsTimeline'],
        reports: ['reportsList']
    };

    containers[section]?.forEach(containerId => {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '<div class="error-state">Failed to load data</div>';
        }
    });
}

function setupPeriodicRefresh() {
    setInterval(() => {
        if (appState.currentSection === 'dashboard') {
            loadDashboardData();
            refreshCharts();
        }
    }, REFRESH_INTERVAL);
}

function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/service-worker.js')
            .catch(err => console.log('SW registration failed:', err));
    }
}

// Make functions available globally
window.navigateToSection = navigateToSection;
window.openUploadModal = openUploadModal;
window.closeUploadModal = closeUploadModal;