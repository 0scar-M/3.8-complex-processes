const backendURL = "http://127.0.0.1:8000";

window.onload = function onLoad() {
    setSessionVar("sessionID", "new");
    setSessionVar("uploadedFormat", "");
    setSessionVar("convertDisabled", true);
    
    updateUserProgress();
}

function setSessionVar(varName, initValue) {
    /*
    If varName is not in sessionStorage, create it and set it to initValue.
     */
    if (!sessionStorage.getItem(varName)) {
        sessionStorage.setItem(varName, initValue);
    }
}

async function updateUserProgress() {
    /*
    Updates the user's progress on the page as the page is realoded everytime a button is pressed.
     */

    // Update conversion formats dropdown and session storage.
    let fileFormat = sessionStorage.getItem("uploadedFormat");
    if (fileFormat !== "") {
        let response = await (await fetch(
            `${backendURL}/supported-conversions/${fileFormat}`, 
            {method: "get"}
        )).json();
        sessionStorage.setItem("convertFormats", response);
    }
    let formats = sessionStorage.getItem("convertFormats");
    if (formats !== "" && formats !== null) {
        formats = formats.split(",");
        for (let x = 0; x < formats.length; x++) {
            let option = document.createElement("option");
            option.value, option.innerHTML = `<option value="${formats[x]}">${formats[x]}</option>`;
            document.getElementById("format-select").appendChild(option);
        }
    } else {
        document.getElementById("format-select").innerHTML = "";
    }

    // Update disabled property of children of .input elements.
    const parents = document.getElementsByClassName("dependant-input");
    for (let x = 0; x < parents.length; x++) {
        let parent = parents[x];
        let children = parent.children;
        for (let y = 0; y < children.length; y++) {
            let child = children[y];
            let state = (sessionStorage.getItem(`${parent.id}Disabled`) === "true");
            child.disabled = state;
        };
    };
}

async function uploadFile() {
    let file = document.getElementById("file-input").files[0];

    if (file) {
        let fileFormat = file.type.split("/")[1].toUpperCase();
        let formData = new FormData();
        formData.append("file", file)
        
        try {
            let response = await fetch(
                `${backendURL}/upload/?session_id=${sessionStorage.getItem("sessionID")}`, 
                {method: "POST", 
                body: formData}
            );
            let json = await response.json();

            if (response.ok) {
                sessionStorage.setItem("uploadedFormat", fileFormat);
                sessionStorage.setItem("sessionID", json["session_id"]);
                alert("File uploaded successfully.");
            } else if (String(response.status)[0] == "4") {
                // If 4__ error code
                console.error(`Backend response error: ${json["detail"]}`);
                alert(json["detail"]);
            } else {
                // If response not ok but no error raised
                alert(`An error occured while uploading file: ${json["detail"]}`);
                console.error(`Backend response error while uploading file: ${json["detail"]}`);
            }
            sessionStorage.setItem("convertDisabled", false);
        } catch (error) {
            alert("An error occured while uploading file. Please try again.");
            console.error(`Backend response error while uploading file: ${error}`);
        }
    } else {
        alert("Please select a file to upload.");
    }
}

async function convertFile() {
    let toFormat = document.getElementById("format-select").value;
    let optimise = true; // Change to check buttton in future.

    if (toFormat) {
        try {
            let response = await fetch(
                `${backendURL}/download/?session_id=${sessionStorage.getItem("sessionID")}&to_format=${toFormat}&optimise=${optimise}`, 
                {method: "GET"}
            );

            if (response.ok) {
                // Get the file name from the headers
                let fileName = response.headers.get("file-name");
                let blob = await response.blob();
                let link = window.URL.createObjectURL(blob);

                document.getElementById("download").href = link;
                document.getElementById("download").download = fileName;
                alert("File converted successfully.");
            }  else if (String(response.status)[0] == "4") {
                // If 4__ error code
                let json = await response.json();
                console.error(`Backend response error: ${json["detail"]}`);
                alert(json["detail"]);
            } else {
                // If response not ok but no error raised
                let json = await response.json();
                alert(`An error occured while converting file: ${json["detail"]}`);
                console.error(`Backend response error while converting file: ${json["detail"]}`);
            }
        } catch (error) {
            // If error was thrown while getting backend response.
            alert("An error occurred while converting file. Please try again.");
            console.error(`Error during file conversion: ${error}`);
        }
        sessionStorage.setItem("sessionID", "new");
        sessionStorage.setItem("uploadedFormat", "");
        sessionStorage.setItem("convertDisabled", true);
        await updateUserProgress();
        // download file
        document.getElementById("download").click();
    } else {
        alert("Please select a format to convert to.");
    }
}
