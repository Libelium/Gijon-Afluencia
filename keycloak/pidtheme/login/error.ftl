<#import "template.ftl" as layout>

<@layout.registrationLayout displayMessage=false; section>

    <#-- ================================================================= -->
    <#-- SECTION: FORM (The "Error Message" Card Content)                -->
    <#-- ================================================================= -->
    <#if section = "form">

        <div class="login-card floating">
            <div class="v-card ">
                <div >
                    <div >
                        <h2 >${kcSanitize(msg("errorTitle"))?no_esc}</h2>
                        <p >${kcSanitize(message.summary)?no_esc}</p> 
                    </div>
                    <div id="kc-error-message"> 
                        <#if client?? && client.baseUrl?has_content>
                            <p><a id="backToLogin" href="${client.baseUrl}" class="v-btn">${kcSanitize(msg("backToLogin"))?no_esc}</a></p>
                        </#if>
                    </div>
                </div>
            </div>
        </div>

    </#if>
</@layout.registrationLayout>