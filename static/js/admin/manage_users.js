
document.addEventListener("DOMContentLoaded", () => {
    // Khởi tạo DataTables với kiểm tra lỗi
    const initDataTable = () => {
        if (typeof DataTable === "undefined") {
            console.error("DataTable is not defined. Check script loading.");
            document.querySelector("#usersTable").classList.add("table");
            return;
        }
        const table = new DataTable("#usersTable", {
            responsive: true,
            paging: true,
            searching: true,
            ordering: true,
            columnDefs: [
                { orderable: false, targets: 5 },
                { responsivePriority: 1, targets: 0 },
                { responsivePriority: 2, targets: 5 }
            ],
            language: {
                search: "Search users:",
                lengthMenu: "Show _MENU_ entries",
                info: "Showing _START_ to _END_ of _TOTAL_ users"
            }
        });
    };
    initDataTable();

    // Row click to navigate to user details
    const tbody = document.querySelector("#usersTable tbody");
    if (tbody) {
        tbody.addEventListener("click", (e) => {
            const target = e.target;
            if (!target.closest(".btn")) {
                const row = target.closest("tr");
                if (row) {
                    const userId = row.dataset.userId;
                    window.location.href = `/admin/users/${userId}`;
                }
            }
        });
    }

    // Trigger file input khi click vào avatar
    const avatarTrigger = document.querySelector("#avatarTrigger");
    const avatarPreview = document.querySelector("#avatarPreview");
    const userAvatar = document.querySelector("#userAvatar");
    const removeAvatarBtn = document.querySelector("#removeAvatarBtn");
    const defaultAvatarUrl = "https://via.placeholder.com/80"; // Định nghĩa giá trị mặc định cho avatar

    if (avatarTrigger && avatarPreview && userAvatar && removeAvatarBtn) {
        [avatarTrigger, avatarPreview].forEach(elem => {
            elem.addEventListener("click", () => {
                userAvatar.click();
            });
        });

        userAvatar.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                const validTypes = ["image/png", "image/jpg", "image/jpeg"];
                if (!validTypes.includes(file.type)) {
                    alert("Please upload only PNG, JPG, or JPEG files.");
                    e.target.value = "";
                    return;
                }
                const fileSizeMB = file.size / (1024 * 1024);
                if (fileSizeMB > 2) {
                    alert("File size exceeds 2MB limit.");
                    e.target.value = "";
                    return;
                }
                const reader = new FileReader();
                reader.onload = (event) => {
                    avatarPreview.src = event.target.result;
                    avatarPreview.classList.remove("d-none");
                    avatarTrigger.classList.add("d-none");
                    removeAvatarBtn.classList.remove("d-none");
                };
                reader.readAsDataURL(file);
            }
        });

        removeAvatarBtn.addEventListener("click", () => {
            avatarPreview.classList.add("d-none");
            avatarTrigger.classList.remove("d-none");
            removeAvatarBtn.classList.add("d-none");
            userAvatar.value = "";
            avatarPreview.src = defaultAvatarUrl; // Đặt lại về giá trị mặc định
        });
    }

    // Hàm hiển thị alert
    const showAlert = (message, type) => {
        const alertContainer = document.querySelector("#alertContainer");
        const alertDiv = document.createElement("div");
        alertDiv.className = `alert alert-${type} alert-dismissible fade`;
        alertDiv.role = "alert";
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertContainer.appendChild(alertDiv);
        setTimeout(() => alertDiv.classList.add("show"), 10);
        setTimeout(() => {
            alertDiv.classList.remove("show");
            setTimeout(() => alertDiv.remove(), 300);
        }, 3000);
    };

    // Xử lý submit form thêm/chỉnh sửa user
    const userForm = document.querySelector("#userForm");
    if (userForm) {
        userForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const formData = new FormData(userForm);
            const userId = formData.get("user_id");
            const url = userId ? `/admin/users/edit` : "/admin/users/add";

            const userAvatarInput = document.querySelector("#userAvatar");
            if (userAvatarInput && !userAvatarInput.files.length) {
                formData.delete("avatar"); // Xóa trường avatar nếu không có file được chọn
            }

            if (userId && !formData.get("password")) {
                formData.delete("password");
            }

            fetch(url, {
                method: "POST",
                body: formData
            })
            .then(response => {
                if (response.status === 201 || response.status === 200) {
                    showAlert(userId ? "User updated successfully" : "User created successfully", "success");
                    const modal = bootstrap.Modal.getInstance(userForm.closest(".modal"));
                    if (modal) modal.hide();
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    return response.json().then(data => {
                        throw new Error(data.detail || "Operation failed");
                    });
                }
            })
            .catch(error => {
                console.error("Fetch error:", error);
                showAlert(error.message, "danger");
            });
        });
    } else {
        console.error("User form not found in DOM");
    }

    // Xử lý delete user
    const deleteForm = document.querySelector("#deleteForm");
    if (deleteForm) {
        deleteForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const userId = document.querySelector("#deleteId").value;
            if (userId) {
                fetch(`/admin/users/delete`, {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: new URLSearchParams({ user_id: userId })
                })
                .then(response => {
                    if (response.status === 200) {
                        showAlert("User deleted successfully", "success");
                        const modal = bootstrap.Modal.getInstance(deleteForm.closest(".modal"));
                        if (modal) modal.hide();
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        return response.json().then(data => {
                            throw new Error(data.detail || "Delete failed");
                        });
                    }
                })
                .catch(error => {
                    showAlert(error.message, "danger");
                    console.error(error);
                });
            }
        });
    } else {
        console.error("Delete form not found in DOM");
    }
});

function resetUserModal() {
    const userForm = document.querySelector("#userForm");
    const defaultAvatarUrl = "https://via.placeholder.com/80";
    if (userForm) {
        userForm.reset();
        document.querySelector("#userId").value = "";
        document.querySelector("#userModalLabel").innerHTML = '<i class="bi bi-person-plus me-2"></i>Add User';
        const passwordField = document.querySelector("#passwordField");
        if (passwordField) passwordField.classList.remove("d-none");
        const userPassword = document.querySelector("#userPassword");
        if (userPassword) userPassword.required = true;
        document.querySelector("#userRole").value = "";
        document.querySelector("#userCountry").value = "";
        document.querySelector("#userTimezone").value = "";
        const avatarPreview = document.querySelector("#avatarPreview");
        const avatarTrigger = document.querySelector("#avatarTrigger");
        const removeAvatarBtn = document.querySelector("#removeAvatarBtn");
        const userAvatar = document.querySelector("#userAvatar");
        if (avatarPreview && avatarTrigger && removeAvatarBtn && userAvatar) {
            avatarPreview.classList.add("d-none");
            avatarTrigger.classList.remove("d-none");
            avatarPreview.src = defaultAvatarUrl;
            removeAvatarBtn.classList.add("d-none");
            userAvatar.value = ""; // Đặt lại input file
        }
    } else {
        console.error("User form not found for reset");
    }
}

function populateUserModal(id, username, fullname, email, role, date_of_birth, phone_number, country, timezone, website, avatar_url) {
    const defaultAvatarUrl = "https://via.placeholder.com/80";
    const userIdInput = document.querySelector("#userId");
    const userUsername = document.querySelector("#userUsername");
    const userFullname = document.querySelector("#userFullname");
    const userEmail = document.querySelector("#userEmail");
    const userRole = document.querySelector("#userRole");
    const userDateOfBirth = document.querySelector("#userDateOfBirth");
    const userPhoneNumber = document.querySelector("#userPhoneNumber");
    const userCountry = document.querySelector("#userCountry");
    const userTimezone = document.querySelector("#userTimezone");
    const userWebsite = document.querySelector("#userWebsite");
    const avatarPreview = document.querySelector("#avatarPreview");
    const avatarTrigger = document.querySelector("#avatarTrigger");
    const removeAvatarBtn = document.querySelector("#removeAvatarBtn");
    const passwordField = document.querySelector("#passwordField");
    const userPassword = document.querySelector("#userPassword");

    if (userIdInput && userUsername && userFullname && userEmail && userRole && userDateOfBirth && userPhoneNumber &&
        userCountry && userTimezone && userWebsite && avatarPreview && avatarTrigger && removeAvatarBtn &&
        passwordField && userPassword) {
        userIdInput.value = id;
        userUsername.value = username;
        userFullname.value = fullname || "";
        userEmail.value = email;
        userRole.value = role;
        userDateOfBirth.value = date_of_birth || "";
        userPhoneNumber.value = phone_number || "";
        userCountry.value = country || "";
        userTimezone.value = timezone || "";
        userWebsite.value = website || "";
        if (avatar_url && avatar_url.trim() !== "") {
            avatarPreview.src = avatar_url;
            avatarPreview.classList.remove("d-none");
            avatarTrigger.classList.add("d-none");
            removeAvatarBtn.classList.remove("d-none");
        } else {
            avatarPreview.classList.add("d-none");
            avatarTrigger.classList.remove("d-none");
            avatarPreview.src = defaultAvatarUrl;
            removeAvatarBtn.classList.add("d-none");
        }
        document.querySelector("#userModalLabel").innerHTML = '<i class="bi bi-pencil me-2"></i>Edit User';
        passwordField.classList.add("d-none");
        userPassword.required = false;
    } else {
        console.error("One or more elements not found in populateUserModal");
    }
}

function setDeleteId(id) {
    const deleteId = document.querySelector("#deleteId");
    if (deleteId) {
        deleteId.value = id;
    } else {
        console.error("DeleteId element not found");
    }
}