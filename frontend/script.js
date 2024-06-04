const backendURL = "http://127.0.0.1:8000";

window.onload = function onLoad() {
    setSessionVar("sessionID", "new");
    setSessionVar("convertDisabled", true);
    setSessionVar("downloadDisabled", true);
    
    updateDependantInput();
    updateConvertFormats();
}

function setSessionVar(varName, initValue) {
    /*
    If varName is not in sessionStorage, create it and set it to initValue.
     */
    if (!sessionStorage.getItem(varName)) {
        sessionStorage.setItem(varName, initValue);
    }
}

function updateDependantInput(parentID = "", state = "") {
    /*
    Dependant input are input 'groups' that are dependant on the user having already done something.
    If parentID and state aren't "", this sets the disabled property of all children of parent tag to state.
    If they == "", then the dependant input's visibility is updated.
     */
    if (parentID !== "" && state !== "") {
        sessionStorage.setItem(`${parentID}Disabled`, state);
    }
    // Update disabled property of children of .input elements.
    const parents = document.getElementsByClassName("dependant-input");
    for (let x = 0; x < parents.length; x++) {
        parent = parents[x];
        children = parent.children;
        for (let y = 0; y < children.length; y++) {
            child = children[y];
            state = (sessionStorage.getItem(`${parent.id}Disabled`) === "true");
            child.disabled = state;
        };
    };
}

async function updateConvertFormats(fileFormat = "") {
    /*
    Updates the convertFormats session storage and updates the options for select #format-select.
    if fileFormat = "" or undefined, only select #format-select will be updated.
     */
    let formats
    if (fileFormat !== "") {
        formats = await (await fetch(
            `${backendURL}/supported-conversions/${fileFormat}`, 
            { method: "get" }
        )).json();
        sessionStorage.setItem("convertFormats", formats);
    } else {
        formats = sessionStorage.getItem("convertFormats");
        if (formats !== null) {
            formats = formats.split(",");
        }
    }

    if (formats !== null) {
        for (let x = 0; x < formats.length; x++) {
            document.getElementById("format-select").innerHTML += `<option value="${formats[x]}">${formats[x]}</option>`;
        }
    }
}

async function uploadFile() {
    let file = document.getElementById("file-input").files[0];
    let fileFormat = file.type.split("/")[1].toUpperCase();

    if (file) {
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
                sessionStorage.setItem("sessionID", json["session_id"]);
            } else if (String(response.status)[0] == "4") {
                // If 4__ error code
                console.error(`Backend response error: ${json["detail"]}`);
                alert(json["detail"]);
            } else {
                // If response not ok but no error raised
                alert("An error occured while uploading file. Please try again.");
                console.error("An error occured while uploading file. Backend response: " + JSON.stringify(json));
            }
            
            updateDependantInput("convert", false);
            await updateConvertFormats(fileFormat);
        } catch (error) {
            // If error was thrown when getting backend response.
            console.error(`Error while uploading file: ${error}`);
            alert("An error occured while uploading file. Please try again.");
        }
    } else {
        alert("Please select a file to upload.");
    }
}

async function convertFile() {
    let toFormat = document.getElementById("format-select").value;
    let optimise = true; // Change to check buttton in future.
    if (toFormat) {
        let response = await fetch(
            `${backendURL}/convert/?session_id=${sessionStorage.getItem("sessionID")}&to_format=${toFormat}&optimise=${optimise}`, 
            {method: "GET"}
        );
        if (response.ok) {
            alert("File converted successfully.")
        }
    } else {
        alert("Please select a format to convert to.");
    }
}
