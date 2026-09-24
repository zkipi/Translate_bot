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


        // Check text

        if (!text) {

            alert(
                "Please enter a description first."
            );

            return;
        }


        // Disable button

        translateButton.disabled = true;

        translateButton.textContent =
            "Translating...";


        // Clear previous result

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


            // Store source language

            detectedSourceLanguage =
                data.source_language;


            // Show translation

            translatedText.value =
                data.translation;


            // Show languages

            detectedLanguage.textContent =
                `Detected language: ${data.source_language} → ${data.target_language}`;


            // Enable buttons

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


        // Enable button

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
// EXPORT SINGLE TRANSLATION TO EXCEL
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


        // Disable button

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

        // Check file

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


        // Disable button

        excelButton.disabled = true;

        excelButton.textContent =
            "Translating Excel...";


        try {

            // Create form data

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


            // Send Excel to backend

            const response = await fetch(
                "http://127.0.0.1:5000/translate-excel",
                {
                    method: "POST",

                    body: formData
                }
            );


            // Check response

            if (!response.ok) {

                const data =
                    await response.json();

                throw new Error(
                    data.error ||
                    "Excel translation failed."
                );
            }


            // Convert response to file

            const blob =
                await response.blob();


            // Create download URL

            const url =
                window.URL.createObjectURL(
                    blob
                );


            // Create download link

            const link =
                document.createElement("a");


            link.href = url;

            link.download =
                "translated_products.xlsx";


            document.body.appendChild(link);

            link.click();

            link.remove();


            // Clean up

            window.URL.revokeObjectURL(
                url
            );


            alert(
                "Excel translation completed!"
            );


        } catch (error) {

            console.error(
                "Excel translation error:",
                error
            );


            alert(
                error.message ||
                "Could not translate the Excel file."
            );

        }


        // Enable button

        excelButton.disabled = false;

        excelButton.textContent =
            "Translate Excel";

    }
);