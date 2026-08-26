<#import "template.ftl" as layout>

<@layout.registrationLayout
    displayMessage=!messagesPerField.existsError('username')
    displayInfo=true;
    section>


    <#-- ================================================================= -->
    <#-- SECTION: FORM (The Reset Password Card Content)                 -->
    <#-- ================================================================= -->
    <#if section = "form">

        <div class="login-card floating">
            <div class="v-card ">
                <div >
                    <div >
                        <h2 >${msg("emailForgotTitle")}</h2>
                        <p >
                            <#if realm.duplicateEmailsAllowed>
                                ${msg("emailInstructionUsername")}
                            <#else>
                                ${msg("emailInstruction")}
                            </#if>
                        </p>
                    </div>
                    <form id="kc-reset-password-form"  action="${url.loginAction}" method="post">
                        <div class="v-row">

                            <div class="v-col-12">
                                <div class="app-text-field ">
                                    <label class="v-label" for="username">
                                        <#if !realm.loginWithEmailAllowed>${msg("username")}<#elseif !realm.registrationEmailAsUsername>${msg("usernameOrEmail")}<#else>${msg("email")}</#if>
                                    </label>
                                    <div class="v-field">
                                        <input
                                            autofocus
                                            type="text"
                                            id="username"
                                            name="username"
                                            value="${(auth.attemptedUsername!'')}"
                                            class="v-field__input form-control"
                                            aria-invalid="<#if messagesPerField.existsError('username')>true</#if>"
                                            style="height: auto; border-radius: 10px;">
                                    </div>
                                    <#if messagesPerField.existsError('username')>
                                        <span id="input-error-username" class="kcInputErrorMessageClass"><small>${kcSanitize(messagesPerField.get('username'))?no_esc}</small></span>
                                    </#if>
                                </div>
                            </div>

                            <div class="login-form__psw">
                                <div class="d-flex justify-space-between align-center">
                                    <span><a href="${url.loginUrl}"><small>${kcSanitize(msg("backToLogin"))?no_esc}</small></a></span>
                                </div>
                            </div>

                            <button type="submit" class="v-btn " value="${msg("sendResetLink")}">
                                <span>${msg("sendResetLink")}</span>
                            </button>
                        </div>
                    </form>
                </div>
                
            </div>
            <div class="v-card login-infocard-wrapper">
                <div class="login-infocard">
                    <p>${msg("problemsAccount")}</p>
                    <a href="${properties.contactLoginIssuesUrl}">CONTACT US</a>
                </div>
            </div>
        </div>

    <#-- ================================================================= -->
    <#-- SECTION: INFO / SOCIAL PROVIDERS (No aplicable en este flujo)   -->
    <#-- ================================================================= -->
    <#elseif section = "socialProviders">
    </#if>

</@layout.registrationLayout>