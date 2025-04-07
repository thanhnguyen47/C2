window.onload = function() {
    const cmd = document.getElementsByClassName("cmd-section")[0]
    cmd.scrollTop = cmd.scrollHeight
}

document.getElementById("command-form").addEventListener("submit", (event) => {
    event.preventDefault()

    const token = event.currentTarget.getAttribute("bot-token")
    const command = document.getElementById("command").value.trim()
    // update response (later)

    const formData = new FormData()
    formData.append("command", command)

    fetch (`/session/${token}/command`, {
        method: "POST",
        body: formData,
        // credentials: "include"
    })
    .then(r=>r.json())
    .then(j=>{
        console.log(j)
    })
    .catch(e=>console.error(e))
})