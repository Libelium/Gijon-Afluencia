// Keycloak requires a `username` field on the register form unless the realm has
// registrationEmailAsUsername enabled. On this platform the identity is always the email, so
// when the flag is off (register.ftl then renders a hidden username input) we mirror
// the email into it. That way registration works on any realm without having to flip
// the flag by hand — a realm imported before the flag was set keeps the old value.
document.addEventListener('DOMContentLoaded', function () {
    const emailField = document.getElementById('email');
    const usernameField = document.getElementById('username');
    const form = document.getElementById('kc-register-form');
    if (!form || !emailField || !usernameField) {
        return;
    }

    function syncUsername() {
        usernameField.value = emailField.value.trim();
    }

    emailField.addEventListener('input', syncUsername);
    emailField.addEventListener('change', syncUsername);
    form.addEventListener('submit', syncUsername);

    // Cover autofill and the re-render after a validation error.
    syncUsername();
});
