
// Hàm hiển thị thông báo
function showAlert(message, type = "success") {
    console.log(`showAlert called: ${message}, type: ${type}`);
    if (!alertContainer) {
        console.error("alertContainer not found in DOM. Ensure <div id='alertContainer'> exists in HTML.");
        return;
    }
    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = "alert";
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alertContainer.appendChild(alert);
    console.log("Alert added to DOM:", alert.outerHTML);
    setTimeout(() => {
        alert.remove();
        console.log("Alert removed from DOM");
    }, 5000);
}

// Hàm gọi API Access the Lab
async function accessLab(topicSlug, labSlug) {
    try {
        const response = await fetch(`/web/${topicSlug}/${labSlug}/access`, {
            method: 'POST',
            credentials: 'include'
        });
        const data = await response.json();
        if (response.ok) {
            showAlert(`Lab is running at: <a href="https://${data.subdomain}" target="_blank">${data.subdomain}</a>`, 'success');
            window.open(`https://${data.subdomain}`, '_blank');
        } else {
            showAlert(data.detail || 'Failed to access lab', 'danger');
        }
    } catch (error) {
        showAlert(`Error accessing lab: ${error.message}`, 'danger');
    }
}

// Hàm gọi API Submit Flag
async function submitFlag(topicSlug, labSlug) {
    const flagInput = document.querySelector('.flag-input');
    const flag = flagInput.value.trim();
    if (!flag) {
        showAlert('Please enter a flag', 'warning');
        return;
    }
    try {
        const response = await fetch(`/web/${topicSlug}/${labSlug}/submit`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ flag })
        });
        const data = await response.json();
        if (response.ok) {
            showAlert('Flag correct! Challenge solved!', 'success');
            flagInput.value = ''; // Xóa input
            // Cập nhật trạng thái solved (tùy chọn)
            document.querySelector('.lab-status').className = 'lab-status solved';
            document.querySelector('.lab-status').innerHTML = '<i class="bi bi-check-circle-fill"></i> Solved';
        } else {
            showAlert(data.detail || 'Invalid flag', 'danger');
        }
    } catch (error) {
        showAlert(`Error submitting flag: ${error.message}`, 'danger');
    }
}