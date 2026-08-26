<#import "template.ftl" as layout>
<#import "password-commons.ftl" as passwordCommons>

<@layout.registrationLayout
    displayMessage=!messagesPerField.existsError('password','password-confirm');
    section>


    <#-- ================================================================= -->
    <#-- SECTION: FORM (The Update Password Card Content)                 -->
    <#-- ================================================================= -->

    <#if section = "form">

        <div class="login-card floating">
            <div class="v-card ">
                <div >
                    <div >
                        <h2 >${msg("updatePasswordTitle")}</h2>
                        <p >${msg("updatePasswordSubtitle")}</p>
                    </div>
                    <form id="kc-passwd-update-form"  action="${url.loginAction}" method="post">
                        <div class="v-row">

                            <div class="v-col-12">
                                <div class="app-text-field ">
                                    <label class="v-label" for="password-new">${msg("passwordNew")}</label>
                                    <div class="v-field password-field-group">
                                        <input
                                            type="password"
                                            id="password-new"
                                            name="password-new"
                                            class="v-field__input form-control"
                                            autofocus autocomplete="new-password"
                                            style="height: auto; border-radius: 10px;"
                                        />
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
                                    <div id="password-validation-messages-password-new" class="password-validation-messages"></div>
                                </div>
                            </div>

                            <div class="v-col-12">
                                <div class="app-text-field ">
                                    <label class="v-label" for="password-confirm">${msg("passwordConfirm")}</label>
                                    <div class="v-field password-field-group">
                                        <input
                                            type="password"
                                            id="password-confirm"
                                            name="password-confirm"
                                            class="v-field__input form-control"
                                            autocomplete="new-password"
                                            style="height: auto; border-radius: 10px;"
                                        />
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
                                    <div id="password-validation-messages-password-confirm" class="password-validation-messages"></div>
                                </div>
                            </div>

                            <div class="v-col-12">
                                <div id="kc-form-buttons">
                                    <#if isAppInitiatedAction??>
                                        <div class="v-row"> 
                                            <div class="v-col-10 offset-1"> 
                                                <input class="v-btn " type="submit" value="${msg("setNewPassword")}" /> 
                                            </div>
                                        </div>
                                        <div class="v-row" style="margin-top: 12px;"> 
                                            <div class="v-col-10 offset-1"> 
                                                <button class="v-btn bg-secondary" type="submit" name="cancel-aia" value="true">${msg("doCancel")}</button> 
                                            </div>
                                        </div>
                                    <#else>
                                        <div class="v-col-10 offset-1"> 
                                            <input class="v-btn " type="submit" value="${msg("setNewPassword")}" /> 
                                        </div>                                    
                                    </#if>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <script type="module" src="${url.resourcesPath}/js/passwordVisibility.js"></script>
        <script type="text/javascript" src="${url.resourcesPath}/js/passwordValidation.js"></script> <#-- ¡Añadido! -->
    </#if>
</@layout.registrationLayout>