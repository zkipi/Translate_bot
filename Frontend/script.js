// ==========================================
// ELEMENTS
// ==========================================

const sourceText = document.getElementById("sourceText");
const targetLanguage = document.getElementById("targetLanguage");
const translateButton = document.getElementById("translateButton");

const translatedText = document.getElementById("translatedText");
const detectedLanguage = document.getElementById("detectedLanguage");

const copyButton = document.getElementById("copyButton");
const exportButton = document.getElementById("exportButton");

const excelFile = document.getElementById("excelFile");
const selectedFile = document.getElementById("selectedFile");
const excelTargetLanguage =
    document.getElementById("excelTargetLanguage");
const excelButton = document.getElementById("excelButton");


// ==========================================
// VARIABLES
// ==========================================

let detectedSourceLanguage = "";


// ==========================================
// TRANSLATE TEXT
// ==========================================

translateButton.addEventListener(
    "click",
    async () => {

        const text = sourceText.value.trim();
        const language = targetLanguage.value;


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


        // --------------------------------------
        // DEBUG LOG
        // --------------------------------------

        console.log(
            "Sending translation request:",
            {
                target_language: language,
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
                        target_language: language
                    })
                }
            );


            // ----------------------------------
            // DEBUG RESPONSE
            // ----------------------------------

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

            } catch (jsonError) {

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

            // ----------------------------------
            // LOG ERROR
            // ----------------------------------

            console.error(
                "Translation error:",
                error
            );


            // ----------------------------------
            // SHOW USEFUL ERROR
            // ----------------------------------

            let message =
                "Translation failed.";


            if (
                error instanceof TypeError
            ) {

                message =
                    "Could not connect to the backend.\n\n" +
                    "Make sure the backend is running:\n" +
                    "python backend/app.py\n\n" +
                    "If the backend is already running, " +
                    "open F12 → Console for more details.";
            }

            else {

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

            // ----------------------------------
            // RESET BUTTON
            // ----------------------------------

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


        const file =
            excelFile.files[0];

        const language =
            excelTargetLanguage.value;


        excelButton.disabled = true;

        excelButton.textContent =
            "Starting...";


        showExcelProgress(
            "Starting translation..."
        );


        try {

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


            console.log(
                "Starting Excel translation:",
                {
                    file: file.name,
                    target_language: language,
                    file_size: file.size
                }
            );


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


            if (!response.ok) {

                throw new Error(
                    data.error ||
                    `Backend returned HTTP ${response.status}.`
                );
            }


            const jobId =
                data.job_id;


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
                    "python backend/app.py";

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

                    ${data.completed}
                    /
                    ${data.total}
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


            const downloadUrl =
                `http://127.0.0.1:5000/download-excel/${jobId}`;


            const link =
                document.createElement("a");


            link.href =
                downloadUrl;


            link.download =
                "translated_products.xlsx";


            document.body.appendChild(
                link
            );


            link.click();

            link.remove();


            excelButton.disabled =
                false;


            excelButton.textContent =
                "Translate Excel";


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