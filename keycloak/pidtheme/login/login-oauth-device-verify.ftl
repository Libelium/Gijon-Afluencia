<#import "template.ftl" as layout>

<@layout.registrationLayout displayMessage=true; section>

    <#-- ================================================================= -->
    <#-- SECTION: FORM — Introducción del código de dispositivo          -->
    <#-- ================================================================= -->
    <#if section = "form">

        <div class="login-card floating">
            <div class="v-card">
                <div>

                    <div>
                        <h2>${msg("oauth2DeviceVerificationTitle")}</h2>
                        <p>${msg("oauth2DeviceVerificationInstruction")}</p>
                    </div>

                    <form
                        id="kc-user-verify-device-user-code-form"
                        action="${url.oauth2DeviceVerificationAction}"
                        method="post">

                        <div class="v-row">

                            <div class="v-col-12">
                                <div class="app-text-field">
                                    <label class="v-label" for="device-user-code">
                                        ${msg("verifyOAuth2DeviceUserCode")}
                                    </label>
                                    <div class="v-field">
                                        <input
                                            id="device-user-code"
                                            name="device_user_code"
                                            autocomplete="off"
                                            type="text"
                                            class="v-field__input form-control"
                                            autofocus
                                            dir="ltr"
                                            style="border-radius: 10px; text-transform: uppercase; letter-spacing: 0.2em; text-align: center; font-size: 1.2em;"
                                            placeholder="XXXX-XXXX">
                                    </div>
                                    <#if messagesPerField?? && messagesPerField.existsError('device_user_code')>
                                        <span class="kcInputErrorMessageClass">
                                            <small>${kcSanitize(messagesPerField.get('device_user_code'))?no_esc}</small>
                                        </span>
                                    </#if>
                                </div>
                            </div>

                            <div class="v-col-12" style="margin-top: 12px;">
                                <button
                                    type="submit"
                                    class="v-btn"
                                    id="kc-login">
                                    <span>${msg("doSubmit")}</span>
                                </button>
                            </div>

                        </div>
                    </form>

                </div>
            </div>
        </div>

    </#if>

</@layout.registrationLayout>
