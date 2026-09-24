from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from translator import translate_text

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

import pandas as pd

from io import BytesIO


# ==========================================
# SETUP
# ==========================================

app = Flask(__name__)

CORS(app)


# ==========================================
# LANGUAGE COLUMN SUFFIX
# ==========================================

LANGUAGE_SUFFIXES = {
    "English": "en",
    "Swedish": "sv",
    "Danish": "da",
    "Norwegian": "no",
    "Finnish": "fi"
}


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return "Translate Bot is running!"


# ==========================================
# TRANSLATE TEXT
# ==========================================

@app.route("/translate", methods=["POST"])
def translate():

    data = request.get_json()

    text = data.get("text")
    target_language = data.get("target_language")


    # Check input

    if not text:

        return jsonify({
            "error": "No text provided"
        }), 400


    if not target_language:

        return jsonify({
            "error": "No target language provided"
        }), 400


    # Translate

    try:

        result = translate_text(
            text,
            target_language
        )


        return jsonify({

            "translation": result["translation"],

            "source_language": result["source_language"],

            "target_language": target_language

        })


    except Exception as error:

        print("Translation error:", error)

        return jsonify({
            "error": "Translation failed"
        }), 500


# ==========================================
# EXPORT SINGLE TRANSLATION TO EXCEL
# ==========================================

@app.route("/export-excel", methods=["POST"])
def export_excel():

    data = request.get_json()

    original_text = data.get("original_text")
    translation = data.get("translation")
    source_language = data.get("source_language")
    target_language = data.get("target_language")


    # Check input

    if not original_text:

        return jsonify({
            "error": "No original text provided"
        }), 400


    if not translation:

        return jsonify({
            "error": "No translation provided"
        }), 400


    # Create workbook

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Translation"


    # Headers

    worksheet["A1"] = "Original description"
    worksheet["B1"] = "Translation"
    worksheet["C1"] = "Source language"
    worksheet["D1"] = "Target language"


    # Header formatting

    for cell in worksheet[1]:

        cell.font = Font(
            bold=True
        )


    # Data

    worksheet["A2"] = original_text
    worksheet["B2"] = translation
    worksheet["C2"] = source_language
    worksheet["D2"] = target_language


    # Alignment

    worksheet["A2"].alignment = Alignment(
        wrap_text=True,
        vertical="top"
    )

    worksheet["B2"].alignment = Alignment(
        wrap_text=True,
        vertical="top"
    )

    worksheet["C2"].alignment = Alignment(
        vertical="top"
    )

    worksheet["D2"].alignment = Alignment(
        vertical="top"
    )


    # Column widths

    worksheet.column_dimensions["A"].width = 60
    worksheet.column_dimensions["B"].width = 60
    worksheet.column_dimensions["C"].width = 20
    worksheet.column_dimensions["D"].width = 20


    # Freeze header

    worksheet.freeze_panes = "A2"


    # Save to memory

    excel_file = BytesIO()

    workbook.save(excel_file)

    excel_file.seek(0)


    # Send file

    return send_file(
        excel_file,
        as_attachment=True,
        download_name="translated_product.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# ==========================================
# TRANSLATE EXCEL FILE
# ==========================================

@app.route("/translate-excel", methods=["POST"])
def translate_excel():

    # Check file

    if "file" not in request.files:

        return jsonify({
            "error": "No Excel file provided"
        }), 400


    file = request.files["file"]

    target_language = request.form.get(
        "target_language"
    )


    # Check language

    if not target_language:

        return jsonify({
            "error": "No target language provided"
        }), 400


    # Check file name

    if not file.filename:

        return jsonify({
            "error": "No file selected"
        }), 400


    # ==========================================
    # READ EXCEL FILE
    # ==========================================

    try:

        dataframe = pd.read_excel(file)

    except Exception as error:

        print("Excel read error:", error)

        return jsonify({
            "error": "Could not read the Excel file."
        }), 400


    # ==========================================
    # CHECK DESCRIPTION COLUMN
    # ==========================================

    if "description" not in dataframe.columns:

        return jsonify({
            "error": (
                'The Excel file must contain a column named '
                '"description".'
            )
        }), 400


    # ==========================================
    # CREATE TARGET COLUMN
    # ==========================================

    suffix = LANGUAGE_SUFFIXES.get(
        target_language,
        target_language.lower()
    )

    target_column = f"description_{suffix}"


    # ==========================================
    # TRANSLATE DESCRIPTIONS
    # ==========================================

    translations = []

    total_rows = len(dataframe)

    print(
        f"Starting Excel translation: "
        f"{total_rows} rows → {target_language}"
    )


    for index, value in enumerate(
        dataframe["description"]
    ):

        # Empty description

        if pd.isna(value) or str(value).strip() == "":

            translations.append("")

            continue


        text = str(value)


        try:

            result = translate_text(
                text,
                target_language
            )

            translation = result["translation"]

            translations.append(
                translation
            )


            print(
                f"Translated row "
                f"{index + 1}/{total_rows}"
            )


        except Exception as error:

            print(
                f"Translation error on row "
                f"{index + 1}:",
                error
            )

            # Keep cell empty if translation fails

            translations.append("")


    # ==========================================
    # ADD TRANSLATION COLUMN
    # ==========================================

    dataframe[target_column] = translations


    # ==========================================
    # CREATE OUTPUT FILE
    # ==========================================

    output_file = BytesIO()


    dataframe.to_excel(
        output_file,
        index=False,
        engine="openpyxl"
    )


    output_file.seek(0)


    # ==========================================
    # DOWNLOAD FILE NAME
    # ==========================================

    original_filename = file.filename

    if original_filename.lower().endswith(".xlsx"):

        output_filename = (
            original_filename[:-5]
            + f"_{suffix}.xlsx"
        )

    else:

        output_filename = (
            "translated_products.xlsx"
        )


    # ==========================================
    # SEND FILE
    # ==========================================

    return send_file(
        output_file,
        as_attachment=True,
        download_name=output_filename,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )