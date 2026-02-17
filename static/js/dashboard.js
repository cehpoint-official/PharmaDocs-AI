// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

// Dashboard utilities and interactions
class DashboardManager {
    constructor() {
        this.init();
    }

    init() {
        this.bindModuleCards();
        this.loadDashboardStats();
        this.initCharts();
    }

    bindModuleCards() {
        // Make module cards clickable
        document.querySelectorAll('.module-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.tagName !== 'A' && e.target.tagName !== 'BUTTON') {
                    const link = card.querySelector('a');
                    if (link) {
                        window.location.href = link.href;
                    }
                }
            });

            // Add hover effects
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });
    }

    async loadDashboardStats() {
        try {
            const response = await fetch('/dashboard/stats');
            if (!response.ok) return;

            const stats = await response.json();
            this.updateStatsDisplay(stats);
            this.updateCharts(stats);

        } catch (error) {
            console.error('Error loading dashboard stats:', error);
        }
    }

    updateStatsDisplay(stats) {
        // Update any real-time stats displays
        const elements = {
            'total-docs': stats.total_documents,
            'completed-docs': stats.completed_documents,
            'draft-docs': stats.draft_documents,
            'recent-docs': stats.recent_documents
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                this.animateNumber(element, value);
            }
        });
    }

    animateNumber(element, targetValue) {
        const currentValue = parseInt(element.textContent) || 0;
        const increment = (targetValue - currentValue) / 20;
        let current = currentValue;

        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= targetValue) ||
                (increment < 0 && current <= targetValue)) {
                current = targetValue;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 50);
    }

    initCharts() {
        // Initialize any charts on the dashboard
        this.initDocumentTypeChart();
        this.initActivityChart();
    }

    initDocumentTypeChart() {
        const canvas = document.getElementById('documentTypeChart');
        if (!canvas) return;

        // Chart will be initialized when data is loaded
        this.documentTypeChart = null;
    }

    initActivityChart() {
        const canvas = document.getElementById('activityChart');
        if (!canvas) return;

        // Chart will be initialized when data is loaded
        this.activityChart = null;
    }

    updateCharts(stats) {
        if (stats.type_distribution) {
            this.updateDocumentTypeChart(stats.type_distribution);
        }
    }

    updateDocumentTypeChart(distribution) {
        const canvas = document.getElementById('documentTypeChart');
        if (!canvas || !window.Chart) return;

        const labels = Object.keys(distribution);
        const data = Object.values(distribution);
        const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1'];

        if (this.documentTypeChart) {
            this.documentTypeChart.destroy();
        }

        this.documentTypeChart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed * 100) / total).toFixed(1);
                                return `${context.label}: ${context.parsed} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Document actions
    async deleteDocument(documentId) {
        if (!confirm('Are you sure you want to delete this document?')) {
            return;
        }

        try {
            const response = await fetch(`/documents/${documentId}/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const result = await response.json();

            if (result.success) {
                // Remove the document row or reload the page
                location.reload();
            } else {
                alert('Error: ' + (result.error || 'Failed to delete document'));
            }
        } catch (error) {
            console.error('Error deleting document:', error);
            alert('Failed to delete document');
        }
    }

    // Quick actions
    showQuickCreate() {
        // Show quick create modal
        const modal = document.getElementById('quickCreateModal');
        if (modal) {
            new bootstrap.Modal(modal).show();
        }
    }

    // Search functionality
    initSearch() {
        const searchInput = document.getElementById('dashboardSearch');
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.performSearch(e.target.value);
            }, 300);
        });
    }

    performSearch(query) {
        if (!query.trim()) {
            this.clearSearch();
            return;
        }

        // Filter visible elements based on search query
        const searchableElements = document.querySelectorAll('[data-searchable]');
        searchableElements.forEach(element => {
            const text = element.textContent.toLowerCase();
            const matches = text.includes(query.toLowerCase());

            const row = element.closest('tr') || element.closest('.card') || element;
            if (matches) {
                row.style.display = '';
                this.highlightSearchTerm(element, query);
            } else {
                row.style.display = 'none';
            }
        });
    }

    clearSearch() {
        // Show all elements and remove highlights
        document.querySelectorAll('[data-searchable]').forEach(element => {
            const row = element.closest('tr') || element.closest('.card') || element;
            row.style.display = '';
            this.removeHighlight(element);
        });
    }

    highlightSearchTerm(element, term) {
        const text = element.textContent;
        const regex = new RegExp(`(${term})`, 'gi');
        const highlightedText = text.replace(regex, '<mark>$1</mark>');
        element.innerHTML = highlightedText;
    }

    removeHighlight(element) {
        const text = element.textContent;
        element.innerHTML = text;
    }

    // Real-time updates
    initRealTimeUpdates() {
        // Poll for updates every 30 seconds
        setInterval(() => {
            this.loadDashboardStats();
        }, 30000);
    }

    // Notification system
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';

        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // Export data
    async exportData(format = 'csv') {
        try {
            const response = await fetch(`/dashboard/export?format=${format}`);

            if (!response.ok) {
                throw new Error('Export failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dashboard_export_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('Failed to export data', 'danger');
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

// Export for global use
window.DashboardManager = DashboardManager;
