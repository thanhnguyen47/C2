document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const showRegister = document.getElementById("showRegister");
    const showLogin = document.getElementById("showLogin");

    // Hiển thị form đăng ký khi nhấn "Register"
    showRegister.addEventListener("click", (e) => {
        e.preventDefault();
        loginForm.classList.add("d-none");
        registerForm.classList.remove("d-none");
    });

    // Hiển thị form login khi nhấn "Login Now"
    showLogin.addEventListener("click", (e) => {
        e.preventDefault();
        registerForm.classList.add("d-none");
        loginForm.classList.remove("d-none");
    });

    // Xử lý submit form đăng ký
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("reg_username").value;
        const password = document.getElementById("reg_password").value;

        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ username, password })
        });

        const result = await response.json();
        if (response.ok) {
            alert(result.message);
            registerForm.classList.add("d-none");
            loginForm.classList.remove("d-none");
        } else {
            alert(result.detail);
        }
    });

    // Xử lý submit form login
    loginForm.addEventListener("submit", (e) => {
        e.preventDefault()
        const username = document.getElementById("username");
        const password = document.getElementById("password");

        fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ username: username.value, password: password.value })
        })
        .then(response => {
            if (response.ok){
                document.location="/dashboard"
            }
            else {
                username.value=""
                password.value=""
            }
        })
        .catch(error => {
            console.log("error: ", error)
        })
    });
});