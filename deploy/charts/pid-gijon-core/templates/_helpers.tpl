{{/*
Expand the name of the chart.
*/}}
{{- define "pid-gijon-core.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
Truncated at 63 chars because some Kubernetes name fields are limited to this
(by the DNS naming spec). If the release name already contains the chart name it
is used as the full name.
*/}}
{{- define "pid-gijon-core.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "pid-gijon-core.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "pid-gijon-core.labels" -}}
helm.sh/chart: {{ include "pid-gijon-core.chart" . }}
{{ include "pid-gijon-core.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels (the subset that is stable across upgrades).
*/}}
{{- define "pid-gijon-core.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pid-gijon-core.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Convert a string from camelCase to kebab-case.

NOTE: a component's Kubernetes object names (Deployment, Service, ConfigMap, ...)
are derived purely from this kebab-cased component key, WITHOUT the release name.
This is intentional: components address each other over stable in-cluster DNS
names such as http://orion-ld:1026 and http://web-back, which are hard-coded in
their configuration. Do not prefix these names with the release name.
*/}}
{{- define "pid-gijon-core.kebabcase" -}}
{{- $result := . -}}
{{- $result := regexReplaceAll "([a-z0-9])([A-Z])" $result "${1}-${2}" -}}
{{- $result := lower $result -}}
{{- $result -}}
{{- end -}}

{{/*
Build the fully qualified image reference for a component.

Usage: {{ include "pid-gijon-core.imageRef" (list $component $) }}

If .Values.global.imageRegistry is set it is prepended to the component's
image.repository. Public images that already include a registry host (e.g.
quay.io/fiware/orion-ld) should leave global.imageRegistry empty, or set their
own image.registry override.
*/}}
{{- define "pid-gijon-core.imageRef" -}}
{{- $component := index . 0 -}}
{{- $context := index . 1 -}}
{{- $registry := $component.image.registry | default $context.Values.global.imageRegistry -}}
{{- $repository := required "every enabled component needs image.repository" $component.image.repository -}}
{{- $tag := $component.image.tag | default $context.Chart.AppVersion | default "latest" -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end -}}

{{/*
Build an image reference from a free-form image spec (used by initContainers).

Usage: {{ include "pid-gijon-core.rawImageRef" (list $spec $) }}
where $spec has .image (repository), optional .registry and .tag.
*/}}
{{- define "pid-gijon-core.rawImageRef" -}}
{{- $spec := index . 0 -}}
{{- $context := index . 1 -}}
{{- $registry := $spec.registry | default $context.Values.global.imageRegistry -}}
{{- $repository := required "initContainer needs an image" $spec.image -}}
{{- $tag := $spec.tag | default $context.Chart.AppVersion | default "latest" -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end -}}
