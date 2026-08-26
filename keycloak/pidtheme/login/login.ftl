<#import "template.ftl" as layout>

<@layout.registrationLayout 
    displayMessage=!messagesPerField.existsError('username','password') 
    displayInfo=realm.password && realm.registrationAllowed && !registrationDisabled??; 
    section>        
        
    <#-- ================================================================= -->
    <#-- SECTION: FORM (The Login Card Content)                          -->
    <#-- ================================================================= -->
    <#if section = "form">
        
        <div class="login-card floating">
            <div class="v-card "> 
                <div >
                    <div >
                        <h2 >${msg("loginAccountTitle", realm.displayName!)}</h2>
            
                        <p >${msg("loginAccountSubtitle")}</p>
                    </div>
                    <form id="kc-form-login"  action="${url.loginAction}" method="post">
                        <div class="v-row">
                            
                            <div class="v-col-12">
                                <div class="app-text-field ">
                                    <label class="v-label" for="username">${msg("email")}</label>
                                    <div class="v-field">
                                        <input 
                                            autofocus
                                            name="username" 
                                            id="username" 
                                            value="${(login.username)!}" 
                                            class="v-field__input form-control"
                                            type="text"
                                            style="border-radius: 10px"
                                            >
                                    </div>
                                    <#if messagesPerField.existsError('username','password')>
                                        <span class="kcInputErrorMessageClass"><small>${messagesPerField.getFirstError('username','password')?no_esc}</small></span>
                                    </#if>
                                </div>
                            </div>

                            <div class="v-col-12">
                                <div class="app-text-field ">
                                    <label class="v-label" for="password">${msg("password")}</label>
                                    <div class="v-field">
                                        <input 
                                            name="password" 
                                            id="password" 
                                            value="${(login.password)!}" 
                                            class="v-field__input form-control"
                                            type="password"
                                            aria-controls="password"
                                            aria-invalid="<#if messagesPerField.existsError('password')>true</#if>"
                                            style="border-color: transparent !important; 
                                                    border-top-left-radius: 10px; border-bottom-left-radius: 10px"
                                            >
                                            <button                                                 
                                                type="button"
                                                aria-controls="password" 
                                                data-password-toggle
                                                data-icon-show="${properties.kcFormPasswordVisibilityIconShow!}" 
                                                data-icon-hide="${properties.kcFormPasswordVisibilityIconHide!}"
                                                style="background: none; border: none; height: 100%; width: 50px; padding: 5px; cursor: pointer;"
                                            >
                                                <i class="${properties.kcFormPasswordVisibilityIconShow!}" 
                                                
                                                aria-hidden="true">
                                                </i>
                                            </button>
                                    </div>
                                    <#if messagesPerField.existsError('username','password')>
                                        <span class="kcInputErrorMessageClass"><small>${messagesPerField.getFirstError('username','password')?no_esc}</small></span>
                                    </#if>
                                </div>

                            </div>
                            <div class="login-form__psw">
                                    <a href="${url.loginResetCredentialsUrl}"><small>${msg("doForgotPassword")}</small></a>
                            </div>
                            
                            <button type="submit" class="v-btn " name="login" id="kc-login">
                                <span>${msg("doSignIn")}</span>
                            </button>
                            <#if realm.password && realm.registrationAllowed && !registrationDisabled??>
                                <a href="${url.registrationUrl}" id="kc-register" class="v-btn kc-register-btn">
                                    <span>${msg("doRegister")}</span>
                                </a>
                            </#if>
                        </div>
                    </form>
                </div>
            </div>

            <#-- ================================================================= -->
            <#-- SECTION: OpenID Connect Identity Provider Button                -->
            <#-- ================================================================= -->
            <#if realm.password && social?? && social.providers?has_content>
                <#list social.providers as p>
                    <#if p.providerId == "oidc">
                        <div class="v-card" style="margin-top: 10px;">
                            <div style="text-align: center;">
                                <p style="margin-bottom: 15px;">Or sign in with</p>
                                <button type="submit" class="v-btn " name="login" id="kc-login">
                                    <a
                                        href="${p.loginUrl}"
                                        id="social-${p.alias}"
                                        style="width: 100%; display: flex; align-items: center; justify-content: center; color: #FFF; text-decoration: none;">
                                        <span>${p.displayName!}</span>
                                    </a>
                                </button>
                                
                            </div>
                        </div>
                    </#if>
                </#list>
            </#if>

            <div class="v-card login-infocard-wrapper">
                <div class="login-infocard">
                    <p>${msg("noAccountYet")}</p>
                    <a href="${properties.registrationLinkUrl}">${msg("discoverPlatform")}</a>
                </div>
            </div>

        </div>
        

    <#-- ================================================================= -->
    <#-- SECTION: INFO / SOCIAL PROVIDERS                                -->
    <#-- ================================================================= -->
    <#elseif section = "socialProviders">
        </#if>

</@layout.registrationLayout>