document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const forgotPasswordForm = document.getElementById("forgotPasswordForm");
    const loginFormContainer = document.getElementById("loginFormContainer");
    const registerFormContainer = document.getElementById("registerFormContainer");
    const forgotPasswordFormContainer = document.getElementById("forgotPasswordFormContainer");
    const showRegister = document.getElementById("showRegister");
    const showLogin = document.getElementById("showLogin");
    const showForgotPassword = document.getElementById("showForgotPassword");
    const showLoginFromForgot = document.getElementById("showLoginFromForgot");
    const alertContainer = document.getElementById("alertContainer");

    // show alert
    function showAlert(message, type = "success") {
        const alert = document.createElement("div");
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.role = "alert";
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertContainer.appendChild(alert);
        setTimeout(() => alert.remove(), 5000);
    }

    // Hàm bật/tắt loading spinner
    function toggleSpinner(form, show) {
        const button = form.querySelector("button[type=submit]");
        const spinner = button.querySelector(".spinner-border");
        if (show) {
            button.disabled = true;
            spinner.classList.remove("d-none");
        } else {
            button.disabled = false;
            spinner.classList.add("d-none");
        }
    }

    // check strong password
    function validatePassword(password) {
        const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
        if (!regex.test(password)) {
            return "Password must be at least 8 characters long and include uppercase, lowercase, and numbers.";
        }
        return null;
    }

    // show form register
    showRegister.addEventListener("click", (e) => {
        e.preventDefault();
        loginFormContainer.classList.add("d-none");
        registerFormContainer.classList.remove("d-none");
        forgotPasswordFormContainer.classList.add("d-none");
    });

    // show form login
    showLogin.addEventListener("click", (e) => {
        e.preventDefault();
        registerFormContainer.classList.add("d-none");
        loginFormContainer.classList.remove("d-none");
        forgotPasswordFormContainer.classList.add("d-none");
    });

    // show form forgot password
    showForgotPassword.addEventListener("click", (e) => {
        e.preventDefault();
        loginFormContainer.classList.add("d-none");
        registerFormContainer.classList.add("d-none");
        forgotPasswordFormContainer.classList.remove("d-none");
    });

    // show form login from forgot password
    showLoginFromForgot.addEventListener("click", (e) => {
        e.preventDefault();
        forgotPasswordFormContainer.classList.add("d-none");
        loginFormContainer.classList.remove("d-none");
        registerFormContainer.classList.add("d-none");
    });

    //  submit form register
    registerForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const fullname = document.getElementById("reg_fullname");
        const username = document.getElementById("reg_username");
        const email = document.getElementById("reg_email");
        const password = document.getElementById("reg_password");

        // check strong password 
        const passwordError = validatePassword(password.value);
        if (passwordError) {
            showAlert(passwordError, "danger");
            return;
        }

        toggleSpinner(registerForm, true);
        fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ fullname: fullname.value, username: username.value, email: email.value, password: password.value })
        })
        .then(r => {
            toggleSpinner(registerForm, false);
            if (r.status === 201) {
                showAlert("Register success, check your email to verify account", "success");
                registerFormContainer.classList.add("d-none");
                loginFormContainer.classList.remove("d-none");
            } else {
                return r.json().then(data => {
                    throw new Error(data.detail || "Register failed");
                });
            }
        })
        .catch(e => {
            toggleSpinner(registerForm, false);
            showAlert(e.message, "danger");
            console.log(e);
        })
        .finally(() => {
            fullname.value = "";
            username.value = "";
            email.value = "";
            password.value = "";
        });
    });

    // submit form login
    loginForm.addEventListener("submit", (e) => {
        e.preventDefault();
        toggleSpinner(loginForm, true);
        const username = document.getElementById("username");
        const password = document.getElementById("password");

        fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ username: username.value, password: password.value })
        })
        .then(response => {
            toggleSpinner(loginForm, false);
            if (response.ok) {
                document.location = "/dashboard";
            } else {
                return response.json().then(data => {
                    throw new Error(data.detail || "Incorrect username or password");
                });
            }
        })
        .catch(error => {
            toggleSpinner(loginForm, false);
            showAlert(error.message, "danger");
            console.log("error: ", error);
            username.value = "";
            password.value = "";
        });
    });

    // submit form forgot password
    forgotPasswordForm.addEventListener("submit", (e) => {
        e.preventDefault();
        toggleSpinner(forgotPasswordForm, true);
        const email = document.getElementById("forgot_email");

        fetch("/forgot-password", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ email: email.value })
        })
        .then(response => {
            toggleSpinner(forgotPasswordForm, false);
            if (response.ok) {
                showAlert("Password reset link sent to your email", "success");
                forgotPasswordFormContainer.classList.add("d-none");
                loginFormContainer.classList.remove("d-none");
                email.value = "";
            } else {
                return response.json().then(data => {
                    throw new Error(data.detail || "Failed to send reset link");
                });
            }
        })
        .catch(error => {
            toggleSpinner(forgotPasswordForm, false);
            showAlert(error.message, "danger");
            console.log("error: ", error);
            email.value = "";
        });
    });
});