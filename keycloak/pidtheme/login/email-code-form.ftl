<#import "template.ftl" as layout>

<@layout.registrationLayout
    displayMessage=!messagesPerField.existsError('emailCode')
    displayInfo=false;
    section>

    <#-- ================================================================= -->
    <#-- SECTION: HEADER (Title, Subtitle, and Logo Placement)           -->
    <#-- ================================================================= -->
    <#if section = "header">
    <@layout.parallax/>


    <#-- ================================================================= -->
    <#-- SECTION: FORM (The OTP Login Card Content)                      -->
    <#-- ================================================================= -->
    <#elseif section = "form">

        <div class="login-card floating">
            <div class="v-card">
                <div >
                    <div >
                        <h2 >${msg("doLogIn")}</h2> 
                        <p >${msg("emailOtpForm")}</p> 
                    </div>
                    <form id="kc-otp-login-form"  action="${url.loginAction}" method="post">
                        <div class="v-row">

                            <div class="v-col-12">
                                <div class="app-text-field ">
                                    <div class="v-field">
                                        <input
                                            id="emailCode"
                                            name="emailCode"
                                            autocomplete="off"
                                            type="text"
                                            class="v-field__input form-control"
                                            autofocus
                                            aria-invalid="<#if messagesPerField.existsError('emailCode')>true</#if>"
                                            style="height: auto; border-radius: 10px;">
                                    </div>
                                    <#if messagesPerField.existsError('emailCode')>
                                        <span id="input-error-otp-code" class="kcInputErrorMessageClass"><small>${kcSanitize(messagesPerField.get('emailCode'))?no_esc}</small></span>
                                    </#if>
                                </div>
                            </div>

                            <div class="v-col-12" style="margin-top: 12px;"> 
                                <button type="submit" name="login" class="v-btn " id="kc-login-otp"> 
                                    <span >${msg("doLogIn")}</span>
                                </button>
                                <div style="display: flex; justify-content: space-between; margin-top: 12px;">

                                    <button 
                                        type="submit" 
                                        name="resend" 
                                        class="v-btn " 
                                        id="kc-resend-otp" 
                                        style="
                                            width: 45%;
                                            color: var(--kc-bg-color-start);
                                            background-color: white !important;
                                            border: 1px solid var(--kc-bg-color-start);
                                        ">

                                        <span >${msg("resendCode")}</span>
                                    </button>

                                    <button 
                                        type="submit" 
                                        name="cancel" 
                                        class="v-btn"
                                        id="kc-cancel-otp"
                                        style="
                                            width: 45%;
                                            color: var(--kc-bg-color-start);
                                            background-color: white !important;
                                            border: 1px solid var(--kc-bg-color-start);
                                        ">
                                        
                                        <span >${msg("doCancel")}</span>
                                    </button>
                                </div>
                            </div>

                        </div>
                    </form>
                </div>
            </div>
            

        </div>

    <#-- ================================================================= -->
    <#-- SECTION: INFO / SOCIAL PROVIDERS (No aplicable en este flujo)   -->
    <#-- ================================================================= -->
    <#elseif section = "socialProviders">
    </#if>

</@layout.registrationLayout>