// Live password-policy hints for the registration form.
// Mirrors passwordValidation.js (used by the change-password view) but targets the
// register form ids. Rules match the realm passwordPolicy
// (length 8-30, upper, lower, digit, special). Server-side policy still enforces it.

document.addEventListener('DOMContentLoaded', function () {
    const newPasswordField = document.getElementById('password');
    const confirmPasswordField = document.getElementById('password-confirm');
    const form = document.getElementById('kc-register-form');
    if (!form || !newPasswordField) {
        return;
    }
    const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');

    const passwordRequirements = [
        { regex: /[a-z]/, message: 'Must contain at least one lowercase' },
        { regex: /[A-Z]/, message: 'Must contain at least one uppercase' },
        { regex: /[0-9]/, message: 'Must contain at least one digit' },
        { regex: /[!@#$%&*()]/, message: 'Must contain at least one special character' },
    ];

    const minLength = 8;
    const maxLength = 30;

    function createErrorMessageContainer(fieldId) {
        let container = document.getElementById(`password-validation-messages-${fieldId}`);
        if (!container) {
            container = document.createElement('div');
            container.id = `password-validation-messages-${fieldId}`;
            container.className = 'password-validation-messages';
            const fieldGroup = document.querySelector(`#${fieldId}`).closest('.app-text-field');
            if (fieldGroup) {
                fieldGroup.appendChild(container);
            } else {
                document.querySelector(`#${fieldId}`).after(container);
            }
        }
        return container;
    }

    function validatePassword(password, fieldId) {
        const errors = [];
        const container = createErrorMessageContainer(fieldId);
        container.innerHTML = '';

        if (password.length < minLength || password.length > maxLength) {
            errors.push(`Must have between ${minLength} and ${maxLength} characters`);
        }

        passwordRequirements.forEach(req => {
            if (!req.regex.test(password)) {
                errors.push(req.message);
            }
        });

        if (errors.length > 0) {
            errors.forEach(error => {
                const el = document.createElement('div');
                el.className = 'kcInputErrorMessageClass';
                el.innerHTML = `<small>${error}</small>`;
                container.appendChild(el);
            });
            return false;
        }
        return true;
    }

    function validateConfirmPassword(confirmPassword, newPassword) {
        const container = createErrorMessageContainer('password-confirm');
        container.innerHTML = '';
        if (confirmPassword !== newPassword) {
            const el = document.createElement('div');
            el.className = 'kcInputErrorMessageClass';
            el.innerHTML = `<small>Passwords do not match</small>`;
            container.appendChild(el);
            return false;
        }
        return true;
    }

    function checkFormValidity() {
        const okPassword = validatePassword(newPasswordField.value, 'password');
        const okConfirm = validateConfirmPassword(confirmPasswordField.value, newPasswordField.value);
        if (submitButton) {
            submitButton.disabled = !(okPassword && okConfirm && newPasswordField.value && confirmPasswordField.value);
        }
    }

    newPasswordField.addEventListener('input', checkFormValidity);
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('input', checkFormValidity);
    }

    checkFormValidity();
});
