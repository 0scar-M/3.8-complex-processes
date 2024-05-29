const backendURL = "http://127.0.0.1:8000";
if (!sessionStorage.getItem("sessionID")) {
    // If sessionID is not in storage, create it and set it to new.
    sessionStorage.setItem("sessionID", "new")
}

async function uploadFile() {
    let file = document.getElementById("file-input").files[0];
    
    if (file) {
        let formData = new FormData();
        formData.append("file", file)
        
        try {
            let response = await fetch(`${backendURL}/upload/?session_id=${sessionStorage.getItem("sessionID")}`, {
                method: "POST", 
                body: formData
            });
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
        } catch (error) {
            // If error was thrown when getting backend response.
            console.error(`Error while uploading file: ${error}`);
            alert("An error occured while uploading file. Please try again.");
        }
    }
    else {
        alert("Please select a file to upload.");
    }
}
