
document.addEventListener("DOMContentLoaded", () => {
    // Khởi tạo DataTables
    const table = new DataTable("#topicsTable", {
        responsive: true,
        paging: true,
        searching: true,
        ordering: true,
        columnDefs: [
            { orderable: false, targets: 4 },
            { responsivePriority: 1, targets: 0 },
            { responsivePriority: 2, targets: 4 }
        ],
        language: {
            search: "Search topics:",
            lengthMenu: "Show _MENU_ entries",
            info: "Showing _START_ to _END_ of _TOTAL_ topics"
        }
    });

    // Row click to navigate to topic details
    const tbody = document.querySelector("#topicsTable tbody");
    if (tbody) {
        tbody.addEventListener("click", (e) => {
            const target = e.target;
            if (!target.closest(".btn")) {
                const row = target.closest("tr");
                if (row) {
                    const topicId = row.dataset.topicId;
                    window.location.href = `/admin/topics/${topicId}`;
                }
            }
        });
    }

    // Preview icon when selected
    const iconSelect = document.querySelector("#topicIcon");
    const iconPreview = document.querySelector("#iconPreview");
    if (iconSelect && iconPreview) {
        iconSelect.addEventListener("change", () => {
            const selectedIcon = iconSelect.value;
            iconPreview.innerHTML = `<i class="bi ${selectedIcon}"></i>`;
        });
        // Set initial preview
        iconPreview.innerHTML = `<i class="bi ${iconSelect.value}"></i>`;
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

    // Xử lý submit form thêm/chỉnh sửa topic
    const topicForm = document.querySelector("#topicForm");
    if (topicForm) {
        topicForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const formData = new FormData(topicForm);
            const topicId = formData.get("topic_id");
            const url = topicId ? `/admin/topics/edit` : "/admin/topics/add";

            fetch(url, {
                method: "POST",
                body: formData
            })
            .then(response => {
                if (response.status === 201 || response.status === 200) {
                    showAlert(topicId ? "Topic updated successfully" : "Topic created successfully", "success");
                    const modal = bootstrap.Modal.getInstance(topicForm.closest(".modal"));
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
    }

    // Xử lý delete topic
    const deleteForm = document.querySelector("#deleteForm");
    if (deleteForm) {
        deleteForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const topicId = document.querySelector("#deleteId").value;
            if (topicId) {
                fetch(`/admin/topics/delete`, {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: new URLSearchParams({ topic_id: topicId })
                })
                .then(response => {
                    if (response.status === 200) {
                        showAlert("Topic deleted successfully", "success");
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
    }
});

function resetTopicModal() {
    const topicForm = document.querySelector("#topicForm");
    if (topicForm) {
        topicForm.reset();
        document.querySelector("#topicId").value = "";
        document.querySelector("#topicModalLabel").innerHTML = '<i class="bi bi-plus-circle me-2"></i>Add Topic';
        document.querySelector("#topicIcon").value = "bi-database";
        document.querySelector("#iconPreview").innerHTML = '<i class="bi bi-database"></i>';
    }
}

function populateTopicModal(id, title, shortDescription, description, type, icon) {
    const topicIdInput = document.querySelector("#topicId");
    const topicTitle = document.querySelector("#topicTitle");
    const topicShortDescription = document.querySelector("#topicShortDescription");
    const topicDescription = document.querySelector("#topicDescription");
    const topicType = document.querySelector("#topicType");
    const topicIcon = document.querySelector("#topicIcon");
    const iconPreview = document.querySelector("#iconPreview");

    if (topicIdInput && topicTitle && topicShortDescription && topicDescription && topicType && topicIcon && iconPreview) {
        topicIdInput.value = id;
        topicTitle.value = title;
        topicShortDescription.value = shortDescription || "";
        topicDescription.value = description || "";
        topicType.value = type || "";
        topicIcon.value = icon || "bi-database";
        iconPreview.innerHTML = `<i class="bi ${icon || 'bi-database'}"></i>`;
        document.querySelector("#topicModalLabel").innerHTML = '<i class="bi bi-pencil me-2"></i>Edit Topic';
    }
}

function setDeleteId(id) {
    const deleteId = document.querySelector("#deleteId");
    if (deleteId) {
        deleteId.value = id;
    }
}