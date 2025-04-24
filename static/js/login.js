
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
    registerForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const fullname = document.getElementById("reg_fullname");
        const username = document.getElementById("reg_username");
        const email = document.getElementById("reg_email");
        const password = document.getElementById("reg_password");

        fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ fullname: fullname.value, username: username.value, email: email.value, password: password.value })
        })
        .then(r=>{
            if (r.status === 201) {
                alert("Register success, check the email to verify account")
                registerForm.classList.add("d-none")
                loginForm.classList.remove("d-none")
            } else {
                alert("Register fail")
            }
            fullname.value = ""
            username.value = ""
            email.value = ""
            password.value = ""
        })
        .catch(e=>console.log(e))
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