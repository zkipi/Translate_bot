const META_DESCRIPTION_BACKEND_URL = window.BACKEND_URL;

// ==========================================
// META DESCRIPTION - SINGLE GENERATION
// ==========================================

const metaDescBrand = document.getElementById("metaDescBrand");
const metaDescProductName = document.getElementById("metaDescProductName");
const metaDescSource = document.getElementById("metaDescSource");
const generateMetaDescriptionButton = document.getElementById("generateMetaDescriptionButton");
const metaDescriptionResult = document.getElementById("metaDescriptionResult");
const generatedMetaDescription = document.getElementById("generatedMetaDescription");
const metaDescriptionCount = document.getElementById("metaDescriptionCount");
const copyMetaDescriptionButton = document.getElementById("copyMetaDescriptionButton");

function updateMetaDescriptionCount(description) {
    const count = description.length;
    metaDescriptionCount.textContent = `${count} / 155 characters`;
    metaDescriptionCount.classList.toggle("meta-title-over-limit", count > 155);
}

generateMetaDescriptionButton.addEventListener("click", async () => {
    const brand = metaDescBrand.value.trim();
    const productName = metaDescProductName.value.trim();
    const description = metaDescSource.value.trim();

    if (!productName && !description) {
        alert("Enter a product name or description first.");
        return;
    }

    generateMetaDescriptionButton.disabled = true;
    generateMetaDescriptionButton.textContent = "Generating...";
    metaDescriptionResult.style.display = "none";

    try {
        const response = await fetch(`${META_DESCRIPTION_BACKEND_URL}/generate-meta-description`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                brand,
                product_name: productName,
                description
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Meta description generation failed.");
        }

        generatedMetaDescription.value = data.description;
        updateMetaDescriptionCount(data.description);
        metaDescriptionResult.style.display = "block";
    } catch (error) {
        console.error("Meta description error:", error);
        alert(error.message || "Meta description generation failed.");
    } finally {
        generateMetaDescriptionButton.disabled = false;
        generateMetaDescriptionButton.textContent = "Generate meta description";
    }
});

copyMetaDescriptionButton.addEventListener("click", async () => {
    if (!generatedMetaDescription.value) {
        return;
    }

    try {
        await navigator.clipboard.writeText(generatedMetaDescription.value);
        copyMetaDescriptionButton.textContent = "Copied";
        setTimeout(() => {
            copyMetaDescriptionButton.textContent = "Copy";
        }, 1200);
    } catch (error) {
        console.error("Meta description copy error:", error);
        alert("Could not copy the meta description.");
    }
});


// ==========================================
// META DESCRIPTION - EXCEL
// ==========================================

const metaDescExcelFile = document.getElementById("metaDescExcelFile");
const metaDescExcelSelectedFile = document.getElementById("metaDescExcelSelectedFile");
const metaDescExcelBrandColumn = document.getElementById("metaDescExcelBrandColumn");
const metaDescExcelProductColumn = document.getElementById("metaDescExcelProductColumn");
const metaDescExcelDescriptionColumn = document.getElementById("metaDescExcelDescriptionColumn");
const metaDescExcelButton = document.getElementById("metaDescExcelButton");
const stopMetaDescExcelButton = document.getElementById("stopMetaDescExcelButton");
const metaDescExcelProgress = document.getElementById("metaDescExcelProgress");

let currentMetaDescriptionExcelJobId = null;
let metaDescriptionExcelStartTime = null;

function formatMetaDescriptionExcelTime(totalSeconds) {
    const seconds = Math.max(0, Math.round(totalSeconds));
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}

function resetMetaDescriptionColumnSelect(selectElement, placeholder) {
    selectElement.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    selectElement.appendChild(option);
    selectElement.disabled = true;
}

function populateMetaDescriptionColumnSelect(selectElement, columns, includeNone) {
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

function selectLikelyMetaDescriptionColumn(selectElement, columns, names) {
    const match = columns.find((column) =>
        names.includes(String(column).trim().toLowerCase())
    );

    if (match !== undefined) {
        selectElement.value = match;
    }
}

metaDescExcelFile.addEventListener("change", async () => {
    if (!metaDescExcelFile.files.length) {
        metaDescExcelSelectedFile.textContent = "No file selected";
        resetMetaDescriptionColumnSelect(metaDescExcelBrandColumn, "Choose an Excel file first");
        resetMetaDescriptionColumnSelect(metaDescExcelProductColumn, "Choose an Excel file first");
        resetMetaDescriptionColumnSelect(metaDescExcelDescriptionColumn, "Choose an Excel file first");
        return;
    }

    const file = metaDescExcelFile.files[0];
    metaDescExcelSelectedFile.textContent = file.name;
    resetMetaDescriptionColumnSelect(metaDescExcelBrandColumn, "Reading columns...");
    resetMetaDescriptionColumnSelect(metaDescExcelProductColumn, "Reading columns...");
    resetMetaDescriptionColumnSelect(metaDescExcelDescriptionColumn, "Reading columns...");

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${META_DESCRIPTION_BACKEND_URL}/meta-description-columns`, {
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

        populateMetaDescriptionColumnSelect(metaDescExcelBrandColumn, columns, true);
        populateMetaDescriptionColumnSelect(metaDescExcelProductColumn, columns, false);
        populateMetaDescriptionColumnSelect(metaDescExcelDescriptionColumn, columns, true);

        selectLikelyMetaDescriptionColumn(metaDescExcelBrandColumn, columns, [
            "brand", "brand_name", "manufacturer", "varumärke"
        ]);
        selectLikelyMetaDescriptionColumn(metaDescExcelProductColumn, columns, [
            "product name", "product_name", "name", "product", "produktnamn"
        ]);
        selectLikelyMetaDescriptionColumn(metaDescExcelDescriptionColumn, columns, [
            "description", "website_description", "product description",
            "product_description", "beskrivning"
        ]);
    } catch (error) {
        console.error("Could not read Meta description Excel columns:", error);
        resetMetaDescriptionColumnSelect(metaDescExcelBrandColumn, "Could not read columns");
        resetMetaDescriptionColumnSelect(metaDescExcelProductColumn, "Could not read columns");
        resetMetaDescriptionColumnSelect(metaDescExcelDescriptionColumn, "Could not read columns");
        alert("Could not read the Excel columns.\n\nError: " + (error.message || error));
    }
});

function showMetaDescriptionExcelProgress(html) {
    metaDescExcelProgress.innerHTML = html;
    metaDescExcelProgress.style.display = "block";
}

async function monitorMetaDescriptionExcelProgress(jobId) {
    while (true) {
        const response = await fetch(`${META_DESCRIPTION_BACKEND_URL}/meta-description-status/${jobId}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Backend returned HTTP ${response.status}.`);
        }

        const current = Number(data.current || 0);
        const total = Number(data.total || 0);
        const percent = total > 0 ? Math.min(100, (current / total) * 100) : 0;
        const elapsedSeconds = metaDescriptionExcelStartTime
            ? (Date.now() - metaDescriptionExcelStartTime) / 1000
            : 0;
        const estimatedTotalSeconds = current > 0
            ? elapsedSeconds * (total / current)
            : 0;
        const remainingSeconds = Math.max(0, estimatedTotalSeconds - elapsedSeconds);

        if (data.status === "processing") {
            showMetaDescriptionExcelProgress(`
                <strong>Generating meta descriptions...</strong>
                <div style="margin-top: 12px; width: 100%; height: 10px; background: #e9ecef; border-radius: 999px; overflow: hidden;">
                    <div style="width: ${percent}%; height: 100%; background: #222; transition: width 0.3s ease;"></div>
                </div>
                <div style="margin-top: 10px; font-size: 14px; color: #666;">${current} / ${total} rows</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">Elapsed time: ${formatMetaDescriptionExcelTime(elapsedSeconds)}</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">Remaining: ${current > 0 ? formatMetaDescriptionExcelTime(remainingSeconds) : "Calculating..."}</div>
            `);
            await new Promise(resolve => setTimeout(resolve, 1000));
            continue;
        }

        if (data.status === "completed" && data.download_ready) {
            const finalElapsed = metaDescriptionExcelStartTime
                ? (Date.now() - metaDescriptionExcelStartTime) / 1000
                : 0;

            showMetaDescriptionExcelProgress(`
                <strong>Meta description generation complete ✓</strong>
                <div style="margin-top: 8px; font-size: 14px; color: #666;">${data.completed || 0} descriptions generated</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">${data.skipped || 0} rows skipped</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">${data.failed || 0} errors</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">Elapsed time: ${formatMetaDescriptionExcelTime(finalElapsed)}</div>
            `);

            const link = document.createElement("a");
            link.href = `${META_DESCRIPTION_BACKEND_URL}/download-meta-descriptions/${jobId}`;
            link.download = "meta_descriptions.xlsx";
            document.body.appendChild(link);
            link.click();
            link.remove();

            resetMetaDescriptionExcelButtons();
            return;
        }

        if (data.status === "cancelled" && data.download_ready) {
            const finalElapsed = metaDescriptionExcelStartTime
                ? (Date.now() - metaDescriptionExcelStartTime) / 1000
                : 0;

            showMetaDescriptionExcelProgress(`
                <strong>Generation stopped</strong>
                <div style="margin-top: 8px; font-size: 14px; color: #666;">${data.completed || 0} descriptions generated before stopping</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">Elapsed time: ${formatMetaDescriptionExcelTime(finalElapsed)}</div>
                <div style="margin-top: 6px; font-size: 14px; color: #666;">The partial Excel file will be downloaded.</div>
            `);

            const link = document.createElement("a");
            link.href = `${META_DESCRIPTION_BACKEND_URL}/download-meta-descriptions/${jobId}`;
            link.download = "meta_descriptions_partial.xlsx";
            document.body.appendChild(link);
            link.click();
            link.remove();

            resetMetaDescriptionExcelButtons();
            return;
        }

        if (data.status === "failed") {
            throw new Error(data.error || "Meta description Excel generation failed.");
        }

        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}

function resetMetaDescriptionExcelButtons() {
    metaDescExcelButton.disabled = false;
    metaDescExcelButton.textContent = "Generate Meta Descriptions";
    stopMetaDescExcelButton.style.display = "none";
    stopMetaDescExcelButton.disabled = false;
    stopMetaDescExcelButton.textContent = "Stop generation";
    currentMetaDescriptionExcelJobId = null;
    metaDescriptionExcelStartTime = null;
}

metaDescExcelButton.addEventListener("click", async () => {
    if (!metaDescExcelFile.files.length) {
        alert("Please choose an Excel file first.");
        return;
    }

    if (!metaDescExcelProductColumn.value) {
        alert("Please choose a Product name column first.");
        return;
    }

    metaDescExcelButton.disabled = true;
    metaDescExcelButton.textContent = "Starting...";
    stopMetaDescExcelButton.style.display = "inline-block";
    stopMetaDescExcelButton.disabled = false;
    stopMetaDescExcelButton.textContent = "Stop generation";
    metaDescriptionExcelStartTime = Date.now();
    showMetaDescriptionExcelProgress("Starting meta description generation...");

    try {
        const formData = new FormData();
        formData.append("file", metaDescExcelFile.files[0]);
        formData.append("brand_column", metaDescExcelBrandColumn.value);
        formData.append("product_column", metaDescExcelProductColumn.value);
        formData.append("description_column", metaDescExcelDescriptionColumn.value);

        const response = await fetch(`${META_DESCRIPTION_BACKEND_URL}/generate-meta-descriptions`, {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Backend returned HTTP ${response.status}.`);
        }

        currentMetaDescriptionExcelJobId = data.job_id;
        await monitorMetaDescriptionExcelProgress(data.job_id);
    } catch (error) {
        console.error("Meta description Excel error:", error);
        showMetaDescriptionExcelProgress("Meta description generation failed.");
        alert("Meta description Excel generation failed.\n\nError: " + (error.message || error));
        resetMetaDescriptionExcelButtons();
    }
});

stopMetaDescExcelButton.addEventListener("click", async () => {
    if (!currentMetaDescriptionExcelJobId) {
        return;
    }

    stopMetaDescExcelButton.disabled = true;
    stopMetaDescExcelButton.textContent = "Stopping...";

    try {
        const response = await fetch(
            `${META_DESCRIPTION_BACKEND_URL}/stop-meta-descriptions/${currentMetaDescriptionExcelJobId}`,
            { method: "POST" }
        );
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Backend returned HTTP ${response.status}.`);
        }

        showMetaDescriptionExcelProgress(
            "Stopping generation...<br>Finishing requests that are already running."
        );
    } catch (error) {
        console.error("Meta description stop error:", error);
        alert("Could not stop the generation.\n\nError: " + (error.message || error));
        stopMetaDescExcelButton.disabled = false;
        stopMetaDescExcelButton.textContent = "Stop generation";
    }
});
