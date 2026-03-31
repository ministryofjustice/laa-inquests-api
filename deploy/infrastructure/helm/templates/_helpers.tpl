{{/*
Expand the name of the chart.
*/}}
{{- define "laa-inquests-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "laa-inquests-api.fullname" -}}
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

{{- define "laa-inquests-api.whitelist" -}}
{{ join "," .Values.sharedIPRangesLAA}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "laa-inquests-api.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "laa-inquests-api.labels" -}}
helm.sh/chart: {{ include "laa-inquests-api.chart" . }}
{{ include "laa-inquests-api.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "laa-inquests-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "laa-inquests-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "laa-inquests-api.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "laa-inquests-api.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "laa-inquests-api.app.vars" -}}
- name: ENVIRONMENT
  value: {{.Values.environment}}
{{ range $name, $data := .Values.envVars }}
- name: {{ $name }}
{{- if $data.value }}
  value: "{{ $data.value }}"
{{- else if $data.secret }}
  valueFrom:
    secretKeyRef:
      name: {{ $data.secret.name }}
      key: {{ $data.secret.key }}
      optional: {{ $data.secret.optional | default false }}
{{- else if $data.configmap }}
  valueFrom:
    configMapKeyRef:
      name: {{ $data.configmap.name }}
      key: {{ $data.configmap.key }}
      optional: {{ $data.configmap.optional | default false }}
{{- end -}}
{{- end -}}
{{- end -}}