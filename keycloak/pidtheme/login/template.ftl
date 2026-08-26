<#assign brandPrimary = (properties.brandPrimary!'')?starts_with('#')?then(properties.brandPrimary, '#7D00F4')>
<#assign brandSecondary = (properties.brandSecondary!'')?starts_with('#')?then(properties.brandSecondary, '#5800C0')>
<#assign brandIndigo = (properties.brandIndigo!'')?starts_with('#')?then(properties.brandIndigo, '#150D5F')>

<#-- Image the parallax moves, from KC_BRAND_LOGIN_IMAGE: URL, absolute path or file name in img/.
     Order: organization (dynamicLogo.js) > KC_BRAND_LOGIN_IMAGE > the bundled logo. -->
<#assign brandLoginImageRaw = (properties.brandLoginImage!'')?trim>
<#-- Unsubstituted placeholder (no bootstrap) counts as unset. -->
<#if brandLoginImageRaw?starts_with('__')><#assign brandLoginImageRaw = ''></#if>
<#if !brandLoginImageRaw?has_content>
    <#assign brandLoginImageUrl = url.resourcesPath + '/img/logo.png'>
<#elseif brandLoginImageRaw?starts_with('http') || brandLoginImageRaw?starts_with('/')>
    <#assign brandLoginImageUrl = brandLoginImageRaw>
<#else>
    <#assign brandLoginImageUrl = url.resourcesPath + '/img/' + brandLoginImageRaw>
</#if>

<#-- Shared with the OTP view. -->
<#macro parallax>
    <div class="kc-parallax-wrap" id="kc-parallax-wrap">
        <div class="kc-parallax-layer kc-bg-layer" data-depth="1"></div>

        <div class="kc-parallax-layer logo-layer" data-depth="2">
            <div class="login-logo" id="main-logo">
                <div>
                    <img src="${brandLoginImageUrl}" class="centered-image" alt="Logo">
                </div>
            </div>
        </div>
    </div>
</#macro>

<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html class="${properties.kcHtmlClass!}" data-kc-default-locale="${properties.defaultLocale!}"<#if realm.internationalizationEnabled> lang="${locale.currentLanguageTag}" data-kc-current-locale="${locale.currentLanguageTag}"</#if>>

<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="robots" content="noindex, nofollow">

    <#if properties.meta?has_content>
        <#list properties.meta?split(' ') as meta>
            <meta name="${meta?split('==')[0]}" content="${meta?split('==')[1]}"/>
        </#list>
    </#if>

        <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;900&display=swap" rel="stylesheet">
        <#if properties.stylesCommon?has_content>
        <#list properties.stylesCommon?split(' ') as style>
            <link href="${url.resourcesCommonPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <style id="kc-brand">
      :root {
        --kc-primary: ${brandPrimary};
        --kc-bg-color-mid: ${brandSecondary};
        --kc-bg-color-start: ${brandIndigo};
      }
    </style>
    <script>
      window.BACKEND_URL = "${properties['backendUrl']}";
    </script>
    <#if properties.scripts?has_content>
        <#list properties.scripts?split(' ') as script>
            <script src="${url.resourcesPath}/${script}" type="text/javascript"></script>
        </#list>
    </#if>
    <script type="importmap">
        {
            "imports": {
                "rfc4648": "${url.resourcesCommonPath}/node_modules/rfc4648/lib/rfc4648.js"
            }
        }
    </script>
    <script src="${url.resourcesPath}/js/menu-button-links.js" type="module"></script>
    <#if scripts??>
        <#list scripts as script>
            <script src="${script}" type="text/javascript"></script>
        </#list>
    </#if>
    <script type="module">
        import { checkCookiesAndSetTimer } from "${url.resourcesPath}/js/authChecker.js";

        checkCookiesAndSetTimer(
          "${url.ssoLoginInOtherTabsUrl?no_esc}"
        );
    </script>
</head>

<body class="${properties.kcBodyClass!}">
<div class="${properties.kcLoginClass!}">
    
    <@parallax/>

    <div class="${properties.kcFormCardClass!}">
        <header class="${properties.kcFormHeaderClass!}">
            <#-- Selector de idioma (mantener si lo quieres en la tarjeta) -->
            <#if realm.internationalizationEnabled  && locale.supported?size gt 1>
                <div class="${properties.kcLocaleMainClass!}" id="kc-locale">
                    <div id="kc-locale-wrapper" class="${properties.kcLocaleWrapperClass!}">
                        <div id="kc-locale-dropdown" class="menu-button-links ${properties.kcLocaleDropDownClass!}">
                            <button tabindex="1" id="kc-current-locale-link" aria-label="${msg("languages")}" aria-haspopup="true" aria-expanded="false" aria-controls="language-switch1">${locale.current}</button>
                            <ul role="menu" tabindex="-1" aria-labelledby="kc-current-locale-link" aria-activedescendant="" id="language-switch1" class="${properties.kcLocaleListClass!}">
                                <#assign i = 1>
                                <#list locale.supported as l>
                                    <li class="${properties.kcLocaleListItemClass!}" role="none">
                                        <a role="menuitem" id="language-${i}" class="${properties.kcLocaleItemClass!}" href="${l.url}" data-kc-locale-option="${l.languageTag}">${l.label}</a>
                                    </li>
                                    <#assign i++>
                                </#list>
                            </ul>
                        </div>
                    </div>
                </div>
            </#if>
            <h1 id="kc-page-title"><#nested "header"></h1>
        </header>
      <div id="kc-content">
        <div id="kc-content-wrapper">

          <#-- App-initiated actions should not see warning messages about the need to complete the action -->
          <#-- during login.                                                                               -->
          <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
              <div class="alert-${message.type} ${properties.kcAlertClass!} pf-m-<#if message.type = 'error'>danger<#else>${message.type}</#if>">
                  <div class="pf-c-alert__icon">
                      <#if message.type = 'success'><span class="${properties.kcFeedbackSuccessIcon!}"></span></#if>
                      <#if message.type = 'warning'><span class="${properties.kcFeedbackWarningIcon!}"></span></#if>
                      <#if message.type = 'error'><span class="${properties.kcFeedbackErrorIcon!}"></span></#if>
                      <#if message.type = 'info'><span class="${properties.kcFeedbackInfoIcon!}"></span></#if>
                  </div>
                      <span class="${properties.kcAlertTitleClass!}">${kcSanitize(message.summary)?no_esc}</span>
              </div>
          </#if>

          <#nested "form">

          <#if auth?has_content && auth.showTryAnotherWayLink()>
              <form id="kc-select-try-another-way-form" action="${url.loginAction}" method="post">
                  <div class="${properties.kcFormGroupClass!}">
                      <input type="hidden" name="tryAnotherWay" value="on"/>
                      <a href="#" id="try-another-way"
                         onclick="document.forms['kc-select-try-another-way-form'].submit();return false;">${msg("doTryAnotherWay")}</a>
                  </div>
              </form>
          </#if>

          <#nested "socialProviders">

          <#if displayInfo>
              <div id="kc-info" class="${properties.kcSignUpClass!}">
                  <div id="kc-info-wrapper" class="${properties.kcInfoAreaWrapperClass!}">
                      <#nested "info">
                  </div>
              </div>
          </#if>
        </div>
      </div>

    </div>
  </div>
</body>

</html>
</#macro>