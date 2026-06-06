function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
    const dataNode = document.getElementById("mindmap-data");
    const renderArea = document.getElementById("mermaid-render-area");
    const container = document.getElementById("mindmap-container");
    
    const btnZoomIn = document.getElementById("btn-zoom-in");
    const btnZoomOut = document.getElementById("btn-zoom-out");
    const btnResetZoom = document.getElementById("btn-reset-zoom");
    const btnFullscreen = document.getElementById("btn-fullscreen");

    if (!dataNode || !renderArea) return;

    let jsonData = null;
    try {
        let rawData = dataNode.textContent.trim();
        if (rawData.startsWith("```json")) {
            rawData = rawData.replace(/^```json\n/, "").replace(/\n```$/, "");
        } else if (rawData.startsWith("```")) {
            rawData = rawData.replace(/^```\n/, "").replace(/\n```$/, "");
        }
        jsonData = JSON.parse(rawData);
    } catch (err) {
        console.error("Failed to parse mindmap JSON:", err);
        renderArea.innerHTML = `<div class="text-red-400 p-4 border border-red-800 rounded bg-red-900/20 max-w-lg text-center">Failed to render mindmap. Invalid JSON data.</div>`;
        return;
    }

    // Add custom CSS for the tree layout dynamically
    const style = document.createElement('style');
    style.innerHTML = `
        .css-tree ul { padding-top: 20px; position: relative; display: flex; justify-content: center; }
        .css-tree li { float: left; text-align: center; list-style-type: none; position: relative; padding: 20px 10px 0 10px; }
        .css-tree li::before, .css-tree li::after { content: ''; position: absolute; top: 0; right: 50%; border-top: 1px solid #57534e; width: 50%; height: 20px; }
        .css-tree li::after { right: auto; left: 50%; border-left: 1px solid #57534e; }
        .css-tree li:only-child::after, .css-tree li:only-child::before { display: none; }
        .css-tree li:only-child { padding-top: 0; }
        .css-tree li:first-child::before, .css-tree li:last-child::after { border: 0 none; }
        .css-tree li:last-child::before { border-right: 1px solid #57534e; border-radius: 0 4px 0 0; }
        .css-tree li:first-child::after { border-radius: 4px 0 0 0; }
        .css-tree ul ul::before { content: ''; position: absolute; top: 0; left: 50%; border-left: 1px solid #57534e; width: 0; height: 20px; transform: translateX(-50%); }
    `;
    document.head.appendChild(style);

    function buildNode(node, isRoot = false) {
        const li = document.createElement("li");
        
        const box = document.createElement("div");
        box.className = isRoot 
            ? "inline-block px-6 py-3 bg-neutral-900 rounded-sm shadow-md border border-orange-300 flex items-center gap-3 relative z-10"
            : "inline-block px-4 py-2 bg-neutral-800 rounded-sm shadow border border-stone-700 relative z-10 hover:border-stone-500 transition-colors";
            
        let contentHtml = "";
        if (isRoot) {
            contentHtml = `<div class="text-orange-200 text-base font-semibold leading-relaxed">${escapeHtml(node.name || "Root")}</div>`;
        } else {
            contentHtml = `<div class="text-zinc-200 text-sm font-medium">${escapeHtml(node.name || "Node")}</div>`;
        }
        
        box.innerHTML = contentHtml;
        li.appendChild(box);

        if (node.children && Array.isArray(node.children) && node.children.length > 0) {
            // Add toggle badge
            const badge = document.createElement("div");
            badge.className = "absolute -bottom-2.5 left-1/2 -translate-x-1/2 w-5 h-5 bg-neutral-800 rounded-full border border-stone-500 text-stone-300 flex items-center justify-center cursor-pointer hover:bg-stone-600 hover:text-white transition-colors z-20 shadow";
            
            const iconUp = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>`;
            const iconDown = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>`;
            
            badge.innerHTML = iconUp;
            badge.title = "Toggle children";
            box.appendChild(badge);

            const ul = document.createElement("ul");
            node.children.forEach(child => {
                ul.appendChild(buildNode(child, false));
            });
            li.appendChild(ul);

            // Toggle logic
            badge.addEventListener("click", (e) => {
                e.stopPropagation();
                if (ul.style.display === "none") {
                    ul.style.display = "flex";
                    badge.innerHTML = iconUp;
                    badge.classList.replace("bg-orange-500", "bg-neutral-800");
                    badge.classList.replace("text-white", "text-stone-300");
                    badge.classList.replace("border-orange-400", "border-stone-500");
                } else {
                    ul.style.display = "none";
                    badge.innerHTML = iconDown;
                    badge.classList.replace("bg-neutral-800", "bg-orange-500");
                    badge.classList.replace("text-stone-300", "text-white");
                    badge.classList.replace("border-stone-500", "border-orange-400");
                }
            });
        }
        return li;
    }

    const treeContainer = document.createElement("div");
    treeContainer.className = "css-tree";
    const rootUl = document.createElement("ul");
    rootUl.style.paddingTop = "0";
    rootUl.appendChild(buildNode(jsonData, true));
    treeContainer.appendChild(rootUl);

    renderArea.innerHTML = "";
    renderArea.appendChild(treeContainer);

    // Zoom and Pan Logic
    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    let isDragging = false;
    let startX, startY;

    const ZOOM_SPEED = 0.1;
    const MIN_SCALE = 0.2;
    const MAX_SCALE = 5;

    const updateTransform = () => {
        renderArea.style.transform = `scale(${scale}) translate(${translateX}px, ${translateY}px)`;
    };

    btnZoomIn.addEventListener("click", () => {
        scale = Math.min(MAX_SCALE, scale + ZOOM_SPEED);
        updateTransform();
    });

    btnZoomOut.addEventListener("click", () => {
        scale = Math.max(MIN_SCALE, scale - ZOOM_SPEED);
        updateTransform();
    });

    btnResetZoom.addEventListener("click", () => {
        scale = 1;
        translateX = 0;
        translateY = 0;
        updateTransform();
    });

    renderArea.addEventListener("mousedown", (e) => {
        if (e.target.closest('button')) return;
        isDragging = true;
        startX = e.clientX - translateX * scale;
        startY = e.clientY - translateY * scale;
        renderArea.classList.add("cursor-grabbing");
    });

    window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        e.preventDefault();
        translateX = (e.clientX - startX) / scale;
        translateY = (e.clientY - startY) / scale;
        updateTransform();
    });

    window.addEventListener("mouseup", () => {
        isDragging = false;
        renderArea.classList.remove("cursor-grabbing");
    });

    container.addEventListener("wheel", (e) => {
        e.preventDefault();
        const delta = Math.sign(e.deltaY) * -1;
        scale = Math.min(Math.max(MIN_SCALE, scale + delta * ZOOM_SPEED), MAX_SCALE);
        updateTransform();
    });

    btnFullscreen.addEventListener("click", () => {
        if (!document.fullscreenElement) {
            container.requestFullscreen().catch(err => {
                console.error("Fullscreen error:", err);
            });
        } else {
            document.exitFullscreen();
        }
    });

    document.addEventListener("fullscreenchange", () => {
        if (document.fullscreenElement) {
            btnFullscreen.innerHTML = `<iconify-icon icon="tabler:minimize" class="text-lg"></iconify-icon>`;
        } else {
            btnFullscreen.innerHTML = `<iconify-icon icon="tabler:maximize" class="text-lg"></iconify-icon>`;
        }
    });

    const btnExport = document.getElementById("btn-export");
    if (btnExport) {
        btnExport.addEventListener("click", async () => {
            const originalTransform = renderArea.style.transform;
            renderArea.style.transform = "scale(1) translate(0,0)";
            const originalClass = renderArea.className;
            renderArea.classList.remove("cursor-grab", "active:cursor-grabbing");
            
            try {
                btnExport.innerHTML = `<iconify-icon icon="tabler:loader" class="text-lg animate-spin"></iconify-icon><span class="text-sm font-medium">Exporting...</span>`;
                const dataUrl = await window.htmlToImage.toPng(treeContainer, {
                    backgroundColor: "#171717", // neutral-900
                    pixelRatio: 2
                });
                
                const link = document.createElement("a");
                link.download = `Mindmap_${Date.now()}.png`;
                link.href = dataUrl;
                link.click();
            } catch (err) {
                console.error("Export failed:", err);
                alert("Gagal mengekspor gambar: " + (err.message || err));
            } finally {
                renderArea.style.transform = originalTransform;
                renderArea.className = originalClass;
                btnExport.innerHTML = `<iconify-icon icon="tabler:download" class="text-lg"></iconify-icon><span class="text-sm font-medium">Export</span>`;
            }
        });
    }
});
