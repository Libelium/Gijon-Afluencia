{{/*
Chart name
*/}}
{{- define "mongodb.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mongodb.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "mongodb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels (Service → Pod)
*/}}
{{- define "mongodb.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mongodb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Fail fast if the password is empty.
*/}}
{{- define "mongodb.validateCredentials" -}}
{{- if not .Values.credentials.password }}
{{- fail "ERROR: credentials.password is required. Use --set credentials.password=<value> (or scripts/generate-env.sh)." }}
{{- end }}
{{- end }}
