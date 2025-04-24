const defaultAvatar = '/static/default-avatar.jpg'; 
const avatarImg = document.getElementById('avatar-img');
const uploadBtn = document.getElementById('upload-btn');
const trashIcon = document.getElementById('trash-icon');
const avatarUpload = document.getElementById('avatar-upload');
const profileForm = document.getElementById('profile-form');

// handle upload avatar
uploadBtn.addEventListener('click', (event) => {
    event.preventDefault()
    avatarUpload.click();
});

avatarUpload.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file) {
        if (!file.type.startsWith('image/')) {
            alert('Please upload an image file (.png, .jpg, .jpeg).');
            return;
        }
        const img = new Image();
        img.onload = () => {
            if (img.width >= 300 && img.height >= 300) {
                avatarImg.src = URL.createObjectURL(file);
            } else {
                alert('Avatar must be at least 300x300 pixels.');
                avatarUpload.value = '';
            }
        };
        img.onerror = () => {
            alert('Invalid image file.');
            avatarUpload.value = '';
        };
        img.src = URL.createObjectURL(file);
    }
});

// handle delete avatar
trashIcon.addEventListener('click', (event) => {
    event.preventDefault()
    avatarImg.src = defaultAvatar;
    avatarUpload.value = ''; // delete choosen file
    avatarUpload.dataset.deleteAvatar = 'true'; // mark as deleted
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
    } else if (avatarUpload.dataset.deleteAvatar === 'true') {
        formData.append('delete_avatar', 'true'); 
    }

    try {
        const response = await fetch('/profile/update', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const result = await response.json();
        if (response.ok) {
            alert('Profile updated successfully!');
            // update avater after receive the resp
            avatarImg.src = result.avatar_url || defaultAvatar;
            avatarUpload.dataset.deleteAvatar = 'false';
            alert(`Error: ${result.detail || 'Failed to update profile.'}`);
        }
    } catch (error) {
        alert('Error: Could not connect to server.');
        console.error('Submit error:', error);
    }
});