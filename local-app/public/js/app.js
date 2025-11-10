// API Base URL
const API_BASE = '';

// Global data storage
let allData = [];
let tags = [];
let detections = [];

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    await loadAllData();
    renderOverview();
    renderTags();
    renderDetections();
    
    // Hide loading spinner
    document.getElementById('loadingSpinner').style.display = 'none';
    
    // Show sections
    document.getElementById('overview').style.display = 'block';
    document.getElementById('tags').style.display = 'block';
    document.getElementById('detections').style.display = 'block';
});

// Load all data from API
async function loadAllData() {
    try {
        const response = await fetch(`${API_BASE}/api/all-data`);
        if (!response.ok) throw new Error('Failed to fetch data');
        allData = await response.json();
        
        tags = allData;
        detections = allData.filter(item => item.detection !== null).map(item => item.detection);
        
        console.log('Data loaded:', { tags: tags.length, detections: detections.length });
    } catch (error) {
        console.error('Error loading data:', error);
        showError('Failed to load data. Make sure the server is running.');
    }
}

// Render overview statistics
function renderOverview() {
    const totalTags = tags.length;
    const totalPhotos = detections.reduce((sum, d) => sum + (d.photos_processed || 0), 0);
    const totalDetections = detections.reduce((sum, d) => sum + (d.total_detections || 0), 0);
    
    // Get unique objects across all detections
    const allObjects = new Set();
    detections.forEach(d => {
        if (d.detected_objects) {
            d.detected_objects.forEach(obj => allObjects.add(obj));
        }
    });
    const uniqueObjects = allObjects.size;
    
    document.getElementById('totalTags').textContent = totalTags;
    document.getElementById('totalPhotos').textContent = totalPhotos;
    document.getElementById('totalDetections').textContent = totalDetections;
    document.getElementById('uniqueObjects').textContent = uniqueObjects;
}

// Render tags
function renderTags() {
    const container = document.getElementById('tagsContainer');
    container.innerHTML = '';
    
    if (tags.length === 0) {
        container.innerHTML = '<div class="col-12"><p class="text-muted text-center">No tags found.</p></div>';
        return;
    }
    
    tags.forEach(tag => {
        const tagCard = createTagCard(tag);
        container.appendChild(tagCard);
    });
}

// Create tag card element
function createTagCard(tag) {
    const col = document.createElement('div');
    col.className = 'col-md-6 col-lg-4 fade-in';
    
    const hasDetection = tag.detection !== null;
    const photoCount = tag.photos ? tag.photos.length : 0;
    const detectionCount = hasDetection ? tag.detection.total_detections : 0;
    
    col.innerHTML = `
        <div class="tag-card" onclick="showTagDetails('${tag.id}')">
            <div class="tag-card-header">
                <h5 class="mb-0">
                    <i class="bi bi-geo-alt-fill me-2"></i>
                    ${escapeHtml(tag.title || 'Untitled Tag')}
                </h5>
            </div>
            <div class="tag-card-body">
                <p class="text-muted mb-2">${escapeHtml(tag.description || 'No description')}</p>
                <div class="tag-coords">
                    <i class="bi bi-geo me-1"></i>
                    (${tag.coords[0].toFixed(2)}, ${tag.coords[1].toFixed(2)}, ${tag.coords[2].toFixed(2)})
                </div>
                <div class="mt-3">
                    ${photoCount > 0 ? `<span class="tag-badge bg-info"><i class="bi bi-camera me-1"></i>${photoCount} Photo(s)</span>` : ''}
                    ${hasDetection ? `<span class="tag-badge bg-success"><i class="bi bi-check-circle me-1"></i>Processed</span>` : '<span class="tag-badge bg-secondary">Not Processed</span>'}
                    ${detectionCount > 0 ? `<span class="tag-badge bg-warning"><i class="bi bi-bullseye me-1"></i>${detectionCount} Detection(s)</span>` : ''}
                </div>
            </div>
        </div>
    `;
    
    return col;
}

// Render detections
function renderDetections() {
    const container = document.getElementById('detectionsContainer');
    container.innerHTML = '';
    
    if (detections.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No detections found.</p>';
        return;
    }
    
    detections.forEach(detection => {
        const detectionCard = createDetectionCard(detection);
        container.appendChild(detectionCard);
    });
}

// Create detection card element
function createDetectionCard(detection) {
    const card = document.createElement('div');
    card.className = 'detection-card fade-in';
    
    const uniqueObjects = detection.detected_objects || [];
    const imageDetections = detection.image_detections || [];
    
    let imagesHtml = '';
    if (imageDetections.length > 0) {
        imagesHtml = '<div class="image-gallery">';
        imageDetections.forEach(imgDet => {
            const imagePath = imgDet.image_path.replace(/\\/g, '/');
            const annotatedPath = imgDet.annotated_image_path ? imgDet.annotated_image_path.replace(/\\/g, '/') : null;
            const imageName = imagePath.split(/[/\\]/).pop();
            
            imagesHtml += `
                <div class="image-card">
                    <img src="/${imagePath}" alt="Original" class="img-fluid" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'400\' height=\'300\'%3E%3Crect fill=\'%23ddd\' width=\'400\' height=\'300\'/%3E%3Ctext fill=\'%23999\' font-family=\'sans-serif\' font-size=\'18\' x=\'50%25\' y=\'50%25\' text-anchor=\'middle\' dy=\'.3em\'%3EImage not found%3C/text%3E%3C/svg%3E';">
                    <div class="image-card-body">
                        <div class="image-card-title">${escapeHtml(imageName)}</div>
                        <p class="text-muted small mb-2">${imgDet.detection_count || 0} object(s) detected</p>
                        ${annotatedPath ? `<a href="/${annotatedPath}" target="_blank" class="btn btn-sm btn-primary"><i class="bi bi-eye me-1"></i>View Annotated</a>` : ''}
                    </div>
                </div>
            `;
            
            if (annotatedPath) {
                imagesHtml += `
                    <div class="image-card">
                        <img src="/${annotatedPath}" alt="Annotated" class="img-fluid" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'400\' height=\'300\'%3E%3Crect fill=\'%23ddd\' width=\'400\' height=\'300\'/%3E%3Ctext fill=\'%23999\' font-family=\'sans-serif\' font-size=\'18\' x=\'50%25\' y=\'50%25\' text-anchor=\'middle\' dy=\'.3em\'%3EImage not found%3C/text%3E%3C/svg%3E';">
                        <div class="image-card-body">
                            <div class="image-card-title">Annotated Version</div>
                            <p class="text-muted small mb-2">With bounding boxes</p>
                        </div>
                    </div>
                `;
            }
        });
        imagesHtml += '</div>';
    }
    
    let detectionsListHtml = '';
    if (imageDetections.length > 0) {
        detectionsListHtml = '<h6 class="mt-3 mb-2"><i class="bi bi-list-ul me-2"></i>Detected Objects:</h6><ul class="detection-list">';
        imageDetections.forEach(imgDet => {
            imgDet.detections.forEach(det => {
                detectionsListHtml += `
                    <li class="detection-item">
                        <div class="detection-item-label">
                            <i class="bi bi-check-circle-fill text-success me-2"></i>
                            ${escapeHtml(det.label)}
                        </div>
                        <div class="detection-item-box">
                            Box: [${det.box_2d_absolute.join(', ')}] | Confidence: ${(det.confidence * 100).toFixed(1)}%
                        </div>
                    </li>
                `;
            });
        });
        detectionsListHtml += '</ul>';
    }
    
    card.innerHTML = `
        <div class="detection-header">
            <h5 class="mb-0">
                <i class="bi bi-tag-fill me-2"></i>
                ${escapeHtml(detection.tag_title || 'Unknown Tag')}
            </h5>
            <small class="opacity-75">ID: ${detection.tag_id}</small>
        </div>
        <div class="detection-body">
            <div class="detection-stats">
                <div class="detection-stat">
                    <div class="detection-stat-value">${detection.photos_processed || 0}</div>
                    <div class="detection-stat-label">Photos Processed</div>
                </div>
                <div class="detection-stat">
                    <div class="detection-stat-value">${detection.total_detections || 0}</div>
                    <div class="detection-stat-label">Total Detections</div>
                </div>
                <div class="detection-stat">
                    <div class="detection-stat-value">${uniqueObjects.length}</div>
                    <div class="detection-stat-label">Unique Object Types</div>
                </div>
            </div>
            
            <div class="mb-3">
                <h6><i class="bi bi-geo-alt me-2"></i>Location:</h6>
                <code class="bg-light p-2 rounded d-inline-block">
                    (${detection.tag_coords[0].toFixed(2)}, ${detection.tag_coords[1].toFixed(2)}, ${detection.tag_coords[2].toFixed(2)})
                </code>
            </div>
            
            ${uniqueObjects.length > 0 ? `
                <div class="mb-3">
                    <h6><i class="bi bi-box-seam me-2"></i>Detected Object Types:</h6>
                    ${uniqueObjects.map(obj => `<span class="object-badge">${escapeHtml(obj)}</span>`).join('')}
                </div>
            ` : ''}
            
            ${imagesHtml}
            ${detectionsListHtml}
            
            ${detection.summary ? `
                <div class="mt-4">
                    <h6><i class="bi bi-file-text me-2"></i>Summary:</h6>
                    <div class="summary-box">${escapeHtml(detection.summary)}</div>
                </div>
            ` : ''}
        </div>
    `;
    
    return card;
}

// Show tag details in modal
async function showTagDetails(tagId) {
    const tag = tags.find(t => t.id === tagId);
    if (!tag) return;
    
    const modal = new bootstrap.Modal(document.getElementById('tagDetailModal'));
    const modalTitle = document.getElementById('tagDetailTitle');
    const modalBody = document.getElementById('tagDetailBody');
    
    modalTitle.textContent = tag.title || 'Tag Details';
    
    let detectionHtml = '';
    if (tag.detection) {
        const det = tag.detection;
        detectionHtml = `
            <div class="alert alert-success">
                <h6><i class="bi bi-check-circle me-2"></i>Detection Data Available</h6>
                <p class="mb-1"><strong>Photos Processed:</strong> ${det.photos_processed}</p>
                <p class="mb-1"><strong>Total Detections:</strong> ${det.total_detections}</p>
                <p class="mb-0"><strong>Unique Objects:</strong> ${(det.detected_objects || []).length}</p>
            </div>
        `;
    } else {
        detectionHtml = '<div class="alert alert-warning">No detection data available for this tag.</div>';
    }
    
    modalBody.innerHTML = `
        <div class="mb-3">
            <h6><i class="bi bi-info-circle me-2"></i>Description</h6>
            <p>${escapeHtml(tag.description || 'No description')}</p>
        </div>
        
        <div class="mb-3">
            <h6><i class="bi bi-geo-alt me-2"></i>Coordinates</h6>
            <code class="bg-light p-2 rounded d-inline-block">
                X: ${tag.coords[0].toFixed(4)}, Y: ${tag.coords[1].toFixed(4)}, Z: ${tag.coords[2].toFixed(4)}
            </code>
        </div>
        
        <div class="mb-3">
            <h6><i class="bi bi-camera me-2"></i>Photos</h6>
            ${tag.photos && tag.photos.length > 0 ? `
                <p>${tag.photos.length} photo(s) associated with this tag.</p>
            ` : '<p class="text-muted">No photos associated with this tag.</p>'}
        </div>
        
        ${detectionHtml}
    `;
    
    modal.show();
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// Show error message
function showError(message) {
    const container = document.querySelector('.container-fluid');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger alert-dismissible fade show';
    errorDiv.innerHTML = `
        <strong>Error:</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.insertBefore(errorDiv, container.firstChild);
}

