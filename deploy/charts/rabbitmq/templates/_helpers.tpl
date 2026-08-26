{{/*
Chart name
*/}}
{{- define "rabbitmq.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "rabbitmq.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "rabbitmq.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Fail fast if credentials are empty.
*/}}
{{- define "rabbitmq.validateCredentials" -}}
{{- if not .Values.credentials.username }}
{{- fail "ERROR: credentials.username is required. Use --set credentials.username=<value> (or scripts/generate-env.sh)." }}
{{- end }}
{{- if not .Values.credentials.password }}
{{- fail "ERROR: credentials.password is required. Use --set credentials.password=<value> (or scripts/generate-env.sh)." }}
{{- end }}
{{- end }}
