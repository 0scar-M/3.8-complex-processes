const backendURL = "http://127.0.0.1:8000";
const convertSelectPlaceholder = "please select a file";
let sessionID = "new";

async function updateToFormats() {
    /* Updates the options of the format-select element. */

    function setOptions(value, clear) {
        /* Adds option to the #format-select select. */
        if (clear) {
            document.getElementById("format-select").innerHTML = "";
        } else {
            let option = document.createElement("option");
            option.value = value;
            option.innerHTML = value;
            document.getElementById("format-select").appendChild(option);
        }
    }
    // Get supported formats from backend.
    try {
        let response = await fetch(
            `${backendURL}/supported-formats/`, 
            {method: "get"}
        );
        json = await response.json();
        if (response.ok && json.constructor.name == "Array") {
            validFormats = json;
        }
    } catch (error) {
        handleError(error, "getting supported formats");
    }

    let fileFormat = "";
    try {
        fileFormat = document.getElementById("file-input").files[0].name.split(".")[1].toUpperCase();
    } catch {}
    
    // Correct format for possible aliases
    try {
        let response = await fetch(
            `${backendURL}/correct-format/?format=${fileFormat}`, 
            {method: "get"}
        );
        json = await response.json();
        if (response.ok) {
            fileFormat = json;
        }
    } catch (error) {
        handleError(error, "checking format aliases");
    }

    if (fileFormat !== "" && validFormats.includes(fileFormat)) {
        try {
            let response = await fetch(
                `${backendURL}/supported-conversions/?format=${fileFormat}`, 
                {method: "get"}
            );
            if (response.ok) {
                let formats = await response.json();
                if (Array.isArray(formats)) {
                    document.getElementById("format-select").innerHTML = "";
                    formats.forEach(format => {
                        setOptions(format, false);
                    });
                    if (formats.includes(fileFormat)) { // Set format select option to uploaded file format
                        document.getElementById("format-select").value = fileFormat;
                    }
                } else {
                    handleError(json["detail"], "getting conversion formats");
                    setOptions(convertSelectPlaceholder, true);
                }
            } else {
                handleError(json["detail"], "getting conversion formats");
                setOptions(convertSelectPlaceholder, true);
            }
        } catch (error) {
            handleError(error, "getting conversion formats")
            setOptions(convertSelectPlaceholder, true);
        }
        setUserFeedback("", "black");
    } else if (!validFormats.includes(fileFormat)) {
        setUserFeedback("Please select a file with a valid format.", "orange");
        setOptions(convertSelectPlaceholder, true);
    } else {
        setOptions(convertSelectPlaceholder, true);
    }
}

async function convertFile() {
    /* 
    Converts the file.
    Called by the submission of the #convert form.
    */

    let file = document.getElementById("file-input").files[0];
    let fileFormat = "";

    if (file) {
        fileFormat = file.name.split(".")[1].toUpperCase();
    } else {
        setUserFeedback("Please select a file to convert.", "orange");
        return;
    }
    let toFormat = document.getElementById("format-select").value;
    let validFormats = [];

    // Get supported formats from backend.
    try {
        let response = await fetch(
            `${backendURL}/supported-formats/`, 
            {method: "get"}
        );
        json = await response.json();
        if (response.ok && json.constructor.name == "Array") {
            validFormats = json;
        }
    } catch (error) {
        handleError(error, "getting supported formats");
    }
    
    if (validFormats.includes(fileFormat) && toFormat !== convertSelectPlaceholder) {
        document.getElementById("convert-loader").style.display = "block"; // Show loader

        // Upload file
        try {
            let formData = new FormData();
            formData.append("file", file);

            let response = await fetch(
                `${backendURL}/upload/?session_id=${sessionID}`, 
                {method: "POST", 
                body: formData}
            );
            let json = await response.json();

            if (response.ok) {
                sessionID = json["session_id"];
                setUserFeedback("File uploaded successfully.", "black");
            } else {
                handleError(json["detail"], "uploading file");
                return;
            }
        } catch (error) {
            handleError(error, "uploading file");
            return;
        }

        // Check conversion with backend.
        let validConversion = null;
        try {
            let response = await fetch(
                `${backendURL}/is-valid-conversion/?from_format=${fileFormat}&to_format=${toFormat}`, 
                {method: "get"}
            );
            json = await response.json();
            if (response.ok) {
                validConversion = json;
            }
        } catch (error) {
            handleError(error, "checking conversion");
        }

        if (validConversion) {
            // Convert file
            try {
                let response = await fetch(
                    `${backendURL}/convert/?session_id=${sessionID}&to_format=${toFormat}`, 
                    {method: "PATCH"}
                );
                let json = await response.json();

                if (response.ok) {
                    setUserFeedback(`File converted successfully from: '${file.name}' to: '${json["new_file_name"]}'`, "green");
                } else {
                    handleError(json["detail"], "converting file");
                    return;
                }
            } catch (error) {
                handleError(error, "converting file");
                return;
            }

            // Download file
            try {
                let response = await fetch(
                    `${backendURL}/download/?session_id=${sessionID}`, 
                    {method: "GET"}
                );

                if (response.ok) {
                    let fileName = response.headers.get("file_name");
                    let blob = await response.blob();
                    let link = window.URL.createObjectURL(blob);
                    let a = document.createElement('a');
                    a.href = link;
                    a.download = fileName;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setUserFeedback(`File download started: '${fileName}'`, "green");
                } else {
                    let json = await response.json();
                    handleError(json["detail"], "downloading file");
                    return;
                }
            } catch (error) {
                handleError(error, "downloading file");
                return;
            }
            sessionID = "new";
        } else {
            setUserFeedback(`Invalid conversion: ${fileFormat} to ${toFormat}. Please try again with a different format.`, "orange");
        }
        
    } else if (!validFormats.includes(fileFormat)) {
        setUserFeedback("Please select a file with a valid format.", "orange");
    } else if (toFormat == convertSelectPlaceholder) {
        setUserFeedback("Please select a format to convert to.", "orange");
    }
    document.getElementById("convert-loader").style.display = "none"; // Hide loader
    return;
}

function handleError(error, context) {
    /* Handles errors and gives user feedback. */
    setUserFeedback(`An error occured while ${context}. Please try again.`, "red");
    console.error(`An error occured while ${context}. Error: ${error}`);
    document.getElementById("convert-loader").style.display = "none"; // Hide loader
}

function setUserFeedback(text, color) {
    /* 
    Sets the innerText and style.color properties of the element #user-feedback
    If color is red or orange, then #user-feedback will be bold.
     */
    document.getElementById("user-feedback").innerText = text;
    document.getElementById("user-feedback").style.color = color;
    if (color == "red" || color == "orange") {
        document.getElementById("user-feedback").style.fontWeight = "bold";
    } else {
        document.getElementById("user-feedback").style.fontWeight = "normal";
    }
}
