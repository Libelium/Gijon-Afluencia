<#import "template.ftl" as layout>

<@layout.registrationLayout; section>

    <#-- ================================================================= -->
    <#-- SECTION: FORM (The "Page Expired" Card Content)                 -->
    <#-- ================================================================= -->
    <#if section = "form">

        <div class="login-card floating">
            <div class="v-card ">
                <div >
                    <div >
                        <h2 >${msg("pageExpiredTitle")}</h2>
                    <p id="instruction1">
                        ${msg("pageExpiredMsg1")} <a id="loginRestartLink" href="${url.loginRestartFlowUrl}">${msg("doClickHere")}</a> .<br/>
                    </p>
                </div>
            </div>
        </div>

    </#if>
</@layout.registrationLayout>