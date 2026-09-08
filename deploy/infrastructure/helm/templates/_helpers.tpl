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
{{- range $name, $value := .Values.env }}
- name: {{ $name }}
  value: {{ $value | quote }}
{{- end -}}
{{- end -}}

{{/*
Secret-backed environment variables shared by the app container and cronjobs.
*/}}
{{- define "laa-inquests-api.app.secrets" -}}
- name: INQUESTS_API_CLIENT_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_INQUESTS_API_ENTRA_CONFIG }}
      key: INQUESTS_API_CLIENT_ID
- name: INQUESTS_API_TENANT_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_INQUESTS_API_ENTRA_CONFIG }}
      key: INQUESTS_API_TENANT_ID
- name: GOV_NOTIFY_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_API_KEY }}
      key: GOV_NOTIFY_API_KEY
- name: GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_TEMPLATE_IDS }}
      key: GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID
- name: GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_TEMPLATE_IDS }}
      key: GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID
- name: GOV_NOTIFY_APPLICATION_GRANT_TEMPLATE_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_TEMPLATE_IDS }}
      key: GOV_NOTIFY_APPLICATION_GRANT_TEMPLATE_ID
- name: GOV_NOTIFY_CLAIM_SUBMIT_TEMPLATE_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_TEMPLATE_IDS }}
      key: GOV_NOTIFY_CLAIM_SUBMIT_TEMPLATE_ID
- name: GOV_NOTIFY_CLAIM_REJECT_TEMPLATE_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_TEMPLATE_IDS }}
      key: GOV_NOTIFY_CLAIM_REJECT_TEMPLATE_ID
- name: GOV_NOTIFY_FINAL_BILL_CLAIM_REJECT_TEMPLATE_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_TEMPLATE_IDS }}
      key: GOV_NOTIFY_FINAL_BILL_CLAIM_REJECT_TEMPLATE_ID
- name: GOV_NOTIFY_POA_CLAIM_AUTO_APPROVE_TEMPLATE_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_TEMPLATE_IDS }}
      key: GOV_NOTIFY_POA_CLAIM_AUTO_APPROVE_TEMPLATE_ID
- name: GOV_NOTIFY_CALLBACK_BEARER_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_GOV_NOTIFY_CALLBACK_BEARER_TOKEN }}
      key: GOV_NOTIFY_CALLBACK_BEARER_TOKEN
- name: SDS_BASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_SDS_CONFIG }}
      key: SDS_BASE_URL
- name: SDS_TENANT_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_SDS_CONFIG }}
      key: SDS_TENANT_ID
- name: SDS_CLIENT_ID
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_SDS_CONFIG }}
      key: SDS_CLIENT_ID
- name: SDS_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_SDS_CONFIG }}
      key: SDS_CLIENT_SECRET
- name: SDS_SCOPE
  valueFrom:
    secretKeyRef:
      name: {{ .Values.env.AWS_SECRETS_SDS_CONFIG }}
      key: SDS_SCOPE
{{- end -}}