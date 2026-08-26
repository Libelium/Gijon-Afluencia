<#import "template.ftl" as layout>

<@layout.registrationLayout displayMessage=false; section>

    <#-- ================================================================= -->
    <#-- SECTION: FORM (The "Info Message" Card Content)                 -->
    <#-- ================================================================= -->
    <#if section = "form">

        <div class="login-card floating">
            <div class="v-card ">
                <div >
                    <div >
                        <h2 >
                            <#if messageHeader??>
                                ${kcSanitize(msg("${messageHeader}"))?no_esc}
                            <#else>
                                ${message.summary}
                            </#if>
                        </h2>
                    </div>
                    <div id="kc-info-message">
                        <#if requiredActions??><p><#list requiredActions><b><#items as reqActionItem>${kcSanitize(msg("requiredAction.${reqActionItem}"))?no_esc}<#sep>, </#items></b></#list></p></#if>
                        <#if skipLink??>
                        <#else>
                            <#if pageRedirectUri?has_content>
                                <p><a href="${pageRedirectUri}" class="v-btn">${kcSanitize(msg("backToApplication"))?no_esc}</a></p>
                            <#elseif actionUri?has_content>
                                <#if requiredActions?? && requiredActions?size == 1 && requiredActions?first == "UPDATE_PASSWORD">
                                    <script>window.location.href = "${actionUri}";</script>
                                <#else>
                                    <p><a href="${actionUri}" class="v-btn">${kcSanitize(msg("proceedWithAction"))?no_esc}</a></p>
                                </#if>
                            <#elseif (client.baseUrl)?has_content>
                                <p><a href="${client.baseUrl}" class="v-btn">${kcSanitize(msg("backToApplication"))?no_esc}</a></p>
                            </#if>
                        </#if>
                    </div>
                </div>
            </div>
        </div>

    </#if>
</@layout.registrationLayout>