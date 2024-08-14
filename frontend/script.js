const backendURL = `http://${window.location.hostname}:5000`;
const convertSelectPlaceholder = "please select a file";
const darkModeStylesHref = "dark-styles.css";
let sessionID = "new";
let validFormats = [];
let darkmode = false;

document.getElementById("theme-toggle").addEventListener("click", function() {
    setDarkMode(!darkmode)
});

document.getElementById("file-select").addEventListener("click", function() {
    // Propogates click event from the light grey box #file-select to the #file-input button.
    document.getElementById("file-input").click();
});

window.onload = async function() {
    // Set darkmode based on user preference or cookie
    darkmodeCookie = document.cookie.split(";").find(row => row.startsWith("darkmode="))?.split("=")[1] || null; // Extract cookie
    if (darkmodeCookie !== null) {
        darkmodeCookie = (darkmodeCookie === "true");
        setDarkMode(darkmodeCookie);
    } else {
        setDarkMode(window.matchMedia("(prefers-color-scheme: dark)").matches);
    }

    // Get supported formats
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

    // Set supported formats list in about section
    document.getElementById("supported-formats-list").innerHTML = "";
    validFormats.forEach(format => {
        let listItem = document.createElement("li");
        listItem.innerText = format;
        document.getElementById("supported-formats-list").appendChild(listItem);
    });
}

function setDarkMode(darkMode) {
    // Sets darkmode by toggling dark-styles.css stylesheet.
    if (darkMode) {
        darkmode = true;
        document.getElementById("dark-styles").href = darkModeStylesHref;
        document.getElementById("theme-icon-light").style.display = "block";
        document.getElementById("theme-icon-dark").style.display = "none";
    } else {
        darkmode = false;
        document.getElementById("dark-styles").href = "";
        document.getElementById("theme-icon-light").style.display = "none";
        document.getElementById("theme-icon-dark").style.display = "block";
    }
    document.cookie = `darkmode=${darkmode};}`; // Set cookie
}

async function updateToFormats() {
    // Updates the options of the format-select element.

    function setOptions(value, clear) {
        // Adds option to the #format-select select.
        if (clear) {
            document.getElementById("format-select").innerHTML = "";
        } else {
            let option = document.createElement("option");
            option.value = value;
            option.innerHTML = value;
            document.getElementById("format-select").appendChild(option);
        }
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
    // Handles errors and gives user feedback.
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
