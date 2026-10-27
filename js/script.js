/* ================= PASSWORD SHOW / HIDE ================= */

function togglePassword() {
    const password = document.getElementById("password");
    const button = document.querySelector(".show-password");

    if (!password || !button) return;

    if (password.type === "password") {
        password.type = "text";
        button.textContent = "Hide";
    } else {
        password.type = "password";
        button.textContent = "Show";
    }
}


/* ================= REGISTER PASSWORD ================= */

function toggleRegisterPassword(fieldId, button) {
    const passwordField = document.getElementById(fieldId);

    if (!passwordField || !button) return;

    if (passwordField.type === "password") {
        passwordField.type = "text";
        button.textContent = "Hide";
    } else {
        passwordField.type = "password";
        button.textContent = "Show";
    }
}


/* ================= SIGNATURE PAD ================= */

let signaturePad = null;


/* ================= PAGE LOAD ================= */

document.addEventListener("DOMContentLoaded", function () {
    console.log("script.js loaded successfully");

    const signatureCanvas = document.getElementById("signature-pad");

    // Signature-related code runs only on verify.html
    if (!signatureCanvas) return;

    if (typeof SignaturePad === "undefined") {
        console.error("SignaturePad library is not loaded.");
        return;
    }

    /* ================= RESIZE CANVAS ================= */

    function resizeCanvas() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        const oldData = signaturePad ? signaturePad.toData() : null;

        const width = signatureCanvas.offsetWidth;
        const height = signatureCanvas.offsetHeight;

        signatureCanvas.width = width * ratio;
        signatureCanvas.height = height * ratio;

        const context = signatureCanvas.getContext("2d");
        context.setTransform(ratio, 0, 0, ratio, 0, 0);

        if (signaturePad && oldData) {
            signaturePad.clear();
            signaturePad.fromData(oldData);
        }
    }

    resizeCanvas();

    /* ================= CREATE SIGNATURE PAD ================= */

    signaturePad = new SignaturePad(signatureCanvas, {
        minWidth: 1,
        maxWidth: 2.5,
        penColor: "#172033",
        backgroundColor: "rgb(255,255,255)"
    });

    console.log("SignaturePad created successfully");

    /* ================= RESIZE EVENT ================= */

    window.addEventListener("resize", resizeCanvas);

    /* ================= CLEAR BUTTON ================= */

    const clearButton = document.getElementById("clear-signature");

    if (clearButton) {
        clearButton.addEventListener("click", function () {
            signaturePad.clear();
            console.log("Signature cleared");
        });
    }

    /* ================= FILE UPLOAD PREVIEW ================= */

    const verifyFile = document.getElementById("verify-file");
    const imagePreview = document.getElementById("image-preview");
    const previewContainer = document.getElementById("image-preview-container");
    const selectedFileName = document.getElementById("selected-file-name");

    if (verifyFile) {
        verifyFile.addEventListener("change", function () {
            const file = this.files && this.files[0];

            if (!file) return;

            if (selectedFileName) {
                selectedFileName.textContent = file.name;
            }

            const reader = new FileReader();

            reader.onload = function (event) {
                if (imagePreview) {
                    imagePreview.src = event.target.result;
                }

                if (previewContainer) {
                    previewContainer.style.display = "block";
                }
            };

            reader.readAsDataURL(file);
        });
    }

    /*
      Do not add another Verify click listener here.
      The HTML button uses onclick="verifySignature()".
    */
});


/* ================= VERIFY SIGNATURE FUNCTION ================= */

window.verifySignature = async function () {
    console.log("VERIFY FUNCTION STARTED");

    const verifyButton = document.getElementById("verify-button");
    const verifyMessage = document.getElementById("verify-message");
    const verifyFile = document.getElementById("verify-file");
    const canvas = document.getElementById("signature-pad");

    if (!verifyButton) {
        console.error("Verify button not found");
        return;
    }

    // Prevent accidental repeated submissions
    if (verifyButton.disabled) return;

    verifyButton.disabled = true;
    verifyButton.textContent = "Verifying...";

    if (verifyMessage) {
        verifyMessage.textContent = "";
    }

    const uploadedFile = Boolean(
        verifyFile &&
        verifyFile.files &&
        verifyFile.files.length > 0
    );

    const drawnSignature = Boolean(
        signaturePad && !signaturePad.isEmpty()
    );

    console.log("Uploaded:", uploadedFile);
    console.log("Drawn:", drawnSignature);

    if (!uploadedFile && !drawnSignature) {
        if (verifyMessage) {
            verifyMessage.textContent =
                "Please upload or draw a signature first.";
        }

        verifyButton.disabled = false;
        verifyButton.textContent = "Verify Signature →";
        return;
    }

    try {
        let signatureFile;

        /* ================= GET SIGNATURE IMAGE ================= */

        if (uploadedFile) {
            signatureFile = verifyFile.files[0];
            console.log("Using uploaded signature:", signatureFile.name);
        } else {
            console.log("Using drawn signature");

            const blob = await new Promise(function (resolve, reject) {
                canvas.toBlob(function (createdBlob) {
                    if (!createdBlob) {
                        reject(new Error("Could not create image from drawing."));
                        return;
                    }

                    resolve(createdBlob);
                }, "image/png");
            });

            signatureFile = new File(
                [blob],
                "drawn_signature.png",
                { type: "image/png" }
            );

            console.log("Drawn signature converted to file");
        }

        /* ================= SEND TO FLASK ================= */

        const formData = new FormData();
        formData.append("signature", signatureFile);

        console.log("Sending signature to Flask...");

        const response = await fetch(
            "http://127.0.0.1:5000/verify",
            {
                method: "POST",
                body: formData
            }
        );

        console.log("Flask status:", response.status);

        const responseText = await response.text();
        console.log("Raw Flask response:", responseText);

        let data;

        try {
            data = JSON.parse(responseText);
        } catch (error) {
            throw new Error("Invalid response received from Flask.");
        }

        console.log("Parsed backend response:", data);

        if (!response.ok) {
            throw new Error(
                data.error || "Signature verification failed."
            );
        }

        /* ================= PREPARE RESULT ================= */

        const verificationResult = {
            result: data.result || "Unknown",
            similarity: Number(data.similarity || 0),
            samplesCompared: Number(data.samplesCompared || 0),
            allScores: Array.isArray(data.allScores)
                ? data.allScores
                : []
        };

        console.log("Verification result:", verificationResult);

        /* ================= SAVE RESULT ================= */

        localStorage.setItem(
            "verificationResult",
            JSON.stringify(verificationResult)
        );

        // Confirm that the latest result was saved
        const savedResult = localStorage.getItem("verificationResult");

        if (!savedResult) {
            throw new Error("Could not save verification result.");
        }

        console.log("Result saved successfully");

        if (verifyMessage) {
            verifyMessage.textContent = "Verification complete. Opening result...";
        }

        verifyButton.textContent = "Verified ✓";

        /* ================= OPEN RESULT PAGE ================= */

        // Relative path: same origin => localStorage hamesha milega
        window.location.href = "result.html?time=" + Date.now();

    } catch (error) {
        console.error("VERIFY ERROR:", error);

        if (verifyMessage) {
            const isNetworkError =
                error instanceof TypeError &&
                /fetch/i.test(error.message);

            verifyMessage.textContent = isNetworkError
                ? "Cannot reach the server. Make sure app.py is running at http://127.0.0.1:5000 and try again."
                : (error.message || "Unable to connect to Python backend.");
        }

        verifyButton.disabled = false;
        verifyButton.textContent = "Verify Signature →";
    }
};


/* ================= SCRIPT READY ================= */

console.log("verifySignature function is ready");