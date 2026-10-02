from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from translator import translate_text, validate_with_grok_batch

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

import pandas as pd

from io import BytesIO

import threading
import uuid

from concurrent.futures import ThreadPoolExecutor, as_completed


# ==========================================
# SETUP
# ==========================================

app = Flask(__name__)

CORS(app)


# ==========================================
# LANGUAGE COLUMN SUFFIXES
# ==========================================

LANGUAGE_SUFFIXES = {
    "English": "en",
    "Swedish": "sv",
    "Danish": "da",
    "Norwegian": "no",
    "Finnish": "fi"
}


# ==========================================
# EXCEL JOB STORAGE
# ==========================================

excel_jobs = {}


# ==========================================
# EXCEL FORMATTING
# ==========================================

def format_worksheet(worksheet):

    # ------------------------------------------
    # COLORS
    # ------------------------------------------

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="1F4E78"
    )

    alternate_fill = PatternFill(
        fill_type="solid",
        fgColor="F2F6FA"
    )


    # ------------------------------------------
    # HEADER
    # ------------------------------------------

    header_font = Font(
        bold=True,
        color="FFFFFF"
    )


    for cell in worksheet[1]:

        cell.fill = header_fill

        cell.font = header_font

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )


    # ------------------------------------------
    # BODY
    # ------------------------------------------

    for row_number in range(
        2,
        worksheet.max_row + 1
    ):

        if row_number % 2 == 0:

            for cell in worksheet[row_number]:

                cell.fill = alternate_fill


        for cell in worksheet[row_number]:

            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True
            )


    # ------------------------------------------
    # COLUMN WIDTHS
    # ------------------------------------------

    for column in worksheet.columns:

        column_letter = (
            column[0].column_letter
        )

        header = worksheet[
            f"{column_letter}1"
        ].value


        # Description columns

        if (
            header == "description"
            or (
                isinstance(header, str)
                and header.startswith(
                    "description_"
                )
            )
        ):

            worksheet.column_dimensions[
                column_letter
            ].width = 60


        # Product name columns

        elif header in [
            "name",
            "title",
            "product_name"
        ]:

            worksheet.column_dimensions[
                column_letter
            ].width = 35


        # ID columns

        elif header in [
            "id",
            "ID"
        ]:

            worksheet.column_dimensions[
                column_letter
            ].width = 12


        # Translation status

        elif header in [
            "translation_check",
            "translation_issues"
        ]:

            worksheet.column_dimensions[
                column_letter
            ].width = 30


        # Other columns

        else:

            worksheet.column_dimensions[
                column_letter
            ].width = 20


    # ------------------------------------------
    # ROW HEIGHT
    # ------------------------------------------

    worksheet.row_dimensions[1].height = 25


    for row_number in range(
        2,
        worksheet.max_row + 1
    ):

        worksheet.row_dimensions[
            row_number
        ].height = 80


    # ------------------------------------------
    # BORDERS
    # ------------------------------------------

    thin_border = Border(
        bottom=Side(
            style="thin",
            color="D9E1F2"
        )
    )


    for row in worksheet.iter_rows(
        min_row=2
    ):

        for cell in row:

            cell.border = thin_border


    # ------------------------------------------
    # FREEZE HEADER
    # ------------------------------------------

    worksheet.freeze_panes = "A2"


    # ------------------------------------------
    # FILTER
    # ------------------------------------------

    if worksheet.max_row >= 2:

        worksheet.auto_filter.ref = (
            worksheet.dimensions
        )


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return "Translate Bot is running!"


# ==========================================
# TRANSLATE TEXT
# ==========================================

@app.route(
    "/translate",
    methods=["POST"]
)
def translate():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No request data provided"
        }), 400


    text = data.get("text")

    target_language = data.get(
        "target_language"
    )

    prompt_style = data.get(
        "prompt_style",
        "standard"
    )


    # ------------------------------------------
    # CHECK INPUT
    # ------------------------------------------

    if not text:

        return jsonify({
            "error": "No text provided"
        }), 400


    if not target_language:

        return jsonify({
            "error":
                "No target language provided"
        }), 400


    # ------------------------------------------
    # TRANSLATE
    # ------------------------------------------

    try:

        result = translate_text(
            text,
            target_language,
            prompt_style
        )


        return jsonify({

            "translation":
                result["translation"],

            "source_language":
                result["source_language"],

            "target_language":
                target_language,

            "validation_status":
                result.get(
                    "validation_status",
                    "OK"
                ),

            "validation_issues":
                result.get(
                    "validation_issues",
                    []
                )

        })


    except Exception as error:

        print(
            "Translation error:",
            error
        )


        return jsonify({
            "error":
                "Translation failed"
        }), 500


# ==========================================
# EXPORT SINGLE TRANSLATION
# ==========================================

@app.route(
    "/export-excel",
    methods=["POST"]
)
def export_excel():

    data = request.get_json()


    original_text = data.get(
        "original_text"
    )

    translation = data.get(
        "translation"
    )

    source_language = data.get(
        "source_language"
    )

    target_language = data.get(
        "target_language"
    )


    # ------------------------------------------
    # CHECK INPUT
    # ------------------------------------------

    if not original_text:

        return jsonify({
            "error":
                "No original text provided"
        }), 400


    if not translation:

        return jsonify({
            "error":
                "No translation provided"
        }), 400


    # ------------------------------------------
    # CREATE WORKBOOK
    # ------------------------------------------

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Translation"


    # ------------------------------------------
    # HEADERS
    # ------------------------------------------

    worksheet.append([
        "Original description",
        "Translation",
        "Source language",
        "Target language"
    ])


    # ------------------------------------------
    # DATA
    # ------------------------------------------

    worksheet.append([
        original_text,
        translation,
        source_language,
        target_language
    ])


    # ------------------------------------------
    # FORMAT
    # ------------------------------------------

    format_worksheet(
        worksheet
    )


    # ------------------------------------------
    # SAVE
    # ------------------------------------------

    excel_file = BytesIO()

    workbook.save(
        excel_file
    )

    excel_file.seek(0)


    # ------------------------------------------
    # SEND FILE
    # ------------------------------------------

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
# GET EXCEL COLUMNS
# ==========================================

@app.route(
    "/excel-columns",
    methods=["POST"]
)
def excel_columns():

    if "file" not in request.files:

        return jsonify({
            "error": "No Excel file provided"
        }), 400


    file = request.files["file"]


    if not file.filename:

        return jsonify({
            "error": "No file selected"
        }), 400


    try:

        dataframe = pd.read_excel(file, nrows=0)

        columns = [
            str(column)
            for column in dataframe.columns
        ]

        return jsonify({
            "columns": columns
        })


    except Exception as error:

        print(
            "Excel column read error:",
            error
        )

        return jsonify({
            "error":
                "Could not read the Excel file."
        }), 400


# ==========================================
# START EXCEL TRANSLATION JOB
# ==========================================

@app.route(
    "/translate-excel",
    methods=["POST"]
)
def translate_excel():

    # ------------------------------------------
    # CHECK FILE
    # ------------------------------------------

    if "file" not in request.files:

        return jsonify({
            "error":
                "No Excel file provided"
        }), 400


    file = request.files["file"]


    target_language = request.form.get(
        "target_language"
    )


    prompt_style = request.form.get(
        "prompt_style",
        "standard"
    )


    source_column = request.form.get(
        "source_column",
        "description"
    )


    # ------------------------------------------
    # CHECK LANGUAGE
    # ------------------------------------------

    if not target_language:

        return jsonify({
            "error":
                "No target language provided"
        }), 400


    # ------------------------------------------
    # CHECK FILE
    # ------------------------------------------

    if not file.filename:

        return jsonify({
            "error":
                "No file selected"
        }), 400


    # ------------------------------------------
    # READ EXCEL
    # ------------------------------------------

    try:

        dataframe = pd.read_excel(
            file
        )


    except Exception as error:

        print(
            "Excel read error:",
            error
        )


        return jsonify({
            "error":
                "Could not read the Excel file."
        }), 400


    # ------------------------------------------
    # CHECK SOURCE COLUMN
    # ------------------------------------------

    if source_column not in dataframe.columns:

        return jsonify({
            "error":
                f'The selected column "{source_column}" '
                'does not exist in the Excel file.'
        }), 400


    # ------------------------------------------
    # CREATE JOB
    # ------------------------------------------

    job_id = str(
        uuid.uuid4()
    )


    total_rows = len(
        dataframe
    )


    excel_jobs[job_id] = {

        "status": "processing",

        "current": 0,

        "total": total_rows,

        "completed": 0,

        "failed": 0,

        "ok_count": 0,

        "corrected_count": 0,

        "review_count": 0,

        "skipped_count": 0,

        "download_ready": False,

        "file": None,

        "error": None,

        "source_column": source_column,

        "cancel_event": threading.Event()

    }


    # ------------------------------------------
    # START BACKGROUND THREAD
    # ------------------------------------------

    thread = threading.Thread(

        target=process_excel_translation,

        args=(

            job_id,

            dataframe,

            target_language,

            prompt_style,

            source_column

        )

    )


    thread.start()


    # ------------------------------------------
    # RETURN JOB ID
    # ------------------------------------------

    return jsonify({

        "job_id": job_id,

        "total": total_rows

    })


# ==========================================
# PROCESS EXCEL TRANSLATION
# ==========================================

def process_excel_translation(
    job_id,
    dataframe,
    target_language,
    prompt_style,
    source_column
):

    try:

        cancel_event = excel_jobs[job_id]["cancel_event"]

        # --------------------------------------
        # TARGET COLUMN
        # --------------------------------------

        suffix = LANGUAGE_SUFFIXES.get(
            target_language,
            target_language.lower()
        )


        target_column = (
            f"{source_column}_{suffix}"
        )


        total_rows = len(
            dataframe
        )


        translations = [
            ""
        ] * total_rows


        validation_statuses = [
            ""
        ] * total_rows


        validation_issues = [
            ""
        ] * total_rows


        # --------------------------------------
        # PARALLEL REQUEST SETTINGS
        # --------------------------------------

        MAX_WORKERS = 10


        print()
        print(
            "=========================================="
        )

        print(
            f"Starting Excel translation job {job_id}"
        )

        print(
            f"Target language: {target_language}"
        )

        print(
            f"Translation style: {prompt_style}"
        )

        print(
            f"Source column: {source_column}"
        )

        print(
            f"Output column: {target_column}"
        )

        print(
            f"Rows: {total_rows}"
        )

        print(
            f"Workers: {MAX_WORKERS}"
        )

        print(
            "=========================================="
        )

        print()


        # --------------------------------------
        # TRANSLATE ONE ROW
        # --------------------------------------

        def translate_row(
            index,
            value
        ):

            # Do not start new translations after Stop is pressed.
            if cancel_event.is_set():

                return (
                    index,
                    "",
                    "Cancelled",
                    None,
                    "cancelled",
                    index + 2
                )


            # Excel row number is +2 because:
            #
            # Row 1 = headers
            # Row 2 = dataframe index 0

            excel_row = index + 2


            # ----------------------------------
            # EMPTY CELL
            # ----------------------------------

            if pd.isna(value):

                return (
                    index,
                    "",
                    "Skipped",
                    None,
                    "skipped",
                    excel_row
                )


            # ----------------------------------
            # CONVERT TO TEXT
            # ----------------------------------

            text = str(value).strip()


            # ----------------------------------
            # EMPTY STRING
            # ----------------------------------

            if not text:

                return (
                    index,
                    "",
                    "Skipped",
                    None,
                    "skipped",
                    excel_row
                )


            # ----------------------------------
            # PUNCTUATION ONLY
            # ----------------------------------

            if not any(
                character.isalnum()
                for character in text
            ):

                return (
                    index,
                    text,
                    "Skipped",
                    None,
                    "skipped",
                    excel_row
                )


            # ----------------------------------
            # TRANSLATE
            # ----------------------------------

            try:

                result = translate_text(

                    text,

                    target_language,

                    prompt_style

                )


                translation = (
                    result["translation"]
                )


                validation_status = (
                    result.get(
                        "validation_status",
                        "OK"
                    )
                )


                validation_issue_list = (
                    result.get(
                        "validation_issues",
                        []
                    )
                )


                # ----------------------------------
                # FORMAT ISSUES
                # ----------------------------------

                if isinstance(
                    validation_issue_list,
                    list
                ):

                    issue_text = ", ".join(
                        str(issue)
                        for issue
                        in validation_issue_list
                    )

                else:

                    issue_text = str(
                        validation_issue_list
                    )


                # ----------------------------------
                # NORMALIZE STATUS
                # ----------------------------------

                if validation_status == "OK":

                    terminal_status = "OK"

                elif (
                    validation_status
                    == "Corrected automatically"
                ):

                    terminal_status = (
                        "Corrected automatically"
                    )

                elif (
                    validation_status
                    == "Review required"
                ):

                    terminal_status = (
                        "Review required"
                    )

                else:

                    terminal_status = (
                        validation_status
                    )


                return (

                    index,

                    translation,

                    terminal_status,

                    issue_text,

                    "completed",

                    excel_row

                )


            except Exception as error:

                print(
                    f"Translation error on "
                    f"Excel row {excel_row}: "
                    f"{error}"
                )


                return (

                    index,

                    "",

                    "Error",

                    str(error),

                    "failed",

                    excel_row

                )


        # --------------------------------------
        # RUN TRANSLATIONS IN PARALLEL
        # --------------------------------------

        # Counts rows that were actually processed.
        # Cancelled queued rows are NOT included.
        processed_count = 0

        with ThreadPoolExecutor(
            max_workers=MAX_WORKERS
        ) as executor:

            futures = [

                executor.submit(

                    translate_row,

                    index,

                    value

                )

                for index, value

                in enumerate(
                    dataframe[source_column]
                )

            ]


            # ----------------------------------
            # HANDLE COMPLETED REQUESTS
            # ----------------------------------

            for completed_count, future in enumerate(

                as_completed(futures),

                start=1

            ):

                (

                    index,

                    translation,

                    validation_status,

                    issue_text,

                    processing_status,

                    excel_row

                ) = future.result()


                # ----------------------------------
                # HANDLE CANCELLED ROW
                # ----------------------------------

                # A queued row can reach translate_row after Stop
                # was pressed. It returns "cancelled" before making
                # a Gemini request. Do NOT count that row as processed.
                if processing_status == "cancelled":

                    translations[index] = ""

                    validation_statuses[index] = ""

                    validation_issues[index] = ""

                    continue


                # ----------------------------------
                # STORE TRANSLATION
                # ----------------------------------

                translations[index] = (
                    translation
                )


                # ----------------------------------
                # STORE VALIDATION STATUS
                # ----------------------------------

                if processing_status == "skipped":

                    validation_statuses[index] = (
                        "Skipped"
                    )

                    validation_issues[index] = ""


                    excel_jobs[job_id][
                        "skipped_count"
                    ] += 1


                    print(
                        f"[Row {excel_row}] "
                        f"- Skipped"
                    )


                elif processing_status == "failed":

                    validation_statuses[index] = (
                        "Review required"
                    )

                    validation_issues[index] = (
                        f"translation_error: "
                        f"{issue_text}"
                    )


                    excel_jobs[job_id][
                        "failed"
                    ] += 1


                    excel_jobs[job_id][
                        "review_count"
                    ] += 1


                    print(
                        f"[Row {excel_row}] "
                        f"✕ Error"
                    )

                    print(
                        f"           Reason: "
                        f"{issue_text}"
                    )


                else:

                    validation_statuses[index] = (
                        validation_status
                    )

                    validation_issues[index] = (
                        issue_text
                    )


                    excel_jobs[job_id][
                        "completed"
                    ] += 1


                    # ----------------------------------
                    # COUNT VALIDATION STATUS
                    # ----------------------------------

                    if validation_status == "OK":

                        excel_jobs[job_id][
                            "ok_count"
                        ] += 1


                        print(
                            f"[Row {excel_row}] "
                            f"✓ OK"
                        )


                    elif (
                        validation_status
                        == "Corrected automatically"
                    ):

                        excel_jobs[job_id][
                            "corrected_count"
                        ] += 1


                        print(
                            f"[Row {excel_row}] "
                            f"⚠ Corrected automatically"
                        )


                        if issue_text:

                            print(
                                f"           Reason: "
                                f"{issue_text}"
                            )


                    elif (
                        validation_status
                        == "Review required"
                    ):

                        excel_jobs[job_id][
                            "review_count"
                        ] += 1


                        print(
                            f"[Row {excel_row}] "
                            f"🔍 Review required"
                        )


                        if issue_text:

                            print(
                                f"           Reason: "
                                f"{issue_text}"
                            )


                    else:

                        print(
                            f"[Row {excel_row}] "
                            f"✓ {validation_status}"
                        )


                # ----------------------------------
                # UPDATE PROGRESS
                # ----------------------------------

                # Only rows that actually completed, were skipped,
                # or failed count as processed. Cancelled rows do not.
                processed_count += 1

                excel_jobs[job_id][
                    "current"
                ] = processed_count

                excel_jobs[job_id][
                    "completed"
                ] = processed_count


        # --------------------------------------
        # AI VALIDATION WITH GROK 4.7
        # --------------------------------------

        # Python/local validation has already run during the Composer
        # translation phase. Grok now handles only semantic/language QA.
        # Several products are sent in each Grok request to reduce the
        # number of API calls and repeated prompt overhead.

        validation_indexes = [
            index
            for index, translation in enumerate(translations)
            if str(translation).strip()
        ]

        VALIDATOR_BATCH_SIZE = 1

        print()
        print(
            "=========================================="
        )
        print(
            "Starting AI validation with Grok 4.7"
        )
        print(
            f"Translations to validate: {len(validation_indexes)}"
        )
        print(
            f"Products per Grok request: {VALIDATOR_BATCH_SIZE}"
        )
        print(
            f"Parallel Grok requests: {MAX_WORKERS}"
        )
        print(
            "=========================================="
        )
        print()

        if validation_indexes and not cancel_event.is_set():
            excel_jobs[job_id]["current"] = max(
                0,
                total_rows - 1
            )

        # Build small batches. Five products keeps each request reasonably
        # sized while cutting the number of Grok requests by about 5x.
        validation_batches = [
            validation_indexes[start_index:start_index + VALIDATOR_BATCH_SIZE]
            for start_index in range(
                0,
                len(validation_indexes),
                VALIDATOR_BATCH_SIZE
            )
        ]

        def validate_batch_with_grok(batch_number, indexes):
            if cancel_event.is_set():
                return batch_number, "cancelled", None

            products = []
            for index in indexes:
                products.append({
                    "id": index,
                    "original": dataframe.iloc[index][source_column],
                    "translation": translations[index],
                    "local_issues": validation_issues[index]
                })

            try:
                result = validate_with_grok_batch(
                    products,
                    target_language,
                    prompt_style
                )
                return batch_number, "completed", result

            except Exception as error:
                return batch_number, "failed", str(error)

        validation_processed = 0

        if validation_batches and not cancel_event.is_set():
            with ThreadPoolExecutor(
                max_workers=MAX_WORKERS
            ) as validator_executor:

                validation_futures = [
                    validator_executor.submit(
                        validate_batch_with_grok,
                        batch_number,
                        batch_indexes
                    )
                    for batch_number, batch_indexes
                    in enumerate(validation_batches, start=1)
                ]

                for future in as_completed(validation_futures):
                    batch_number, processing_status, validation_result = (
                        future.result()
                    )

                    if processing_status == "cancelled":
                        continue

                    batch_indexes = validation_batches[batch_number - 1]
                    validation_processed += len(batch_indexes)

                    # ----------------------------------
                    # GROK BATCH ERROR
                    # ----------------------------------

                    if processing_status == "failed":
                        for index in batch_indexes:
                            existing = validation_issues[index]
                            ai_error = (
                                "ai_validator_error: "
                                + str(validation_result)
                            )

                            validation_issues[index] = (
                                f"{existing}; {ai_error}"
                                if existing
                                else ai_error
                            )

                            validation_statuses[index] = (
                                "Review required"
                            )

                        print(
                            f"[Grok batch {batch_number}] "
                            f"🔍 AI validator error"
                        )
                        print(
                            f"           Rows: "
                            f"{', '.join(str(index + 2) for index in batch_indexes)}"
                        )
                        print(
                            f"           Reason: {validation_result}"
                        )

                    else:
                        # ----------------------------------
                        # COMBINE LOCAL + AI VALIDATION
                        # ----------------------------------

                        for index in batch_indexes:
                            validation_result_for_row = (
                                validation_result.get(index)
                            )

                            if validation_result_for_row is None:
                                validation_statuses[index] = (
                                    "Review required"
                                )
                                validation_issues[index] = (
                                    f"{validation_issues[index]}; "
                                    "ai_validator_error: missing batch result"
                                ).strip("; ")
                                continue

                            ai_status = validation_result_for_row["status"]
                            ai_issues = validation_result_for_row.get(
                                "issues",
                                []
                            )

                            ai_issue_texts = []
                            for issue in ai_issues:
                                ai_issue_texts.append(
                                    "ai_validator["
                                    + str(issue.get("severity", "medium"))
                                    + "] "
                                    + str(issue.get("type", "other"))
                                    + ": "
                                    + str(issue.get("explanation", ""))
                                )

                            suggested = validation_result_for_row.get(
                                "suggested_translation"
                            )

                            if (
                                ai_status == "Review required"
                                and suggested
                            ):
                                ai_issue_texts.append(
                                    "ai_validator_suggestion: "
                                    + str(suggested)
                                )

                            if ai_issue_texts:
                                existing = validation_issues[index]
                                combined = "; ".join(ai_issue_texts)
                                validation_issues[index] = (
                                    f"{existing}; {combined}"
                                    if existing
                                    else combined
                                )

                            if ai_status == "Review required":
                                validation_statuses[index] = (
                                    "Review required"
                                )

                            excel_row = index + 2
                            print(
                                f"[Row {excel_row}] "
                                + (
                                    "🔍 AI review required"
                                    if ai_status == "Review required"
                                    else "✓ AI OK"
                                )
                            )

                            for issue_text in ai_issue_texts:
                                print(
                                    f"           {issue_text}"
                                )

                    # Keep the progress bar moving during validation.
                    excel_jobs[job_id]["current"] = min(
                        total_rows,
                        max(0, total_rows - 1) + validation_processed
                    )

        # Recalculate final review/OK/corrected counters after both
        # validation layers have completed so rows are never double-counted.
        final_ok_count = 0
        final_corrected_count = 0
        final_review_count = 0

        for index, status in enumerate(validation_statuses):
            if status == "OK":
                final_ok_count += 1
            elif status == "Corrected automatically":
                final_corrected_count += 1
            elif status == "Review required":
                final_review_count += 1

        excel_jobs[job_id]["ok_count"] = final_ok_count
        excel_jobs[job_id]["corrected_count"] = final_corrected_count
        excel_jobs[job_id]["review_count"] = final_review_count

        if not cancel_event.is_set():
            excel_jobs[job_id]["current"] = total_rows


        # --------------------------------------
        # ADD TRANSLATION COLUMN
        # --------------------------------------

        dataframe[
            target_column
        ] = translations


        # --------------------------------------
        # ADD VALIDATION COLUMNS
        # --------------------------------------

        dataframe[
            "translation_check"
        ] = validation_statuses


        dataframe[
            "translation_issues"
        ] = validation_issues


        # --------------------------------------
        # CREATE OUTPUT EXCEL
        # --------------------------------------

        output_file = BytesIO()


        with pd.ExcelWriter(

            output_file,

            engine="openpyxl"

        ) as writer:

            dataframe.to_excel(

                writer,

                index=False,

                sheet_name="Products"

            )


            worksheet = writer.book[
                "Products"
            ]


            format_worksheet(
                worksheet
            )


        output_file.seek(0)


        # --------------------------------------
        # STORE RESULT
        # --------------------------------------

        excel_jobs[job_id][
            "file"
        ] = output_file.getvalue()


        excel_jobs[job_id][
            "download_ready"
        ] = True


        if cancel_event.is_set():

            excel_jobs[job_id][
                "status"
            ] = "cancelled"

        else:

            excel_jobs[job_id][
                "status"
            ] = "completed"


        # --------------------------------------
        # TERMINAL COMPLETE MESSAGE
        # --------------------------------------

        print()

        print(
            "=========================================="
        )

        print(
            "Excel translation complete."
        )

        print(
            "=========================================="
        )

        print()


    except Exception as error:

        print()

        print(
            f"Excel job {job_id} failed:"
        )

        print(
            error
        )

        print()


        excel_jobs[job_id][
            "status"
        ] = "failed"


        excel_jobs[job_id][
            "error"
        ] = str(error)


# ==========================================
# STOP EXCEL TRANSLATION
# ==========================================

@app.route(
    "/stop-excel/<job_id>",
    methods=["POST"]
)
def stop_excel_translation(job_id):

    if job_id not in excel_jobs:

        return jsonify({
            "error":
                "Job not found"
        }), 404


    job = excel_jobs[job_id]


    if job["status"] != "processing":

        return jsonify({
            "message":
                "Job is no longer running."
        })


    job["cancel_event"].set()


    print(
        f"Stop requested for Excel job {job_id}"
    )


    return jsonify({
        "message":
            "Stop requested"
    })


# ==========================================
# EXCEL TRANSLATION STATUS
# ==========================================

@app.route(
    "/translation-status/<job_id>",
    methods=["GET"]
)
def translation_status(job_id):

    if job_id not in excel_jobs:

        return jsonify({
            "error":
                "Job not found"
        }), 404


    job = excel_jobs[job_id]


    return jsonify({

        "status":
            job["status"],

        "current":
            job["current"],

        "total":
            job["total"],

        "completed":
            job["completed"],

        "failed":
            job["failed"],

        "ok_count":
            job["ok_count"],

        "corrected_count":
            job["corrected_count"],

        "review_count":
            job["review_count"],

        "skipped_count":
            job["skipped_count"],

        "download_ready":
            job["download_ready"],

        "error":
            job["error"]

    })


# ==========================================
# DOWNLOAD COMPLETED EXCEL
# ==========================================

@app.route(
    "/download-excel/<job_id>",
    methods=["GET"]
)
def download_excel(job_id):

    if job_id not in excel_jobs:

        return jsonify({
            "error":
                "Job not found"
        }), 404


    job = excel_jobs[job_id]


    if not job["download_ready"]:

        return jsonify({
            "error":
                "Excel file is not ready yet."
        }), 400


    output_file = BytesIO(
        job["file"]
    )


    output_file.seek(0)


    return send_file(

        output_file,

        as_attachment=True,

        download_name=(
            "translated_products.xlsx"
        ),

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