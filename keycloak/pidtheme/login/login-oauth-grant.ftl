<#import "template.ftl" as layout>

<@layout.registrationLayout bodyClass="oauth"; section>

    <#-- ================================================================= -->
    <#-- SECTION: FORM — Pantalla de consentimiento OAuth2               -->
    <#-- ================================================================= -->
    <#if section = "form">

        <div class="login-card floating">
            <div class="v-card">
                <div>

                    <#-- Logotipo del cliente si está definido -->
                    <#if client.attributes.logoUri??>
                        <div style="text-align: center; margin-bottom: 16px;">
                            <img src="${client.attributes.logoUri}" alt="${client.name!client.clientId}" style="max-height: 64px;">
                        </div>
                    </#if>

                    <div>
                        <h2>
                            <#if client.name?has_content>
                                ${msg("oauthGrantTitle", advancedMsg(client.name))}
                            <#else>
                                ${msg("oauthGrantTitle", client.clientId)}
                            </#if>
                        </h2>
                        <p>${msg("oauthGrantRequest")}</p>
                    </div>

                    <#-- Lista de scopes solicitados -->
                    <#if oauth.clientScopesRequested??>
                        <ul style="list-style: none; padding: 0; margin: 16px 0;">
                            <#list oauth.clientScopesRequested as clientScope>
                                <li style="display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #eee;">
                                    <span style="color: var(--kc-bg-color-start); font-size: 1.1em;">&#10003;</span>
                                    <span>
                                        <#if !clientScope.dynamicScopeParameter??>
                                            ${advancedMsg(clientScope.consentScreenText)}
                                        <#else>
                                            ${advancedMsg(clientScope.consentScreenText)}: <strong>${clientScope.dynamicScopeParameter}</strong>
                                        </#if>
                                    </span>
                                </li>
                            </#list>
                        </ul>
                    </#if>

                    <#-- ToS y política de privacidad -->
                    <#if client.attributes.policyUri?? || client.attributes.tosUri??>
                        <p style="font-size: 0.85em; color: #666; margin-bottom: 16px;">
                            <#if client.name?has_content>
                                ${msg("oauthGrantInformation", advancedMsg(client.name))}
                            <#else>
                                ${msg("oauthGrantInformation", client.clientId)}
                            </#if>
                            <#if client.attributes.tosUri??>
                                ${msg("oauthGrantReview")}
                                <a href="${client.attributes.tosUri}" target="_blank">${msg("oauthGrantTos")}</a>
                            </#if>
                            <#if client.attributes.policyUri??>
                                ${msg("oauthGrantReview")}
                                <a href="${client.attributes.policyUri}" target="_blank">${msg("oauthGrantPolicy")}</a>
                            </#if>
                        </p>
                    </#if>

                    <form action="${url.oauthAction}" method="POST">
                        <input type="hidden" name="code" value="${oauth.code}">
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
