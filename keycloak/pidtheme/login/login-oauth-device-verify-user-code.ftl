<#import "template.ftl" as layout>

<@layout.registrationLayout displayMessage=true; section>

    <#-- ================================================================= -->
    <#-- SECTION: FORM — Confirmación del código de dispositivo          -->
    <#-- ================================================================= -->
    <#if section = "form">

        <div class="login-card floating">
            <div class="v-card">
                <div>

                    <div>
                        <h2>${msg("oauth2DeviceVerificationTitle")}</h2>
                        <p>${msg("oauth2DeviceVerificationConfirm")}</p>
                    </div>

                    <#-- Código mostrado en pantalla -->
                    <div style="
                        text-align: center;
                        margin: 20px 0;
                        padding: 16px;
                        border-radius: 10px;
                        background: rgba(var(--kc-bg-color-start-rgb, 0,0,0), 0.06);
                        border: 1px solid rgba(var(--kc-bg-color-start-rgb, 0,0,0), 0.12);">
                        <span style="
                            font-size: 2em;
                            font-weight: 700;
                            letter-spacing: 0.3em;
                            color: var(--kc-bg-color-start);">
                            ${userCode!}
                        </span>
                    </div>

                    <form
                        id="kc-user-verify-device-user-code-confirm-form"
                        action="${url.oauth2DeviceVerificationAction}"
                        method="post">

                        <input type="hidden" name="device_user_code" value="${userCode!}">

                        <div class="v-row">
                            <div class="v-col-12" style="display: flex; gap: 12px; margin-top: 8px;">
                                <button
                                    type="submit"
                                    name="accept"
                                    id="kc-login"
                                    class="v-btn"
                                    style="flex: 1;">
                                    <span>${msg("doYes")}</span>
                                </button>
                                <button
                                    type="submit"
                                    name="cancel"
                                    id="kc-cancel"
                                    class="v-btn"
                                    style="flex: 1; color: var(--kc-bg-color-start); background-color: white !important; border: 1px solid var(--kc-bg-color-start);">
                                    <span>${msg("doNo")}</span>
                                </button>
                            </div>
                        </div>
                    </form>

                </div>
            </div>
        </div>

    </#if>

</@layout.registrationLayout>
