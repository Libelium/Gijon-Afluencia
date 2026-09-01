{{/*
Chart name
*/}}
{{- define "apisix.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "apisix.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "apisix.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Fail fast when required credentials are missing. Keeps secrets out of the chart
defaults: the deployer must supply them (scripts/generate-env.sh, --set, vault).
*/}}
{{- define "apisix.validateCredentials" -}}
{{- if .Values.apisix.enabled }}
{{- if not .Values.apisix.apisix.admin.credentials.admin }}
{{- fail "ERROR: apisix.apisix.admin.credentials.admin (APISIX admin API key) is required. Use scripts/generate-env.sh or --set apisix.apisix.admin.credentials.admin=<value>." }}
{{- end }}
{{- end }}
{{- if not .Values.keycloak.useExternalSecret }}
{{- if not .Values.keycloak.clientSecret }}
{{- fail "ERROR: keycloak.clientSecret is required (or set keycloak.useExternalSecret=true). Supply it at deploy time — never commit it." }}
{{- end }}
{{- end }}
{{- if not .Values.fiware.backend.gatewaySecret }}
{{- fail "ERROR: fiware.backend.gatewaySecret is required. It is the shared secret the gateway sends to web-back on /api/internal/* (the SAME value as web-back's API_GATEWAY_SECRET). web-back fails closed without it, so a gateway installed without it would reject every FIWARE write. Use scripts/generate-env.sh or --set fiware.backend.gatewaySecret=<value>." }}
{{- end }}
{{- end }}
