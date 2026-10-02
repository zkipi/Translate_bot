// ==========================================
// ELEMENTS
// ==========================================

const sourceText = document.getElementById("sourceText");
const targetLanguage = document.getElementById("targetLanguage");
const promptStyle = document.getElementById("promptStyle");
const translateButton = document.getElementById("translateButton");

const translatedText = document.getElementById("translatedText");
const detectedLanguage = document.getElementById("detectedLanguage");

const copyButton = document.getElementById("copyButton");
const exportButton = document.getElementById("exportButton");

const excelFile = document.getElementById("excelFile");
const selectedFile = document.getElementById("selectedFile");
const excelColumn = document.getElementById("excelColumn");
const excelTargetLanguage =
    document.getElementById("excelTargetLanguage");
const excelPromptStyle =
    document.getElementById("excelPromptStyle");
const excelButton = document.getElementById("excelButton");
const stopExcelButton =
    document.getElementById("stopExcelButton");


// ==========================================
// VARIABLES
// ==========================================

let detectedSourceLanguage = "";

let currentExcelJobId = null;

let excelTranslationStartTime = null;


// ==========================================
// TRANSLATE TEXT
// ==========================================

translateButton.addEventListener(
    "click",
    async () => {

        const text = sourceText.value.trim();
        const language = targetLanguage.value;
        const style = promptStyle.value;


        // --------------------------------------
        // CHECK INPUT
        // --------------------------------------

        if (!text) {

            alert(
                "Please enter a product description first."
            );

            return;
        }


        // --------------------------------------
        // BUTTON STATE
        // --------------------------------------

        translateButton.disabled = true;

        translateButton.textContent =
            "Translating...";


        translatedText.value = "";

        detectedLanguage.textContent =
            "Detecting language...";


        console.log(
            "Sending translation request:",
            {
                target_language: language,
                prompt_style: style,
                text_length: text.length
            }
        );


        try {

            // ----------------------------------
            // SEND REQUEST
            // ----------------------------------

            const response = await fetch(
                "http://127.0.0.1:5000/translate",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        text: text,
                        target_language: language,
                        prompt_style: style
                    })
                }
            );


            console.log(
                "Backend response:",
                response.status
            );


            // ----------------------------------
            // READ RESPONSE
            // ----------------------------------

            let data;

            try {

                data = await response.json();

            } catch {

                throw new Error(
                    `Backend returned an invalid response ` +
                    `(HTTP ${response.status}).`
                );
            }


            // ----------------------------------
            // CHECK HTTP STATUS
            // ----------------------------------

            if (!response.ok) {

                throw new Error(
                    data.error ||
                    `Backend returned HTTP ${response.status}.`
                );
            }


            // ----------------------------------
            // CHECK TRANSLATION
            // ----------------------------------

            if (
                !data.translation &&
                data.translation !== ""
            ) {

                throw new Error(
                    "Backend returned no translation."
                );
            }


            // ----------------------------------
            // DISPLAY RESULT
            // ----------------------------------

            translatedText.value =
                data.translation;


            detectedSourceLanguage =
                data.source_language;


            detectedLanguage.textContent =
                `Detected language: ` +
                `${data.source_language} → ` +
                `${data.target_language}`;


            console.log(
                "Translation successful."
            );


        } catch (error) {

            console.error(
                "Translation error:",
                error
            );


            let message =
                "Translation failed.";


            if (
                error instanceof TypeError
            ) {

                message =
                    "Could not connect to the backend.\n\n" +
                    "Make sure the backend is running:\n" +
                    "python Backend/app.py\n\n" +
                    "If the backend is already running, " +
                    "open F12 → Console for more details.";

            } else {

                message =
                    "Translation failed.\n\n" +
                    "Error: " +
                    (error.message || error) +
                    "\n\n" +
                    "Open F12 → Console for more details.";
            }


            alert(message);


            translatedText.value = "";

            detectedLanguage.textContent =
                "Detected language: -";


        } finally {

            translateButton.disabled = false;

            translateButton.textContent =
                "Translate";
        }
    }
);


// ==========================================
// COPY TRANSLATION
// ==========================================

copyButton.addEventListener(
    "click",
    async () => {

        const text =
            translatedText.value;


        if (!text) {

            alert(
                "There is no translation to copy."
            );

            return;
        }


        try {

            await navigator.clipboard.writeText(
                text
            );


            copyButton.textContent =
                "Copied!";


            setTimeout(
                () => {

                    copyButton.textContent =
                        "Copy";

                },
                1500
            );


        } catch (error) {

            console.error(
                "Copy error:",
                error
            );


            alert(
                "Could not copy the translation."
            );
        }
    }
);


// ==========================================
// EXPORT SINGLE TRANSLATION
// ==========================================

exportButton.addEventListener(
    "click",
    async () => {

        const originalText =
            sourceText.value.trim();

        const translation =
            translatedText.value.trim();

        const target =
            targetLanguage.value;


        if (!originalText) {

            alert(
                "Please enter a product description first."
            );

            return;
        }


        if (!translation) {

            alert(
                "Please translate the description first."
            );

            return;
        }


        try {

            const response = await fetch(
                "http://127.0.0.1:5000/export-excel",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        original_text:
                            originalText,

                        translation:
                            translation,

                        source_language:
                            detectedSourceLanguage,

                        target_language:
                            target
                    })
                }
            );


            if (!response.ok) {

                let data = {};

                try {

                    data =
                        await response.json();

                } catch {
                    // Ignore invalid JSON
                }


                throw new Error(
                    data.error ||
                    `Backend returned HTTP ${response.status}.`
                );
            }


            const blob =
                await response.blob();


            const url =
                window.URL.createObjectURL(
                    blob
                );


            const link =
                document.createElement("a");


            link.href = url;

            link.download =
                "translated_product.xlsx";


            document.body.appendChild(link);

            link.click();

            link.remove();


            window.URL.revokeObjectURL(
                url
            );


        } catch (error) {

            console.error(
                "Export error:",
                error
            );


            alert(
                "Could not export the Excel file.\n\n" +
                "Error: " +
                (error.message || error)
            );
        }
    }
);


// ==========================================
// EXCEL FILE SELECTION
// ==========================================

excelFile.addEventListener(
    "change",
    () => {

        if (excelFile.files.length) {

            selectedFile.textContent =
                excelFile.files[0].name;

        } else {

            selectedFile.textContent =
                "No file selected";
        }
    }
);


// ==========================================
// LOAD EXCEL COLUMNS
// ==========================================

excelFile.addEventListener(
    "change",
    async () => {

        excelColumn.innerHTML = "";
        excelColumn.disabled = true;

        if (!excelFile.files.length) {

            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Choose an Excel file first";
            excelColumn.appendChild(option);

            return;
        }

        const file = excelFile.files[0];

        const formData = new FormData();
        formData.append("file", file);

        const loadingOption = document.createElement("option");
        loadingOption.value = "";
        loadingOption.textContent = "Reading columns...";
        excelColumn.appendChild(loadingOption);

        try {

            const response = await fetch(
                "http://127.0.0.1:5000/excel-columns",
                {
                    method: "POST",
                    body: formData
                }
            );

            let data = {};

            try {
                data = await response.json();
            } catch {
                // Ignore invalid JSON
            }

            if (!response.ok) {
                throw new Error(
                    data.error ||
                    `Backend returned HTTP ${response.status}.`
                );
            }

            const columns = Array.isArray(data.columns)
                ? data.columns
                : [];

            if (!columns.length) {
                throw new Error(
                    "No columns were found in the Excel file."
                );
            }

            excelColumn.innerHTML = "";

            columns.forEach((column) => {

                const option = document.createElement("option");
                option.value = column;
                option.textContent = column;
                excelColumn.appendChild(option);
            });

            // Keep the old behaviour as the default when the file
            // contains a column named "description".
            if (columns.includes("description")) {
                excelColumn.value = "description";
            }

            excelColumn.disabled = false;

        } catch (error) {

            console.error(
                "Could not read Excel columns:",
                error
            );

            excelColumn.innerHTML = "";

            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Could not read columns";
            excelColumn.appendChild(option);

            alert(
                "Could not read the Excel columns.\n\n" +
                "Error: " +
                (error.message || error)
            );
        }
    }
);


// ==========================================
// TRANSLATE EXCEL
// ==========================================

excelButton.addEventListener(
    "click",
    async () => {

        if (!excelFile.files.length) {

            alert(
                "Please choose an Excel file first."
            );

            return;
        }


        if (!excelColumn.value) {

            alert(
                "Please choose a column to translate first."
            );

            return;
        }


        const file =
            excelFile.files[0];

        const language =
            excelTargetLanguage.value;

        const style =
            excelPromptStyle.value;

        const sourceColumn =
            excelColumn.value;


        excelButton.disabled = true;

        excelButton.textContent =
            "Starting...";

        stopExcelButton.style.display =
            "inline-block";

        stopExcelButton.disabled =
            false;

        stopExcelButton.textContent =
            "Stop translation";


        excelTranslationStartTime =
            Date.now();


        showExcelProgress(
            "Starting translation..."
        );


        try {

            const formData =
                new FormData();


            // ----------------------------------
            // ADD FORM DATA
            // ----------------------------------

            formData.append(
                "file",
                file
            );


            formData.append(
                "target_language",
                language
            );


            formData.append(
                "prompt_style",
                style
            );

            formData.append(
                "source_column",
                sourceColumn
            );


            console.log(
                "Starting Excel translation:",
                {
                    file: file.name,
                    target_language: language,
                    prompt_style: style,
                    source_column: sourceColumn,
                    file_size: file.size
                }
            );


            // ----------------------------------
            // SEND REQUEST
            // ----------------------------------

            const response = await fetch(
                "http://127.0.0.1:5000/translate-excel",
                {
                    method: "POST",
                    body: formData
                }
            );


            console.log(
                "Excel backend response:",
                response.status
            );


            // ----------------------------------
            // READ RESPONSE
            // ----------------------------------

            let data;

            try {

                data =
                    await response.json();

            } catch {

                throw new Error(
                    `Backend returned an invalid response ` +
                    `(HTTP ${response.status}).`
                );
            }


            // ----------------------------------
            // CHECK RESPONSE
            // ----------------------------------

            if (!response.ok) {

                throw new Error(
                    data.error ||
                    `Backend returned HTTP ${response.status}.`
                );
            }


            const jobId =
                data.job_id;

            currentExcelJobId =
                jobId;


            console.log(
                "Excel translation job started:",
                jobId
            );


            await monitorExcelProgress(
                jobId
            );


        } catch (error) {

            console.error(
                "Excel translation error:",
                error
            );


            showExcelProgress(
                "Translation failed."
            );


            let message;


            if (
                error instanceof TypeError
            ) {

                message =
                    "Could not connect to the backend.\n\n" +
                    "Make sure the backend is running:\n" +
                    "python Backend/app.py";

            } else {

                message =
                    "Excel translation failed.\n\n" +
                    "Error: " +
                    (error.message || error);
            }


            alert(message);


            excelButton.disabled = false;

            excelButton.textContent =
                "Translate Excel";

            stopExcelButton.style.display =
                "none";

            stopExcelButton.disabled =
                false;

            stopExcelButton.textContent =
                "Stop translation";

            currentExcelJobId =
                null;

            excelTranslationStartTime =
                null;
        }
    }
);


// ==========================================
// STOP EXCEL TRANSLATION
// ==========================================

stopExcelButton.addEventListener(
    "click",
    async () => {

        if (!currentExcelJobId) {
            return;
        }


        stopExcelButton.disabled =
            true;

        stopExcelButton.textContent =
            "Stopping...";


        try {

            const response = await fetch(
                `http://127.0.0.1:5000/stop-excel/${currentExcelJobId}`,
                {
                    method: "POST"
                }
            );


            let data = {};

            try {
                data = await response.json();
            } catch {
                // Ignore invalid JSON
            }


            if (!response.ok) {

                throw new Error(
                    data.error ||
                    `Backend returned HTTP ${response.status}.`
                );
            }


            showExcelProgress(
                "Stopping translation...<br>" +
                "Finishing requests that are already running."
            );


        } catch (error) {

            console.error(
                "Stop error:",
                error
            );


            alert(
                "Could not stop the translation.\n\n" +
                "Error: " +
                (error.message || error)
            );


            stopExcelButton.disabled =
                false;

            stopExcelButton.textContent =
                "Stop translation";
        }
    }
);


// ==========================================
// EXCEL PROGRESS UI
// ==========================================

function showExcelProgress(message) {

    let progressContainer =
        document.getElementById(
            "excelProgress"
        );


    if (!progressContainer) {

        progressContainer =
            document.createElement(
                "div"
            );


        progressContainer.id =
            "excelProgress";


        progressContainer.style.marginTop =
            "20px";


        progressContainer.style.padding =
            "15px";


        progressContainer.style.background =
            "#f4f6f8";


        progressContainer.style.borderRadius =
            "8px";


        excelButton.parentNode.appendChild(
            progressContainer
        );
    }


    progressContainer.innerHTML =
        message;
}


// ==========================================
// MONITOR EXCEL PROGRESS
// ==========================================

async function monitorExcelProgress(
    jobId
) {

    while (true) {

        const response = await fetch(
            `http://127.0.0.1:5000/translation-status/${jobId}`
        );


        console.log(
            "Progress response:",
            response.status
        );


        let data;

        try {

            data =
                await response.json();

        } catch {

            throw new Error(
                `Could not read backend progress ` +
                `(HTTP ${response.status}).`
            );
        }


        if (!response.ok) {

            throw new Error(
                data.error ||
                `Backend returned HTTP ${response.status}.`
            );
        }


        // --------------------------------------
        // CALCULATE PROGRESS
        // --------------------------------------

        let percentage = 0;


        if (data.total > 0) {

            percentage =
                Math.round(
                    (
                        data.current /
                        data.total
                    ) * 100
                );
        }


        // --------------------------------------
        // CALCULATE TIME
        // --------------------------------------

        let elapsedSeconds = 0;
        let remainingSeconds = null;


        if (excelTranslationStartTime) {

            elapsedSeconds =
                (Date.now() - excelTranslationStartTime) /
                1000;
        }


        // Use completed/current rows to estimate the remaining time.
        // Wait until at least 3 rows are done so the estimate is not
        // based on the very first request.
        if (
            data.current >= 3 &&
            data.total > data.current &&
            elapsedSeconds > 0
        ) {

            const averageSecondsPerRow =
                elapsedSeconds / data.current;

            remainingSeconds =
                averageSecondsPerRow *
                (data.total - data.current);
        }


        function formatTime(seconds) {

            if (seconds === null) {
                return "Calculating...";
            }


            seconds = Math.max(
                0,
                Math.round(seconds)
            );


            const hours =
                Math.floor(seconds / 3600);

            const minutes =
                Math.floor((seconds % 3600) / 60);

            const secs =
                seconds % 60;


            if (hours > 0) {

                return `${hours}h ${minutes}m`;
            }


            if (minutes > 0) {

                return `${minutes}m ${secs}s`;
            }


            return `${secs}s`;
        }


        const elapsedTime =
            formatTime(elapsedSeconds);


        const remainingTime =
            formatTime(remainingSeconds);


        // --------------------------------------
        // SHOW PROGRESS
        // --------------------------------------

        showExcelProgress(`

            <strong>
                Translating Excel...
            </strong>

            <div style="
                margin-top: 10px;
                background: #ddd;
                border-radius: 6px;
                height: 12px;
                overflow: hidden;
            ">

                <div style="
                    width: ${percentage}%;
                    height: 100%;
                    background: #1F4E78;
                    transition: width 0.3s;
                "></div>

            </div>

            <div style="
                margin-top: 8px;
                font-size: 14px;
                color: #666;
            ">

                ${data.current}
                /
                ${data.total}
                products
                (${percentage}%)

            </div>

            <div style="
                margin-top: 8px;
                font-size: 14px;
                color: #666;
            ">

                Elapsed time: ${elapsedTime}
                <br>
                Remaining time: ${remainingTime}

            </div>

            ${
                data.failed > 0
                ? `
                    <div style="
                        margin-top: 5px;
                        font-size: 13px;
                        color: #a33;
                    ">
                        Failed: ${data.failed}
                    </div>
                `
                : ""
            }

        `);


        // --------------------------------------
        // CANCELLED
        // --------------------------------------

        if (
            data.status === "cancelled" &&
            data.download_ready
        ) {

            showExcelProgress(`

                <strong>
                    Translation stopped
                </strong>

                <div style="
                    margin-top: 8px;
                    font-size: 14px;
                    color: #666;
                ">

                    ${data.current}
                    /
                    ${data.total}
                    products processed.

                </div>

                <div style="
                    margin-top: 10px;
                    font-size: 13px;
                    color: #666;
                ">

                    The partially translated Excel file
                    will be downloaded.

                </div>

                <div style="
                    margin-top: 8px;
                    font-size: 14px;
                    color: #666;
                ">
                    Elapsed time: ${elapsedTime}
                </div>

            `);


            const downloadUrl =
                `http://127.0.0.1:5000/download-excel/${jobId}`;


            const link =
                document.createElement("a");


            link.href =
                downloadUrl;

            link.download =
                "translated_products_partial.xlsx";


            document.body.appendChild(
                link
            );

            link.click();

            link.remove();


            excelButton.disabled =
                false;

            excelButton.textContent =
                "Translate Excel";

            stopExcelButton.style.display =
                "none";

            stopExcelButton.disabled =
                false;

            stopExcelButton.textContent =
                "Stop translation";

            currentExcelJobId =
                null;

            excelTranslationStartTime =
                null;


            return;
        }


        // --------------------------------------
        // COMPLETED
        // --------------------------------------

        if (
            data.status === "completed" &&
            data.download_ready
        ) {

            showExcelProgress(`

                <strong>
                    Translation complete ✓
                </strong>

                <div style="
                    margin-top: 8px;
                    font-size: 14px;
                    color: #666;
                ">
                    ${data.total} rows processed
                </div>

                <div style="
                    margin-top: 8px;
                    font-size: 14px;
                    color: #666;
                ">
                    Elapsed time: ${elapsedTime}
                </div>

                <div style="
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 8px 16px;
                    margin-top: 14px;
                    font-size: 14px;
                ">

                    <div>
                        ✓ ${data.ok_count ?? 0} OK
                    </div>

                    <div>
                        ⚠ ${data.corrected_count ?? 0}
                        corrected automatically
                    </div>

                    <div>
                        🔍 ${data.review_count ?? 0}
                        review required
                    </div>

                    <div>
                        — ${data.skipped_count ?? 0}
                        skipped
                    </div>

                    <div>
                        ✕ ${data.failed ?? 0}
                        errors
                    </div>

                </div>

                ${
                    data.review_count > 0
                    ? `
                        <div style="
                            margin-top: 14px;
                            padding: 10px 12px;
                            background: #fff4e5;
                            border-radius: 6px;
                            font-size: 13px;
                        ">
                            ${data.review_count}
                            row(s) need manual review.

                            Check the
                            <strong>
                                translation_check
                            </strong>
                            and
                            <strong>
                                translation_issues
                            </strong>
                            columns in the Excel file.
                        </div>
                    `
                    : ""
                }

            `);


            // ----------------------------------
            // DOWNLOAD FILE
            // ----------------------------------

            const downloadUrl =
                `http://127.0.0.1:5000/download-excel/${jobId}`;


            const link =
                document.createElement("a");


            link.href =
                downloadUrl;


            link.download =
                "translated_products.xlsx";


            document.body.appendChild(link);


            link.click();

            link.remove();


            // ----------------------------------
            // RESET BUTTON
            // ----------------------------------

            excelButton.disabled =
                false;


            excelButton.textContent =
                "Translate Excel";

            stopExcelButton.style.display =
                "none";

            stopExcelButton.disabled =
                false;

            stopExcelButton.textContent =
                "Stop translation";

            currentExcelJobId =
                null;

            excelTranslationStartTime =
                null;


            return;
        }


        // --------------------------------------
        // FAILED
        // --------------------------------------

        if (
            data.status === "failed"
        ) {

            throw new Error(
                data.error ||
                "Excel translation failed."
            );
        }


        // --------------------------------------
        // WAIT
        // --------------------------------------

        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    1000
                )
        );
    }
}