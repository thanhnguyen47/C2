const defaultAvatar = '/static/default-avatar.jpg'; 
const avatarImg = document.getElementById('avatar-img');
const uploadBtn = document.getElementById('upload-btn');
const trashIcon = document.getElementById('trash-icon');
const avatarUpload = document.getElementById('avatar-upload');
const profileForm = document.getElementById('profile-form');
const alertContainer = document.getElementById('alertContainer');

// Maximum file size (2MB)
const MAX_FILE_SIZE = 2 * 1024 * 1024;

let deleteAvatar = false;

// 
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

// handle upload avatar
uploadBtn.addEventListener('click', (event) => {
    event.preventDefault();
    avatarUpload.click();
});

avatarUpload.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file) {
        // Check file type
        if (!file.type.match(/^image\/(jpeg|png)$/)) {
            showAlert('Please upload an image file (.png, .jpg, .jpeg).', 'danger');
            avatarUpload.value = '';
            return;
        }
        // Check file size
        if (file.size > MAX_FILE_SIZE) {
            showAlert('Image file must be less than 2MB.', 'danger');
            avatarUpload.value = '';
            return;
        }
        const img = new Image();
        const objectUrl = URL.createObjectURL(file);
        img.onload = () => {
            if (img.width >= 300 && img.height >= 300) {
                avatarImg.src = objectUrl;
                deleteAvatar = false; // Reset delete flag
            } else {
                showAlert('Avatar must be at least 300x300 pixels.', 'danger');
                avatarUpload.value = '';
                URL.revokeObjectURL(objectUrl);
            }
        };
        img.onerror = () => {
            showAlert('Invalid image file.', 'danger');
            avatarUpload.value = '';
            URL.revokeObjectURL(objectUrl);
        };
        img.src = objectUrl;
    }
});

// handle delete avatar
trashIcon.addEventListener('click', (event) => {
    event.preventDefault();
    avatarImg.src = defaultAvatar;
    avatarUpload.value = ''; // delete chosen file
    deleteAvatar = true; // mark as deleted
    showAlert('Avatar deleted.', 'success');
});

// submit form
profileForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData();
    formData.append('fullname', document.getElementById('full-name').value);
    formData.append('date_of_birth', document.getElementById('date-of-birth').value);
    formData.append('country', document.getElementById('country').value);
    formData.append('timezone', document.getElementById('timezone').value);
    formData.append('phone_number', document.getElementById('phone-number').value);
    formData.append('website', document.getElementById('website').value);

    const avatarFile = avatarUpload.files[0];
    if (avatarFile) {
        formData.append('avatar', avatarFile);
    } else if (deleteAvatar === true) {
        formData.append('delete_avatar', 'true'); 
        deleteAvatar = false;
    }

    try {
        const response = await fetch('/profile/update', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const result = await response.json();
        if (response.ok) {
            showAlert('Profile updated successfully!', 'success');
            avatarImg.src = result.avatar_url || defaultAvatar;
            deleteAvatar = false;
            avatarUpload.value = ''; // Clear file input
        } else {
            let errorMessage = 'Failed to update profile.';
            if (result.detail) {
                if (result.detail.includes('Image too large')) {
                    errorMessage = 'Image file must be less than 2MB.';
                } else if (result.detail.includes('300x300')) {
                    errorMessage = 'Avatar must be at least 300x300 pixels.';
                } else if (result.detail.includes('File type not allowed')) {
                    errorMessage = 'Please upload a valid image file (.png, .jpg, .jpeg).';
                } else if (result.detail.includes('Invalid image file')) {
                    errorMessage = 'Invalid image file.';
                } else {
                    errorMessage = result.detail;
                }
            }
            showAlert(`Error: ${errorMessage}`, 'danger');
        }
    } catch (error) {
        showAlert('Error: Could not connect to server.', 'danger');
        console.error('Submit error:', error);
    }
});