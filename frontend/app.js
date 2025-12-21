/**
 * StarPrint - Frontend Application
 * DeltaWerks | Star Citizen 3D Print Extractor
 */

// DOM Elements
const setupScreen = document.getElementById('setup-screen');
const mainScreen = document.getElementById('main-screen');
const scPathInput = document.getElementById('sc-path');
const btnSetPath = document.getElementById('btn-set-path');
const setupError = document.getElementById('setup-error');
const categoryTree = document.getElementById('category-tree');
const previewPanel = document.getElementById('preview-panel');
const previewTitle = document.getElementById('preview-title');
const searchInput = document.getElementById('search-input');
const btnExport = document.getElementById('btn-export');

// State
let categories = [];
let currentPath = null;

// Initialize
async function init() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error('Server not responding');

        const status = await response.json();

        if (status.configured) {
            showMainScreen();
            loadCategories();
        } else {
            showSetupScreen();
        }
    } catch (e) {
        console.error('Init error:', e);
        showSetupScreen();
    }
}

function showSetupScreen() {
    if (setupScreen) setupScreen.style.display = 'flex';
    if (mainScreen) mainScreen.classList.add('hidden');
}

function showMainScreen() {
    if (setupScreen) setupScreen.style.display = 'none';
    if (mainScreen) mainScreen.classList.remove('hidden');
}

// Set SC Path
if (btnSetPath) {
    btnSetPath.addEventListener('click', async () => {
        const path = scPathInput.value.trim();
        if (!path) {
            setupError.textContent = 'Please enter a path';
            return;
        }

        setupError.textContent = '';
        btnSetPath.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> INITIALIZING...';
        btnSetPath.disabled = true;

        try {
            const response = await fetch('/api/set-path', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });

            if (!response.ok) {
                const error = await response.json();
                setupError.textContent = error.detail || 'Failed to load game data';
                btnSetPath.innerHTML = '<i class="fa-solid fa-link"></i> CONNECT INTERFACE';
                btnSetPath.disabled = false;
                return;
            }

            showMainScreen();
            loadCategories();
        } catch (e) {
            console.error('Connection error:', e);
            setupError.textContent = 'Connection error - Is the server running?';
            btnSetPath.innerHTML = '<i class="fa-solid fa-link"></i> CONNECT INTERFACE';
            btnSetPath.disabled = false;
        }
    });
}

// Load Categories
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();
        categories = data.categories;
        renderCategoryTree(categories, categoryTree);
    } catch (e) {
        console.error('Failed to load categories:', e);
    }
}

function renderCategoryTree(cats, container) {
    if (!container) return;
    container.innerHTML = '';

    for (const cat of cats) {
        const li = document.createElement('li');
        li.className = 'sidebar-item';

        // Create content wrapper for name and thumbnail button
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'sidebar-item-content';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'sidebar-item-name';
        nameSpan.textContent = cat.name;
        contentWrapper.appendChild(nameSpan);

        // Add thumbnail generation button for leaf nodes (actual item categories)
        if (cat.leaf && cat.path) {
            const thumbBtn = document.createElement('button');
            thumbBtn.className = 'thumb-gen-btn';
            thumbBtn.innerHTML = '<i class="fa-solid fa-camera"></i>';
            thumbBtn.title = 'Generate thumbnails for this category';
            thumbBtn.addEventListener('click', async (e) => {
                e.stopPropagation();

                // Confirmation
                if (!confirm(`Generate thumbnails for "${cat.name}"?\n\nThis will export and render all items in this category. It may take a while.`)) {
                    return;
                }

                thumbBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
                thumbBtn.disabled = true;

                try {
                    const response = await fetch('/api/generate-thumbnails', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: cat.path })
                    });
                    const result = await response.json();

                    if (result.status === 'complete') {
                        thumbBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
                        thumbBtn.classList.add('success');
                        alert(`Thumbnails generated!\n\nGenerated: ${result.generated}\nSkipped (cached): ${result.skipped}\nFailed: ${result.failed}`);

                        // Refresh the grid if we're viewing this category
                        if (currentPath === cat.path) {
                            loadItems(cat.path);
                        }
                    }
                } catch (err) {
                    console.error('Thumbnail generation failed:', err);
                    thumbBtn.innerHTML = '<i class="fa-solid fa-exclamation-triangle"></i>';
                    alert('Thumbnail generation failed. Check console for details.');
                } finally {
                    setTimeout(() => {
                        thumbBtn.innerHTML = '<i class="fa-solid fa-camera"></i>';
                        thumbBtn.disabled = false;
                        thumbBtn.classList.remove('success');
                    }, 3000);
                }
            });
            contentWrapper.appendChild(thumbBtn);
        }

        li.appendChild(contentWrapper);

        if (cat.leaf) {
            // Leaf node - clicking loads items using the internal path
            li.addEventListener('click', (e) => {
                e.stopPropagation();
                document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
                li.classList.add('active');
                loadItems(cat.path);  // Use the actual DataCore path
            });
        } else if (cat.children) {
            // Parent node - clicking toggles children
            li.addEventListener('click', (e) => {
                e.stopPropagation();
                let subUl = li.querySelector('ul');
                if (subUl) {
                    subUl.classList.toggle('hidden');
                } else {
                    subUl = document.createElement('ul');
                    subUl.className = 'sidebar-menu';
                    renderCategoryTree(cat.children, subUl);
                    li.appendChild(subUl);
                }
            });
        }

        container.appendChild(li);
    }
}

// Load Items
async function loadItems(path) {
    currentPath = path;

    const gridContainer = document.querySelector('.grid-container');
    if (!gridContainer) return;

    gridContainer.innerHTML = '<p class="placeholder-msg">Loading...</p>';

    try {
        const response = await fetch(`/api/items/${encodeURIComponent(path)}`);
        const data = await response.json();

        if (!data.items || data.items.length === 0) {
            gridContainer.innerHTML = '<p class="placeholder-msg">No items found in this category.</p>';
            return;
        }

        gridContainer.innerHTML = '';

        for (const item of data.items) {
            const card = document.createElement('div');
            card.className = 'item-card';

            // Thumbnail logic: If thumbnail URL exists, use it with fallback
            let swatchContent = '<i class="fa-solid fa-cube"></i>';
            if (item.thumbnail) {
                swatchContent = `<img src="${item.thumbnail}" alt="${item.name}" loading="lazy" onerror="this.onerror=null; this.parentNode.innerHTML='<i class=\\'fa-solid fa-cube\\'></i>'">`;
            }

            card.innerHTML = `
                <div class="card-swatch">
                    ${swatchContent}
                </div>
                <div class="card-footer">
                    <div class="item-name">${item.name}</div>
                    <div class="item-code">${item.type || ''}</div>
                </div>
            `;
            card.addEventListener('click', () => selectItem(item));
            gridContainer.appendChild(card);
        }
    } catch (e) {
        console.error('Failed to load items:', e);
        gridContainer.innerHTML = '<p class="placeholder-msg">Error loading items.</p>';
    }
}

// Select Item
function selectItem(item) {
    if (previewPanel) previewPanel.classList.remove('hidden');
    if (previewTitle) previewTitle.textContent = item.name;

    // Store selected item for export
    window.selectedItem = item;
}

// Search
if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();

        clearTimeout(searchTimeout);
        if (query.length < 2) return;

        searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                const gridContainer = document.querySelector('.grid-container');
                if (!gridContainer) return;

                if (data.results && data.results.length > 0) {
                    gridContainer.innerHTML = '';
                    for (const item of data.results) {
                        const card = document.createElement('div');
                        card.className = 'item-card';
                        card.innerHTML = `
                            <div class="card-swatch"><i class="fa-solid fa-cube"></i></div>
                            <div class="card-footer">
                                <div class="item-name">${item.name}</div>
                                <div class="item-code">${item.type || ''}</div>
                            </div>
                        `;
                        card.addEventListener('click', () => selectItem(item));
                        gridContainer.appendChild(card);
                    }
                } else {
                    gridContainer.innerHTML = '<p class="placeholder-msg">No results found.</p>';
                }
            } catch (e) {
                console.error('Search error:', e);
            }
        }, 300);
    });
}

// Export
if (btnExport) {
    btnExport.addEventListener('click', async () => {
        if (!window.selectedItem) {
            alert('Please select an item first!');
            return;
        }

        const item = window.selectedItem;
        btnExport.disabled = true;
        btnExport.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> EXPORTING...';

        try {
            const response = await fetch(`/api/export/${encodeURIComponent(item.id)}`);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Export failed');
            }

            if (result.status === 'success') {
                // Show 3D Preview
                const previewContainer = document.getElementById('preview-3d');
                if (previewContainer && result.preview_url) {
                    previewContainer.innerHTML = `
                        <model-viewer 
                            src="${result.preview_url}" 
                            camera-controls 
                            auto-rotate
                            shadow-intensity="1"
                            style="width: 100%; height: 100%; background-color: #0b0c15;"
                        ></model-viewer>
                    `;
                }

                // Trigger download
                const link = document.createElement('a');
                link.href = result.download_url;
                link.download = result.output_file.split('/').pop();
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                // Toast notification instead of alert?
                // For now, keep it simple but maybe less intrusive
                console.log(`Export successful: ${result.output_file}`);
            } else {
                throw new Error(result.message || 'Unknown error');
            }
        } catch (e) {
            console.error('Export error:', e);
            alert(`Export failed:\n${e.message}`);
        } finally {
            btnExport.disabled = false;
            btnExport.innerHTML = '<i class="fa-solid fa-download"></i> EXPORT OBJ';
        }
    });
}

// Start
init();
