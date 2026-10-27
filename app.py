from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import os
import json
from datetime import datetime


# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)


# Allow frontend from Live Server to connect
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    },
    supports_credentials=False
)


# ==========================================
# HOME / SERVER TEST ROUTE
# ==========================================

@app.route("/", methods=["GET"])
def home():

    return "Signature Verification Backend is Running!"


# ==========================================
# PROJECT PATHS
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SIGNATURES_FOLDER = os.path.join(
    BASE_DIR,
    "Signatures"
)

GENUINE_FOLDER = os.path.join(
    SIGNATURES_FOLDER,
    "genuine"
)

UPLOADED_FOLDER = os.path.join(
    SIGNATURES_FOLDER,
    "uploaded"
)

HISTORY_FILE = os.path.join(
    BASE_DIR,
    "verification_history.json"
)


# ==========================================
# CREATE REQUIRED FOLDERS
# ==========================================

os.makedirs(
    GENUINE_FOLDER,
    exist_ok=True
)

os.makedirs(
    UPLOADED_FOLDER,
    exist_ok=True
)


# ==========================================
# FIND ALL GENUINE SIGNATURES
# ==========================================

def find_genuine_images():

    valid_extensions = [
        ".png",
        ".jpg",
        ".jpeg"
    ]

    genuine_images = []

    for filename in os.listdir(GENUINE_FOLDER):

        file_path = os.path.join(
            GENUINE_FOLDER,
            filename
        )

        if os.path.isfile(file_path):

            extension = os.path.splitext(
                filename
            )[1].lower()

            if extension in valid_extensions:

                genuine_images.append(file_path)

    return genuine_images


# ==========================================
# PREPROCESS SIGNATURE
# ==========================================

def preprocess_signature(image):

    _, thresh = cv2.threshold(
        image,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    coords = cv2.findNonZero(thresh)

    if coords is not None:

        x, y, w, h = cv2.boundingRect(
            coords
        )

        cropped = thresh[
            y:y + h,
            x:x + w
        ]

    else:

        cropped = thresh

    resized = cv2.resize(
        cropped,
        (300, 150)
    )

    return resized


# ==========================================
# CALCULATE SIMILARITY
# ==========================================

def calculate_similarity(
    uploaded_processed,
    genuine_processed
):

    difference = cv2.absdiff(
        uploaded_processed,
        genuine_processed
    )

    mean_difference = np.mean(
        difference
    )

    similarity = 100 - (
        mean_difference / 255 * 100
    )

    similarity = max(
        0,
        min(100, similarity)
    )

    return round(
        similarity,
        2
    )


# ==========================================
# SAVE VERIFICATION HISTORY
# ==========================================

def save_history(
    result,
    similarity
):

    now = datetime.now()

    record = {

        "date":
            now.strftime("%Y-%m-%d"),

        "time":
            now.strftime("%H:%M:%S"),

        "result":
            result,

        "similarity":
            similarity
    }

    history = []

    if os.path.exists(HISTORY_FILE):

        try:

            with open(
                HISTORY_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                history = json.load(file)

                if not isinstance(history, list):
                    history = []

        except Exception:

            history = []

    history.append(record)

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            indent=4
        )


# ==========================================
# REGISTER GENUINE SIGNATURES
# ==========================================

@app.route(
    "/register",
    methods=["POST", "OPTIONS"]
)
def register_user():

    if request.method == "OPTIONS":
        return jsonify({
            "message": "CORS OK"
        }), 200

    print("\n================================")
    print("REGISTER REQUEST RECEIVED")
    print("================================")

    # ==========================================
    # CHECK FILES
    # ==========================================

    if "signatures" not in request.files:

        return jsonify({
            "error": "No signature samples uploaded"
        }), 400

    files = request.files.getlist("signatures")

    print(
        "Number of files received:",
        len(files)
    )

    # ==========================================
    # CHECK NUMBER OF FILES
    # ==========================================

    if len(files) < 3 or len(files) > 5:

        return jsonify({
            "error":
                "Please upload 3 to 5 signature samples"
        }), 400

    # ==========================================
    # VALID EXTENSIONS
    # ==========================================

    valid_extensions = [
        ".png",
        ".jpg",
        ".jpeg"
    ]

    valid_files = []

    for file in files:

        if not file or file.filename == "":
            continue

        extension = os.path.splitext(
            file.filename
        )[1].lower()

        print(
            "Received:",
            file.filename
        )

        if extension in valid_extensions:

            valid_files.append(
                (file, extension)
            )

    if len(valid_files) < 3:

        return jsonify({
            "error":
                "At least 3 valid PNG, JPG or JPEG signature images are required"
        }), 400

    # ==========================================
    # USER DETAILS
    # ==========================================

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    print("Name:", name)
    print("Email:", email)

    # ==========================================
    # DELETE OLD SIGNATURES
    # ==========================================

    print("Cleaning old signature samples...")

    for filename in os.listdir(GENUINE_FOLDER):

        file_path = os.path.join(
            GENUINE_FOLDER,
            filename
        )

        if os.path.isfile(file_path):

            extension = os.path.splitext(
                filename
            )[1].lower()

            if extension in valid_extensions:

                try:

                    # Make file writable
                    os.chmod(
                        file_path,
                        0o666
                    )

                    os.remove(
                        file_path
                    )

                    print(
                        "Deleted old file:",
                        filename
                    )

                except Exception as error:

                    print(
                        "Could not delete:",
                        filename
                    )

                    print(
                        "Reason:",
                        error
                    )

                    # Don't stop registration
                    # if an old file cannot be deleted
                    continue

    # ==========================================
    # SAVE NEW SIGNATURES
    # ==========================================

    saved_count = 0

    for index, item in enumerate(
        valid_files
    ):

        file = item[0]
        extension = item[1]

        filename = (
            "genuine_"
            + str(index + 1)
            + extension
        )

        file_path = os.path.join(
            GENUINE_FOLDER,
            filename
        )

        try:

            file.save(
                file_path
            )

            print(
                "Saved:",
                filename
            )

            saved_count += 1

        except Exception as error:

            print(
                "Could not save:",
                filename
            )

            print(
                "Reason:",
                error
            )

    # ==========================================
    # FINAL CHECK
    # ==========================================

    if saved_count < 3:

        return jsonify({
            "error":
                "Could not save at least 3 signature samples. Check the Signatures/genuine folder permissions."
        }), 500

    print("--------------------------------")
    print(
        "New Genuine Signatures Registered"
    )
    print(
        "Samples Saved:",
        saved_count
    )
    print("--------------------------------")

    return jsonify({

        "success": True,

        "message":
            "Signature samples registered successfully",

        "samples":
            saved_count

    }), 200


# ==========================================
# VERIFY SIGNATURE
# ==========================================

@app.route(
    "/verify",
    methods=["POST", "OPTIONS"]
)
def verify_signature():

    if request.method == "OPTIONS":

        return jsonify({
            "message": "CORS OK"
        }), 200


    if "signature" not in request.files:

        return jsonify({
            "error":
                "No signature uploaded"
        }), 400


    file = request.files["signature"]


    uploaded_path = os.path.join(
        UPLOADED_FOLDER,
        "signature.png"
    )


    try:

        file.save(
            uploaded_path
        )

    except Exception as error:

        print(
            "Upload error:",
            error
        )

        return jsonify({
            "error":
                "Could not save uploaded signature"
        }), 500


    # ------------------------------------------
    # GET GENUINE SIGNATURES
    # ------------------------------------------

    genuine_paths = find_genuine_images()


    if len(genuine_paths) == 0:

        return jsonify({
            "error":
                "Genuine signatures not found"
        }), 404


    # ------------------------------------------
    # READ UPLOADED SIGNATURE
    # ------------------------------------------

    uploaded_image = cv2.imread(
        uploaded_path,
        cv2.IMREAD_GRAYSCALE
    )


    if uploaded_image is None:

        return jsonify({
            "error":
                "Uploaded image could not be read"
        }), 400


    uploaded_processed = preprocess_signature(
        uploaded_image
    )


    similarity_scores = []


    # ------------------------------------------
    # COMPARE WITH ALL GENUINE SIGNATURES
    # ------------------------------------------

    for genuine_path in genuine_paths:

        genuine_image = cv2.imread(
            genuine_path,
            cv2.IMREAD_GRAYSCALE
        )


        if genuine_image is None:

            continue


        genuine_processed = preprocess_signature(
            genuine_image
        )


        similarity = calculate_similarity(
            uploaded_processed,
            genuine_processed
        )


        similarity_scores.append(
            similarity
        )


        print(
            "Compared with:",
            os.path.basename(genuine_path),
            "->",
            similarity,
            "%"
        )


    if len(similarity_scores) == 0:

        return jsonify({
            "error":
                "No valid genuine signatures found"
        }), 400


    # ------------------------------------------
    # BEST SIMILARITY
    # ------------------------------------------

    best_similarity = max(
        similarity_scores
    )


    # ------------------------------------------
    # CLASSIFICATION
    # ------------------------------------------

    if best_similarity >= 90:

        result = "Genuine"

    else:

        result = "Forged"


    # ------------------------------------------
    # TERMINAL OUTPUT
    # ------------------------------------------

    print("--------------------------------")
    print(
        "Signature Verification Result"
    )

    print(
        "Genuine Samples Compared:",
        len(similarity_scores)
    )

    print(
        "Similarity Scores:",
        similarity_scores
    )

    print(
        "Best Similarity:",
        best_similarity,
        "%"
    )

    print(
        "Result:",
        result
    )

    print("--------------------------------")


    # ------------------------------------------
    # SAVE HISTORY
    # ------------------------------------------

    save_history(
        result,
        best_similarity
    )


    return jsonify({

        "result":
            result,

        "similarity":
            best_similarity,

        "samplesCompared":
            len(similarity_scores),

        "allScores":
            similarity_scores

    }), 200


# ==========================================
# GET VERIFICATION HISTORY
# ==========================================

@app.route(
    "/history",
    methods=["GET", "OPTIONS"]
)
def get_history():

    if request.method == "OPTIONS":

        return jsonify({
            "message": "CORS OK"
        }), 200


    if not os.path.exists(
        HISTORY_FILE
    ):

        return jsonify([])


    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            history = json.load(file)


        if not isinstance(
            history,
            list
        ):

            history = []


        return jsonify(
            history
        )


    except Exception as error:

        print(
            "History error:",
            error
        )

        return jsonify([])


# ==========================================
# START FLASK SERVER
# ==========================================

if __name__ == "__main__":

    print("--------------------------------")
    print(
        "Signature Verification Server"
    )
    print(
        "Server running at:"
    )
    print(
        "http://127.0.0.1:5000"
    )
    print("--------------------------------")


    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )