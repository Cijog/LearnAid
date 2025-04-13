const loginForm = document.querySelector(".login-form");
const signupForm = document.querySelector(".signup-form");
const signUpButtons = document.querySelectorAll(".sign-up-btn");
const loginButtons = document.querySelectorAll(".login-btn");
const backLayer = document.querySelector(".back-layer");

signUpButtons.forEach(button => {
    button.addEventListener("click", () => {
        loginForm.classList.remove("active");
        signupForm.classList.add("active");
        backLayer.style.clipPath = "inset(0 0 0 50%)";
    });
});

loginButtons.forEach(button => {
    button.addEventListener("click", () => {
        signupForm.classList.remove("active");
        loginForm.classList.add("active");
        backLayer.style.clipPath = "";
    });
});
document.addEventListener('DOMContentLoaded', function () {
    // Select the buttons and forms
    const signUpBtn = document.querySelector('.sign-up-btn');
    const loginBtn = document.querySelector('.login-btn');
    const loginForm = document.querySelector('.login-form');
    const signUpForm = document.querySelector('.signup-form');

    // Add event listener for "Sign up here" link
    signUpBtn.addEventListener('click', function () {
        loginForm.classList.remove('active');
        signUpForm.classList.add('active');
    });

    // Add event listener for "Login here" link
    loginBtn.addEventListener('click', function () {
        signUpForm.classList.remove('active');
        loginForm.classList.add('active');
    });
});

