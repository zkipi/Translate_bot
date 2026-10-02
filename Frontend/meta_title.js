const META_TITLE_BACKEND_URL = window.BACKEND_URL;

// ==========================================
// META TITLE - SINGLE GENERATION
// ==========================================

// META TITLE ELEMENTS
// ==========================================

const metaBrand =
    document.getElementById("metaBrand");

const metaProductName =
    document.getElementById("metaProductName");

const metaTitleSourceDescription =
    document.getElementById("metaTitleSourceDescription");

const generateMetaTitleButton =
    document.getElementById("generateMetaTitleButton");

const metaTitleResult =
    document.getElementById("metaTitleResult");

const generatedMetaTitle =
    document.getElementById("generatedMetaTitle");

const metaTitleCount =
    document.getElementById("metaTitleCount");

const copyMetaTitleButton =
    document.getElementById("copyMetaTitleButton");


function updateMetaTitleCount(title) {
    const count = title.length;
    metaTitleCount.textContent = `${count} / 60 characters`;
    metaTitleCount.classList.toggle("meta-title-over-limit", count > 60);
}


generateMetaTitleButton.addEventListener("click", async () => {
    const brand = metaBrand.value.trim();
    const productName = metaProductName.value.trim();
    const description = metaTitleSourceDescription.value.trim();

    if (!productName && !description) {
        alert("Enter a product name or description first.");
        return;
    }

    generateMetaTitleButton.disabled = true;
    generateMetaTitleButton.textContent = "Generating...";
    metaTitleResult.style.display = "none";

    try {
        const response = await fetch(
            `${META_TITLE_BACKEND_URL}/generate-meta-title`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    brand: brand,
                    product_name: productName,
                    description: description
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Meta title generation failed.");
        }

        generatedMetaTitle.value = data.title;
        updateMetaTitleCount(data.title);
        metaTitleResult.style.display = "block";

    } catch (error) {
        alert(error.message);
    } finally {
        generateMetaTitleButton.disabled = false;
        generateMetaTitleButton.textContent = "Generate meta title";
    }
});


copyMetaTitleButton.addEventListener("click", async () => {
    if (!generatedMetaTitle.value) {
        return;
    }

    await navigator.clipboard.writeText(
        generatedMetaTitle.value
    );

    copyMetaTitleButton.textContent = "Copied";

    setTimeout(() => {
        copyMetaTitleButton.textContent = "Copy";
    }, 1200);
});

// ==========================================
// META TITLE - EXCEL
// ==========================================

const metaExcelFile = document.getElementById("metaExcelFile");
const metaExcelSelectedFile = document.getElementById("metaExcelSelectedFile");
const metaExcelBrandColumn = document.getElementById("metaExcelBrandColumn");
const metaExcelProductColumn = document.getElementById("metaExcelProductColumn");
const metaExcelDescriptionColumn = document.getElementById("metaExcelDescriptionColumn");
const metaExcelButton = document.getElementById("metaExcelButton");
const stopMetaExcelButton = document.getElementById("stopMetaExcelButton");
const metaExcelProgress = document.getElementById("metaExcelProgress");

let currentMetaExcelJobId = null;
let metaExcelStartTime = null;

// ==========================================
// META TITLE EXCEL
// ==========================================

function formatMetaExcelTime(totalSeconds) {
    const seconds = Math.max(0, Math.round(totalSeconds));
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}

function resetMetaExcelColumnSelect(selectElement, placeholder) {
    selectElement.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    selectElement.appendChild(option);
    selectElement.disabled = true;
}

function populateMetaExcelColumnSelect(selectElement, columns, includeNone) {
    selectElement.innerHTML = "";
    if (includeNone) {
        const noneOption = document.createElement("option");
        noneOption.value = "";
        noneOption.textContent = "None";
        selectElement.appendChild(noneOption);
    }
    columns.forEach((column) => {
        const option = document.createElement("option");
        option.value = column;
        option.textContent = column;
        selectElement.appendChild(option);
    });
    selectElement.disabled = false;
}

function selectLikelyMetaColumn(selectElement, columns, names) {
    const match = columns.find((column) =>
        names.includes(String(column).trim().toLowerCase())
    );
    if (match !== undefined) {
        selectElement.value = match;
    }
}

metaExcelFile.addEventListener("change", async () => {
    if (!metaExcelFile.files.length) {
        metaExcelSelectedFile.textContent = "No file selected";
        resetMetaExcelColumnSelect(metaExcelBrandColumn, "Choose an Excel file first");
        resetMetaExcelColumnSelect(metaExcelProductColumn, "Choose an Excel file first");
        resetMetaExcelColumnSelect(metaExcelDescriptionColumn, "Choose an Excel file first");
        return;
    }

    const file = metaExcelFile.files[0];
    metaExcelSelectedFile.textContent = file.name;
    resetMetaExcelColumnSelect(metaExcelBrandColumn, "Reading columns...");
    resetMetaExcelColumnSelect(metaExcelProductColumn, "Reading columns...");
    resetMetaExcelColumnSelect(metaExcelDescriptionColumn, "Reading columns...");

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${META_TITLE_BACKEND_URL}/meta-title-columns`, {
            method: "POST",
            body: formData
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Backend returned HTTP ${response.status}.`);
        }

        const columns = Array.isArray(data.columns) ? data.columns : [];
        if (!columns.length) {
            throw new Error("No columns were found in the Excel file.");
        }

        populateMetaExcelColumnSelect(metaExcelBrandColumn, columns, true);
        populateMetaExcelColumnSelect(metaExcelProductColumn, columns, false);
        populateMetaExcelColumnSelect(metaExcelDescriptionColumn, columns, true);

        selectLikelyMetaColumn(metaExcelBrandColumn, columns, [
            "brand", "brand_name", "manufacturer", "varumärke"
        ]);
        selectLikelyMetaColumn(metaExcelProductColumn, columns, [
            "product name", "product_name", "name", "product", "produktnamn"
        ]);
        selectLikelyMetaColumn(metaExcelDescriptionColumn, columns, [
            "description", "website_description", "product description",
            "product_description", "beskrivning"
        ]);
    } catch (error) {
        console.error("Could not read Meta title Excel columns:", error);
        resetMetaExcelColumnSelect(metaExcelBrandColumn, "Could not read columns");
        resetMetaExcelColumnSelect(metaExcelProductColumn, "Could not read columns");
        resetMetaExcelColumnSelect(metaExcelDescriptionColumn, "Could not read columns");
        alert("Could not read the Excel columns.\n\nError: " + (error.message || error));
    }
});

function showMetaExcelProgress(html) {
    metaExcelProgress.innerHTML = html;
    metaExcelProgress.style.display = "block";
}

async function monitorMetaExcelProgress(jobId) {
    while (true) {
        const response = await fetch(`${META_TITLE_BACKEND_URL}/meta-title-status/${jobId}`);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Backend returned HTTP ${response.status}.`);
        }

        const current = Number(data.current || 0);
        const total = Number(data.total || 0);
        const percent = total > 0 ? Math.min(100, (current / total) * 100) : 0;
        const elapsedSeconds = metaExcelStartTime
            ? (Date.now() - metaExcelStartTime) / 1000
            : 0;
        const estimatedTotalSeconds = current > 0
            ? elapsedSeconds * (total / current)
            : 0;
        const remainingSeconds = Math.max(0, estimatedTotalSeconds - elapsedSeconds);

        if (data.status === "processing") {
            showMetaExcelProgress(`
                <strong>Generating meta titles...</strong>
                <div style="margin-top: 12px; width: 100%; height: 10px; background: #e9ecef; border-radius: 999px; overflow: hidden;">
                    <div style="width: ${percent}%; height: 100%; background: #222; transition: width 0.3s ease;"></div>
                </div>
                <div style="margin-top: 10px; font-size: 14px; color: #666;">${current} / ${total} rows</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">Elapsed time: ${formatMetaExcelTime(elapsedSeconds)}</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">Remaining: ${current > 0 ? formatMetaExcelTime(remainingSeconds) : "Calculating..."}</div>
            `);
            await new Promise(resolve => setTimeout(resolve, 1000));
            continue;
        }

        if (data.status === "completed" && data.download_ready) {
            const finalElapsed = metaExcelStartTime ? (Date.now() - metaExcelStartTime) / 1000 : 0;
            showMetaExcelProgress(`
                <strong>Meta title generation complete ✓</strong>
                <div style="margin-top: 8px; font-size: 14px; color: #666;">${data.completed || 0} titles generated</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">${data.skipped || 0} rows skipped</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">${data.failed || 0} errors</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">Elapsed time: ${formatMetaExcelTime(finalElapsed)}</div>
            `);
            const link = document.createElement("a");
            link.href = `${META_TITLE_BACKEND_URL}/download-meta-titles/${jobId}`;
            link.download = "meta_titles.xlsx";
            document.body.appendChild(link);
            link.click();
            link.remove();
            metaExcelButton.disabled = false;
            metaExcelButton.textContent = "Generate Meta Titles";
            stopMetaExcelButton.style.display = "none";
            stopMetaExcelButton.disabled = false;
            stopMetaExcelButton.textContent = "Stop generation";
            currentMetaExcelJobId = null;
            metaExcelStartTime = null;
            return;
        }

        if (data.status === "cancelled" && data.download_ready) {
            const finalElapsed = metaExcelStartTime ? (Date.now() - metaExcelStartTime) / 1000 : 0;
            showMetaExcelProgress(`
                <strong>Generation stopped</strong>
                <div style="margin-top: 8px; font-size: 14px; color: #666;">${data.completed || 0} titles generated before stopping</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">Elapsed time: ${formatMetaExcelTime(finalElapsed)}</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">The partial Excel file will be downloaded.</div>
            `);
            const link = document.createElement("a");
            link.href = `${META_TITLE_BACKEND_URL}/download-meta-titles/${jobId}`;
            link.download = "meta_titles_partial.xlsx";
            document.body.appendChild(link);
            link.click();
            link.remove();
            metaExcelButton.disabled = false;
            metaExcelButton.textContent = "Generate Meta Titles";
            stopMetaExcelButton.style.display = "none";
            stopMetaExcelButton.disabled = false;
            stopMetaExcelButton.textContent = "Stop generation";
            currentMetaExcelJobId = null;
            metaExcelStartTime = null;
            return;
        }

        if (data.status === "failed") {
            throw new Error(data.error || "Meta title Excel generation failed.");
        }

        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}

metaExcelButton.addEventListener("click", async () => {
    if (!metaExcelFile.files.length) {
        alert("Please choose an Excel file first.");
        return;
    }
    if (!metaExcelProductColumn.value) {
        alert("Please choose a Product name column first.");
        return;
    }

    metaExcelButton.disabled = true;
    metaExcelButton.textContent = "Starting...";
    stopMetaExcelButton.style.display = "inline-block";
    stopMetaExcelButton.disabled = false;
    stopMetaExcelButton.textContent = "Stop generation";
    metaExcelStartTime = Date.now();
    showMetaExcelProgress("Starting meta title generation...");

    try {
        const formData = new FormData();
        formData.append("file", metaExcelFile.files[0]);
        formData.append("brand_column", metaExcelBrandColumn.value);
        formData.append("product_column", metaExcelProductColumn.value);
        formData.append("description_column", metaExcelDescriptionColumn.value);

        const response = await fetch(`${META_TITLE_BACKEND_URL}/generate-meta-titles`, {
            method: "POST",
            body: formData
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Backend returned HTTP ${response.status}.`);
        }
        currentMetaExcelJobId = data.job_id;
        await monitorMetaExcelProgress(data.job_id);
    } catch (error) {
        console.error("Meta title Excel error:", error);
        showMetaExcelProgress("Meta title generation failed.");
        alert("Meta title Excel generation failed.\n\nError: " + (error.message || error));
        metaExcelButton.disabled = false;
        metaExcelButton.textContent = "Generate Meta Titles";
        stopMetaExcelButton.style.display = "none";
        stopMetaExcelButton.disabled = false;
        stopMetaExcelButton.textContent = "Stop generation";
        currentMetaExcelJobId = null;
        metaExcelStartTime = null;
    }
});

stopMetaExcelButton.addEventListener("click", async () => {
    if (!currentMetaExcelJobId) return;
    stopMetaExcelButton.disabled = true;
    stopMetaExcelButton.textContent = "Stopping...";
    try {
        const response = await fetch(`${META_TITLE_BACKEND_URL}/stop-meta-titles/${currentMetaExcelJobId}`, {
            method: "POST"
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Backend returned HTTP ${response.status}.`);
        }
        showMetaExcelProgress("Stopping generation...<br>Finishing requests that are already running.");
    } catch (error) {
        console.error("Meta title stop error:", error);
        alert("Could not stop the generation.\n\nError: " + (error.message || error));
        stopMetaExcelButton.disabled = false;
        stopMetaExcelButton.textContent = "Stop generation";
    }
});
