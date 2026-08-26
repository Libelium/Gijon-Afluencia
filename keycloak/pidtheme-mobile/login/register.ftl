<#import "template.ftl" as layout>

<#--
   Mobile-only two-step registration.
   Step 1: email + first name + last name  -> [Next] [Back to login]
   Step 2: password + confirm              -> [Register] [Back]
   Both steps live inside a single <form>; steps are just show/hidden <div>s, so
   the final submit still posts every field. On a server-side error we open the
   step that owns the failing field.
-->
<@layout.registrationLayout
    displayMessage=messagesPerField.exists('global')
    displayRequiredFields=false;
    section>

    <#if section = "form">

        <#assign step1Error = messagesPerField.existsError('email','firstName','lastName')>
        <#assign step2Error = messagesPerField.existsError('password','password-confirm')>
        <#assign showStep2 = step2Error && !step1Error>

        <div class="login-card floating">
            <div class="v-card ">
                <div>
                    <div>
                        <h2>${msg("registerTitle")}</h2>
                        <p>${msg("registerSubtitle")}</p>
                    </div>

                    <form id="kc-register-form" action="${url.registrationAction}" method="post">
                        <#if !realm.registrationEmailAsUsername>
                            <input type="hidden" name="username" id="username" value="${(register.formData.username!'')}">
                        </#if>

                        <#-- ===================== STEP 1: email + names ===================== -->
                        <div id="reg-step-1" class="reg-step"<#if showStep2> hidden</#if>>
                            <div class="v-row">

                                <div class="v-col-12">
                                    <div class="app-text-field ">
                                        <label class="v-label" for="email">${msg("email")}</label>
                                        <div class="v-field">
                                            <input <#if !showStep2>autofocus</#if>
                                                name="email" id="email"
                                                value="${(register.formData.email!'')}"
                                                class="v-field__input form-control" type="email"
                                                autocomplete="email" required
                                                style="border-radius: 10px">
                                        </div>
                                        <#-- username errors (e.g. already taken) belong to the email field here -->
                                        <#if messagesPerField.existsError('email','username')>
                                            <span class="kcInputErrorMessageClass"><small>${kcSanitize(messagesPerField.getFirstError('email','username'))?no_esc}</small></span>
                                        </#if>
                                    </div>
                                </div>

                                <div class="v-col-12">
                                    <div class="app-text-field ">
                                        <label class="v-label" for="firstName">${msg("firstName")}</label>
                                        <div class="v-field">
                                            <input name="firstName" id="firstName"
                                                value="${(register.formData.firstName!'')}"
                                                class="v-field__input form-control" type="text"
                                                autocomplete="given-name" required
                                                style="border-radius: 10px">
                                        </div>
                                        <#if messagesPerField.existsError('firstName')>
                                            <span class="kcInputErrorMessageClass"><small>${kcSanitize(messagesPerField.get('firstName'))?no_esc}</small></span>
                                        </#if>
                                    </div>
                                </div>

                                <div class="v-col-12">
                                    <div class="app-text-field ">
                                        <label class="v-label" for="lastName">${msg("lastName")}</label>
                                        <div class="v-field">
                                            <input name="lastName" id="lastName"
                                                value="${(register.formData.lastName!'')}"
                                                class="v-field__input form-control" type="text"
                                                autocomplete="family-name" required
                                                style="border-radius: 10px">
                                        </div>
                                        <#if messagesPerField.existsError('lastName')>
                                            <span class="kcInputErrorMessageClass"><small>${kcSanitize(messagesPerField.get('lastName'))?no_esc}</small></span>
                                        </#if>
                                    </div>
                                </div>

                                <button type="button" class="v-btn" id="reg-next">
                                    <span>${msg("doNext")}</span>
                                </button>
                                <a href="${url.loginUrl}" id="kc-back-to-login" class="v-btn kc-register-btn">
                                    <span>${msg("backToLogin")?no_esc}</span>
                                </a>
                            </div>
                        </div>

                        <#-- ===================== STEP 2: passwords ===================== -->
                        <div id="reg-step-2" class="reg-step"<#if !showStep2> hidden</#if>>
                            <div class="v-row">

                                <div class="v-col-12">
                                    <div class="app-text-field ">
                                        <label class="v-label" for="password">${msg("password")}</label>
                                        <div class="v-field">
                                            <input name="password" id="password"
                                                class="v-field__input form-control" type="password"
                                                autocomplete="new-password"
                                                style="border-color: transparent !important; border-top-left-radius: 10px; border-bottom-left-radius: 10px">
                                            <button type="button" aria-controls="password" data-password-toggle
                                                data-icon-show="${properties.kcFormPasswordVisibilityIconShow!}"
                                                data-icon-hide="${properties.kcFormPasswordVisibilityIconHide!}"
                                                style="background: none; border: none; height: 100%; width: 50px; padding: 5px; cursor: pointer;">
                                                <i class="${properties.kcFormPasswordVisibilityIconShow!}" aria-hidden="true"></i>
                                            </button>
                                        </div>
                                        <#if messagesPerField.existsError('password')>
                                            <span class="kcInputErrorMessageClass"><small>${kcSanitize(messagesPerField.get('password'))?no_esc}</small></span>
                                        </#if>
                                    </div>
                                </div>

                                <div class="v-col-12">
                                    <div class="app-text-field ">
                                        <label class="v-label" for="password-confirm">${msg("passwordConfirm")}</label>
                                        <div class="v-field">
                                            <input name="password-confirm" id="password-confirm"
                                                class="v-field__input form-control" type="password"
                                                autocomplete="new-password"
                                                style="border-color: transparent !important; border-top-left-radius: 10px; border-bottom-left-radius: 10px">
                                            <button type="button" aria-controls="password-confirm" data-password-toggle
                                                data-icon-show="${properties.kcFormPasswordVisibilityIconShow!}"
                                                data-icon-hide="${properties.kcFormPasswordVisibilityIconHide!}"
                                                style="background: none; border: none; height: 100%; width: 50px; padding: 5px; cursor: pointer;">
                                                <i class="${properties.kcFormPasswordVisibilityIconShow!}" aria-hidden="true"></i>
                                            </button>
                                        </div>
                                        <#if messagesPerField.existsError('password-confirm')>
                                            <span class="kcInputErrorMessageClass"><small>${kcSanitize(messagesPerField.get('password-confirm'))?no_esc}</small></span>
                                        </#if>
                                    </div>
                                </div>

                                <button type="submit" class="v-btn" name="register" id="kc-register">
                                    <span>${msg("doRegister")}</span>
                                </button>
                                <button type="button" class="v-btn kc-register-btn" id="reg-back">
                                    <span>${msg("doBack")}</span>
                                </button>
                            </div>
                        </div>

                    </form>
                </div>
            </div>
        </div>

        <script type="text/javascript" src="${url.resourcesPath}/js/registerPasswordValidation.js"></script>
        <script type="text/javascript" src="${url.resourcesPath}/js/registerEmailAsUsername.js"></script>
        <script type="text/javascript">
            (function () {
                var step1 = document.getElementById('reg-step-1');
                var step2 = document.getElementById('reg-step-2');
                var next  = document.getElementById('reg-next');
                var back  = document.getElementById('reg-back');

                function swap(showEl, hideEl, focusId) {
                    hideEl.hidden = true;
                    showEl.hidden = false;
                    var f = document.getElementById(focusId);
                    if (f) f.focus();
                }

                if (next) {
                    next.addEventListener('click', function () {
                        // Only advance if the step-1 fields are valid (required / email format).
                        var inputs = step1.querySelectorAll('input');
                        for (var i = 0; i < inputs.length; i++) {
                            if (!inputs[i].reportValidity()) return;
                        }
                        swap(step2, step1, 'password');
                    });
                }
                if (back) {
                    back.addEventListener('click', function () {
                        swap(step1, step2, 'email');
                    });
                }
            })();
        </script>

    </#if>

</@layout.registrationLayout>
