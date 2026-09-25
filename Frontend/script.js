// ==========================================
// GET ELEMENTS
// ==========================================

const sourceText =
    document.getElementById("sourceText");

const translatedText =
    document.getElementById("translatedText");

const targetLanguage =
    document.getElementById("targetLanguage");

const translateButton =
    document.getElementById("translateButton");

const copyButton =
    document.getElementById("copyButton");

const exportButton =
    document.getElementById("exportButton");

const detectedLanguage =
    document.getElementById("detectedLanguage");

const excelFile =
    document.getElementById("excelFile");

const excelButton =
    document.getElementById("excelButton");

const excelTargetLanguage =
    document.getElementById("excelTargetLanguage");

const selectedFile =
    document.getElementById("selectedFile");


// ==========================================
// STORE TRANSLATION INFORMATION
// ==========================================

let detectedSourceLanguage = "";


// ==========================================
// INITIAL STATE
// ==========================================

copyButton.disabled = true;
exportButton.disabled = true;


// ==========================================
// TEXT TRANSLATOR
// ==========================================

translateButton.addEventListener(
    "click",
    async () => {

        const text =
            sourceText.value.trim();

        const language =
            targetLanguage.value;


        if (!text) {

            alert(
                "Please enter a description first."
            );

            return;
        }


        translateButton.disabled = true;

        translateButton.textContent =
            "Translating...";


        translatedText.value = "";

        detectedLanguage.textContent =
            "Translating...";


        copyButton.disabled = true;

        exportButton.disabled = true;


        try {

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

                        target_language:
                            language

                    })
                }
            );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.error ||
                    "Translation failed."
                );
            }


            detectedSourceLanguage =
                data.source_language;


            translatedText.value =
                data.translation;


            detectedLanguage.textContent =
                `Detected language: ${data.source_language} → ${data.target_language}`;


            copyButton.disabled = false;

            exportButton.disabled = false;


        } catch (error) {

            console.error(
                "Translation error:",
                error
            );


            translatedText.value =
                "Translation failed.";


            detectedLanguage.textContent =
                "Translation failed";


            alert(
                "Could not translate the text. " +
                "Please check that the backend is running."
            );

        }


        translateButton.disabled = false;

        translateButton.textContent =
            "Translate";

    }
);


// ==========================================
// COPY TRANSLATION
// ==========================================

copyButton.addEventListener(
    "click",
    async () => {

        const translation =
            translatedText.value.trim();


        if (!translation) {

            return;
        }


        try {

            await navigator.clipboard.writeText(
                translation
            );


            const originalText =
                copyButton.textContent;


            copyButton.textContent =
                "Copied ✓";


            setTimeout(() => {

                copyButton.textContent =
                    originalText;

            }, 1500);


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


        if (!translation) {

            alert(
                "There is no translation to export."
            );

            return;
        }


        exportButton.disabled = true;

        exportButton.textContent =
            "Creating Excel...";


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

                const data =
                    await response.json();

                throw new Error(
                    data.error ||
                    "Excel export failed."
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
                "Excel export error:",
                error
            );


            alert(
                "Could not export the Excel file."
            );

        }


        exportButton.disabled = false;

        exportButton.textContent =
            "Export to Excel";

    }
);


// ==========================================
// EXCEL FILE SELECTION
// ==========================================

excelFile.addEventListener(
    "change",
    () => {

        if (!excelFile.files.length) {

            selectedFile.textContent =
                "No file selected";

            return;
        }


        const file =
            excelFile.files[0];


        selectedFile.textContent =
            `Selected file: ${file.name}`;

    }
);


// ==========================================
// EXCEL TRANSLATION
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


        const file =
            excelFile.files[0];

        const language =
            excelTargetLanguage.value;


        // --------------------------------------
        // DISABLE BUTTON
        // --------------------------------------

        excelButton.disabled = true;

        excelButton.textContent =
            "Starting...";


        // --------------------------------------
        // SHOW PROGRESS
        // --------------------------------------

        showExcelProgress(
            "Starting translation..."
        );


        try {

            // ----------------------------------
            // CREATE FORM DATA
            // ----------------------------------

            const formData =
                new FormData();


            formData.append(
                "file",
                file
            );


            formData.append(
                "target_language",
                language
            );


            // ----------------------------------
            // START JOB
            // ----------------------------------

            const response = await fetch(
                "http://127.0.0.1:5000/translate-excel",
                {
                    method: "POST",

                    body: formData
                }
            );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.error ||
                    "Could not start Excel translation."
                );
            }


            const jobId =
                data.job_id;


            // ----------------------------------
            // CHECK PROGRESS
            // ----------------------------------

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


            alert(
                error.message ||
                "Could not translate the Excel file."
            );


            excelButton.disabled = false;

            excelButton.textContent =
                "Translate Excel";
        }

    }
);


// ==========================================
// SHOW EXCEL PROGRESS
// ==========================================

function showExcelProgress(message) {

    let progressContainer =
        document.getElementById(
            "excelProgress"
        );


    // Create progress area if it doesn't exist

    if (!progressContainer) {

        progressContainer =
            document.createElement("div");

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


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Could not get translation status."
            );
        }


        // ----------------------------------
        // CALCULATE PERCENTAGE
        // ----------------------------------

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


        // ----------------------------------
        // SHOW PROGRESS
        // ----------------------------------

        showExcelProgress(`
            <strong>Translating Excel...</strong>

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
                ${data.current} / ${data.total}
                products
                (${percentage}%)
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


        // ----------------------------------
        // COMPLETED
        // ----------------------------------

        if (
            data.status === "completed"
            && data.download_ready
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
                    ${data.completed}
                    / ${data.total}
                    products translated.
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


            // --------------------------------
            // DOWNLOAD
            // --------------------------------

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


            // --------------------------------
            // RESET BUTTON
            // --------------------------------

            excelButton.disabled = false;

            excelButton.textContent =
                "Translate Excel";


            return;
        }


        // ----------------------------------
        // FAILED
        // ----------------------------------

        if (data.status === "failed") {

            throw new Error(
                data.error ||
                "Excel translation failed."
            );
        }


        // ----------------------------------
        // WAIT 1 SECOND
        // ----------------------------------

        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    1000
                )
        );

    }

}