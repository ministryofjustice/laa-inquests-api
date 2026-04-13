#!/bin/sh

environment=${1:-"uat"}

deployments=$(helm -n laa-inquests-api-${environment} list | grep -v "NAME" | grep -v "^laa-inquests-api\>" | cut -f 1)

if [[ "$deployments" == "" ]]; then
    echo "No ephemeral environments found in the ${environment} namespace"
    exit 0
fi

echo "Current ephemeral environments in ${environment}:\n"

deployment_array=($deployments)

n=1
for deploy in $deployments; do
  echo "${n}) $deploy"
  n=$((n+1))
done

echo
read -r -p "Select a number: " selected_number

if [[ ! "$selected_number" =~ ^[0-9]+$ ]] || [ "$selected_number" -lt 1 ] || [ "$selected_number" -gt "${#deployment_array[@]}" ]; then
    echo "\n${selected_number} is not a number between 1 and ${#deployment_array[@]}"
    exit 1
fi

deployment=${deployment_array[$selected_number-1]}

echo
read -r -p "Are you sure you want to delete the deployment ${deployment} [y/N]? " confirmation

if [[ "$confirmation" == "y"  ]] || [[ "$confirmation" == "Y"  ]]
then
    helm -n laa-inquests-api-${environment} delete "${deployment}"
fi