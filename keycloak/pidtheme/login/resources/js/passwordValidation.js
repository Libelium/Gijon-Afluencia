// themes/tu-tema/login/resources/js/passwordValidation.js

document.addEventListener('DOMContentLoaded', function () {
    const newPasswordField = document.getElementById('password-new');
    const confirmPasswordField = document.getElementById('password-confirm');
    const form = document.getElementById('kc-passwd-update-form');
    const submitButton = form.querySelector('input[type="submit"]'); // O el botón de enviar

    let passwordRequirements = [
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
            container.className = 'password-validation-messages'; // Clase para estilos CSS
            // Inserta el contenedor justo después del campo de entrada o su contenedor de campo.
            const fieldGroup = document.querySelector(`#${fieldId}`).closest('.app-text-field');
            if (fieldGroup) {
                fieldGroup.appendChild(container);
            } else {
                // Fallback si no se encuentra el contenedor .app-text-field
                document.querySelector(`#${fieldId}`).after(container);
            }
        }
        return container;
    }

    function validatePassword(password, fieldId) {
        const errors = [];
        const container = createErrorMessageContainer(fieldId);
        container.innerHTML = ''; // Limpiar mensajes anteriores

        // Validar longitud
        if (password.length < minLength || password.length > maxLength) {
            errors.push(`Must have between ${minLength} and ${maxLength} characters`);
        }

        // Validar requisitos de caracteres
        passwordRequirements.forEach(req => {
            if (!req.regex.test(password)) {
                errors.push(req.message);
            }
        });

        // Mostrar errores
        if (errors.length > 0) {
            errors.forEach(error => {
                const errorMessage = document.createElement('div');
                errorMessage.className = 'kcInputErrorMessageClass'; // Misma clase de error de Keycloak
                errorMessage.innerHTML = `<small>${error}</small>`;
                container.appendChild(errorMessage);
            });
            return false;
        }
        return true;
    }

    function validateConfirmPassword(confirmPassword, newPassword) {
        const container = createErrorMessageContainer('password-confirm');
        container.innerHTML = ''; // Limpiar mensajes anteriores
        if (confirmPassword !== newPassword) {
            const errorMessage = document.createElement('div');
            errorMessage.className = 'kcInputErrorMessageClass';
            errorMessage.innerHTML = `<small>Passwords do not match</small>`;
            container.appendChild(errorMessage);
            return false;
        }
        return true;
    }

    function checkFormValidity() {
        const isNewPasswordValid = validatePassword(newPasswordField.value, 'password-new');
        const isConfirmPasswordValid = validateConfirmPassword(confirmPasswordField.value, newPasswordField.value);

        // Habilitar/deshabilitar el botón de enviar
        if (submitButton) {
            submitButton.disabled = !(isNewPasswordValid && isConfirmPasswordValid && newPasswordField.value && confirmPasswordField.value);
        }
    }

    // Event Listeners
    if (newPasswordField) {
        newPasswordField.addEventListener('input', checkFormValidity);
    }
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('input', checkFormValidity);
    }

    // Validación inicial al cargar la página (por si hay valores precargados)
    checkFormValidity();
});