{{/*
Chart name
*/}}
{{- define "stackgres.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "stackgres.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "stackgres.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Fail fast if any required init-script password is empty.
*/}}
{{- define "stackgres.validatePasswords" -}}
{{- $required := list "realtime" "platformdb" "keycloak" }}
{{- range $required }}
{{- if not (index $.Values.initScripts.passwords .) }}
{{- fail (printf "ERROR: initScripts.passwords.%s is required. Use --set initScripts.passwords.%s=<value> (or scripts/generate-env.sh)." . .) }}
{{- end }}
{{- end }}
{{- end }}
