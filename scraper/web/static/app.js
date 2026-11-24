let currentItems = [];

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initControls();
    loadFiles();

    // Limit slider live text
    const limitRange = document.getElementById("limitRange");
    const limitDisplay = document.getElementById("limitDisplay");
    limitRange.addEventListener("input", () => {
        limitDisplay.textContent = limitRange.value;
    });

    // Test macOS alert
    document.getElementById("testNotifyBtn").addEventListener("click", async () => {
        try {
            await fetch("/api/notify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: "Bulk Scraper macOS",
                    message: "Notification Center alert verified working!",
                    sound: "Hero",
                }),
            });
        } catch (e) {
            console.error(e);
        }
    });

    // Scrape button
    document.getElementById("startScrapeBtn").addEventListener("click", startScraping);

    // Filter search
    document.getElementById("searchFilter").addEventListener("input", filterResults);

    // Export buttons
    document.getElementById("downloadCsvBtn").addEventListener("click", () => exportData("csv"));
    document.getElementById("downloadJsonBtn").addEventListener("click", () => exportData("json"));

    // Modal close
    const modal = document.getElementById("mediaModal");
    document.querySelector(".modal-close").addEventListener("click", () => {
        modal.style.display = "none";
    });
    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });
});

function initTabs() {
    const tabSingle = document.getElementById("tabSingle");
    const tabBatch = document.getElementById("tabBatch");
    const panelSingle = document.getElementById("singleTargetPanel");
    const panelBatch = document.getElementById("batchTargetPanel");

    tabSingle.addEventListener("click", () => {
        tabSingle.classList.add("active");
        tabBatch.classList.remove("active");
        panelSingle.classList.add("active");
        panelBatch.classList.remove("active");
    });

    tabBatch.addEventListener("click", () => {
        tabBatch.classList.add("active");
        tabSingle.classList.remove("active");
        panelBatch.classList.add("active");
        panelSingle.classList.remove("active");
    });
}

function initControls() {
    // Quick focus helper
    document.getElementById("targetInput").focus();
}

async function startScraping() {
    const isBatch = document.getElementById("tabBatch").classList.contains("active");
    const downloadMedia = document.getElementById("downloadMediaCheck").checked;
    const notify = document.getElementById("macosNotifyCheck").checked;

    let payload = { download_media: downloadMedia, notify: notify };

    if (!isBatch) {
        const platform = document.getElementById("platformSelect").value;
        const target = document.getElementById("targetInput").value.trim();
        const limit = parseInt(document.getElementById("limitRange").value, 10);

        if (!target) {
            alert("Please enter a target to scrape.");
            return;
        }

        payload.platform = platform;
        payload.target = target;
        payload.limit = limit;
    } else {
        const lines = document.getElementById("batchInput").value.split("\n");
        const targets = [];
        for (let line of lines) {
            line = line.trim();
            if (!line || line.startsWith("#")) continue;
            let parts = line.split(":");
            let plat = parts.length > 1 ? parts[0].trim() : "reddit";
            let tgt = parts.length > 1 ? parts.slice(1).join(":").trim() : line;
            targets.push({ platform: plat, target: tgt, limit: 20 });
        }
        if (targets.length === 0) {
            alert("Please provide at least one target in the batch list.");
            return;
        }
        payload.targets = targets;
    }

    setScrapingState(true);

    try {
        const res = await fetch("/api/scrape", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (data.success && data.summary) {
            currentItems = data.summary.items || [];
            updateMetrics(data.summary);
            renderTable(currentItems);
            loadFiles();
        } else {
            alert("Error: " + (data.error || "Scraping failed"));
        }
    } catch (err) {
        console.error(err);
        alert("Failed to connect to backend scraper server.");
    } finally {
        setScrapingState(false);
    }
}

function setScrapingState(isScraping) {
    const btn = document.getElementById("startScrapeBtn");
    const banner = document.getElementById("statusBanner");
    const statusVal = document.getElementById("statStatus");

    if (isScraping) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Scraping...';
        banner.classList.remove("hidden");
        statusVal.textContent = "Scraping";
        statusVal.style.color = "#ff9500";
    } else {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🚀</span> Start Bulk Scrape';
        banner.classList.add("hidden");
        statusVal.textContent = "Ready";
        statusVal.style.color = "var(--accent-blue)";
    }
}

function updateMetrics(summary) {
    document.getElementById("statTotalItems").textContent = summary.total_items_scraped || 0;
    const mediaCount = (summary.media_report && summary.media_report.successful) || 0;
    document.getElementById("statMediaCount").textContent = mediaCount;
    document.getElementById("statElapsed").textContent = `${summary.elapsed_seconds || 0}s`;
    document.getElementById("resultsCountBadge").textContent = `${summary.total_items_scraped || 0} items`;

    document.getElementById("downloadCsvBtn").disabled = currentItems.length === 0;
    document.getElementById("downloadJsonBtn").disabled = currentItems.length === 0;
}

function renderTable(items) {
    const tbody = document.getElementById("resultsTbody");
    tbody.innerHTML = "";

    if (!items || items.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-table-cell">
                    <div class="empty-state">
                        <div class="empty-icon">🔍</div>
                        <h4>No items matched</h4>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    items.forEach((item) => {
        const tr = document.createElement("tr");

        let metricsHtml = "";
        if (item.metrics) {
            for (let [k, v] of Object.entries(item.metrics)) {
                if (v !== null && v !== undefined) {
                    metricsHtml += `<span class="badge metric-tag">${k}: ${v}</span>`;
                }
            }
        }

        let mediaHtml = "";
        if (item.media_urls && item.media_urls.length > 0) {
            item.media_urls.slice(0, 3).forEach((url) => {
                mediaHtml += `<img src="${url}" class="thumb-preview" onclick="openMediaModal('${url}')" onerror="this.style.display='none'">`;
            });
        }

        tr.innerHTML = `
            <td><span class="badge platform-${item.platform}">${item.platform.toUpperCase()}</span></td>
            <td><strong>${item.author || item.target}</strong></td>
            <td>
                ${item.title ? `<div style="font-weight:600; margin-bottom:4px;">${escapeHtml(item.title)}</div>` : ""}
                <div class="post-text-box">${escapeHtml(item.text || "")}</div>
                <div>${mediaHtml}</div>
                ${item.url ? `<a href="${item.url}" target="_blank" style="font-size:11px; color:var(--accent-blue);">View Post &rarr;</a>` : ""}
            </td>
            <td>${metricsHtml}</td>
            <td style="white-space:nowrap; font-size:11px; color:var(--text-secondary);">${(item.timestamp || item.scraped_at || "").slice(0, 10)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function filterResults() {
    const query = document.getElementById("searchFilter").value.toLowerCase();
    const filtered = currentItems.filter((item) => {
        const text = (item.text || "") + " " + (item.title || "") + " " + (item.author || "") + " " + (item.platform || "");
        return text.toLowerCase().includes(query);
    });
    renderTable(filtered);
}

function openMediaModal(url) {
    const modal = document.getElementById("mediaModal");
    const img = document.getElementById("modalImg");
    img.src = url;
    modal.style.display = "flex";
}

function exportData(format) {
    if (!currentItems || currentItems.length === 0) return;

    if (format === "json") {
        const blob = new Blob([JSON.stringify(currentItems, null, 2)], { type: "application/json" });
        downloadBlob(blob, `bulk_scrape_${Date.now()}.json`);
    } else if (format === "csv") {
        let csvContent = "data:text/csv;charset=utf-8,";
        let headers = ["platform", "author", "title", "text", "url", "timestamp"];
        csvContent += headers.join(",") + "\r\n";

        currentItems.forEach((row) => {
            let line = [
                row.platform,
                `"${(row.author || '').replace(/"/g, '""')}"`,
                `"${(row.title || '').replace(/"/g, '""')}"`,
                `"${(row.text || '').replace(/"/g, '""')}"`,
                `"${row.url || ''}"`,
                `"${row.timestamp || ''}"`,
            ].join(",");
            csvContent += line + "\r\n";
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `bulk_scrape_${Date.now()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function loadFiles() {
    try {
        const res = await fetch("/api/files");
        const data = await res.json();
        const filesContainer = document.getElementById("filesList");
        filesContainer.innerHTML = "";

        if (!data.files || data.files.length === 0) {
            filesContainer.innerHTML = '<div class="empty-state-sm">No files exported yet</div>';
            return;
        }

        data.files.slice(0, 6).forEach((f) => {
            const item = document.createElement("div");
            item.className = "file-item";
            item.innerHTML = `
                <a href="${f.path}" target="_blank" download>${f.name}</a>
                <span style="font-size:10px; color:var(--text-secondary);">${Math.round(f.size / 1024)} KB</span>
            `;
            filesContainer.appendChild(item);
        });
    } catch (e) {
        console.error(e);
    }
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
