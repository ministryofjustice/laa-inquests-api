#!/bin/bash

ENVIRONMENT=$1

deploy_branch() {
# Convert the branch name into a string that can be turned into a valid URL
  BRANCH_RELEASE_NAME=$(echo "$branch_name" | tr '[:upper:]' '[:lower:]' | sed 's:^\w*\/::' | tr -s ' _/[]().' '-' | cut -c1-18 | sed 's/-$//')
# Set the deployment host, this will add the prefix of the branch name e.g el-257-deploy-with-circleci or just main
  RELEASE_HOST="$BRANCH_RELEASE_NAME-laa-inquests-api-$ENVIRONMENT.apps.live.cloud-platform.service.justice.gov.uk"
# Set the ingress name, needs release name, namespace and -green suffix
  IDENTIFIER="$BRANCH_RELEASE_NAME-laa-inquests-api-$K8S_NAMESPACE-green"
  echo "Github ref: $branch_name; release name: $BRANCH_RELEASE_NAME; identifier: $IDENTIFIER; release host: $RELEASE_HOST"
  echo "Deploying commit: $GITHUB_SHA under release name: '$BRANCH_RELEASE_NAME'..."

  helm upgrade "$BRANCH_RELEASE_NAME" ./deploy/infrastructure/helm/. \
                --install --wait --timeout 10m \
                --namespace="${K8S_NAMESPACE}" \
                --values ./deploy/infrastructure/helm/values/"$ENVIRONMENT".yaml \
                --set image.repository="$REGISTRY/$REPOSITORY" \
                --set image.tag="$IMAGE_TAG" \
                --set ingress.annotations."external-dns\.alpha\.kubernetes\.io/set-identifier"="$IDENTIFIER" \
                --set ingress.hosts[0].host="$RELEASE_HOST" \
                --set env.DB_HOST="$DB_HOST" \
                --set env.DB_NAME="$DB_NAME" \
                --set env.DB_PASSWORD="$DB_PASSWORD" \
                --set env.DB_PORT="$DB_PORT" \
                --set env.DB_USER="$DB_USER" \
                --set env.DEPARTMENT_NAME="$DEPARTMENT_NAME" \
                --set env.DEPARTMENT_URL="$DEPARTMENT_URL" \
                --set env.CONTACT_EMAIL="$CONTACT_EMAIL" \
                --set env.CONTACT_PHONE="$CONTACT_PHONE" \
                --set env.NODE_ENV="$NODE_ENV" \
                --set env.SERVICE_NAME="$SERVICE_NAME" \
                --set env.RATE_LIMIT_MAX="$RATE_LIMIT_MAX" \
                --set env.RATE_WINDOW_MS="$RATE_WINDOW_MS" \
                --set env.RATELIMIT_HEADERS_ENABLED="$RATELIMIT_HEADERS_ENABLED" \
                --set env.RATELIMIT_STORAGE_URI="$RATELIMIT_STORAGE_URI" \
                --set env.SERVICE_PHASE="$SERVICE_PHASE" \
                --set env.SESSION_NAME="$SESSION_NAME" \
                --set env.SESSION_SECRET="$SESSION_SECRET" \
                --set env.SERVICE_URL="$SERVICE_URL"
}

deploy_main() {
  RELEASE_HOST="laa-inquests-api-$ENVIRONMENT.apps.live.cloud-platform.service.justice.gov.uk"
  helm upgrade laa-inquests-api ./deploy/infrastructure/helm/. \
                --install --wait --timeout 10m \
                --namespace="${K8S_NAMESPACE}" \
                --values ./deploy/infrastructure/helm/values/"$ENVIRONMENT".yaml \
                --set image.repository="$REGISTRY/$REPOSITORY" \
                --set image.tag="$IMAGE_TAG" \
                --set env.DB_HOST="$DB_HOST" \
                --set env.DB_NAME="$DB_NAME" \
                --set env.DB_PASSWORD="$DB_PASSWORD" \
                --set env.DB_PORT="$DB_PORT" \
                --set env.DB_USER="$DB_USER" \
                --set env.DEPARTMENT_NAME="$DEPARTMENT_NAME" \
                --set env.DEPARTMENT_URL="$DEPARTMENT_URL" \
                --set env.CONTACT_EMAIL="$CONTACT_EMAIL" \
                --set env.CONTACT_PHONE="$CONTACT_PHONE" \
                --set env.NODE_ENV="$NODE_ENV" \
                --set env.SERVICE_NAME="$SERVICE_NAME" \
                --set env.RATE_LIMIT_MAX="$RATE_LIMIT_MAX" \
                --set env.RATE_WINDOW_MS="$RATE_WINDOW_MS" \
                --set env.RATELIMIT_HEADERS_ENABLED="$RATELIMIT_HEADERS_ENABLED" \
                --set env.RATELIMIT_STORAGE_URI="$RATELIMIT_STORAGE_URI" \
                --set env.SERVICE_PHASE="$SERVICE_PHASE" \
                --set env.SESSION_NAME="$SESSION_NAME" \
                --set env.SESSION_SECRET="$SESSION_SECRET" \
                --set env.SERVICE_URL="$SERVICE_URL"
}

releaseTag="^[0-9]+[.][0-9]+[.][0-9]+$"

branch_name="$GITHUB_HEAD_REF" # Branch name if this is a pull-request event
if [ -z "$branch_name" ]; then
  branch_name="$GITHUB_REF_NAME" # Branch name if this is a push event
fi

if [[ ("$ENVIRONMENT" == 'uat') && "$branch_name" == "main" ]] || \
   [[ (("$ENVIRONMENT" == 'staging' || "$ENVIRONMENT" == 'production') && "$branch_name" =~ $releaseTag) ]]
then
  deploy_main
else
  if deploy_branch; then
    echo "Deploy succeeded"
  else
    echo "Deploy failed. Attempting rollback"
    if helm rollback "$BRANCH_RELEASE_NAME"; then
      echo "Rollback succeeded. Retrying deploy"
      deploy_branch
    else
      echo "Rollback failed. Consider manually running 'helm delete $BRANCH_RELEASE_NAME'"
      exit 1
    fi
  fi
fi
