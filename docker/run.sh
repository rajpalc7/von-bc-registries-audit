#!/bin/bash

AUDIT_CONF=${AUDIT_CONF:-./audit.conf}

function echoBlue (){
  _msg="${@}"
  _blue='\e[34m'
  _nc='\e[0m' # No Color
  echo -e "${_blue}${_msg}${_nc}"
}

function logInfo(){
  (
    infoMsg="${1}"
    echo -e "${infoMsg}"
    postMsgToWebhook "${ENVIRONMENT_FRIENDLY_NAME}" \
                     "${ENVIRONMENT_NAME}" \
                     "INFO" \
                     "${infoMsg}"
  )
}

function logWarn(){
  (
    warnMsg="${1}"
    echoYellow "${warnMsg}"
    postMsgToWebhook "${ENVIRONMENT_FRIENDLY_NAME}" \
                     "${ENVIRONMENT_NAME}" \
                     "WARN" \
                     "${warnMsg}"
  )
}

function logError(){
  (
    errorMsg="${1}"
    echoRed "[!!ERROR!!] - ${errorMsg}" >&2
    postMsgToWebhook "${ENVIRONMENT_FRIENDLY_NAME}" \
                     "${ENVIRONMENT_NAME}" \
                     "ERROR" \
                     "${errorMsg}"
  )
}

function postMsgToWebhook(){
  (
    if [ -z "${WEBHOOK_URL}" ] && [ -f ${WEBHOOK_TEMPLATE} ]; then
      return 0
    fi

    projectFriendlyName=${1}
    projectName=${2}
    statusCode=${3}
    message=$(formatWebhookMsg "${4}")
    curl -s -X POST -H 'Content-Type: application/json' --data "$(getWebhookPayload)" "${WEBHOOK_URL}" > /dev/null
  )
}

function shutDown(){
  jobIds=$(jobs | awk -F '[][]' '{print $2}' )
  for jobId in ${jobIds} ; do
    echo "Shutting down background job '${jobId}' ..."
    kill %${jobId}
  done

  if [ ! -z "${jobIds}" ]; then
    echo "Waiting for any background jobs to complete ..."
  fi
  wait

  exit 0
}

function startCron(){
  logInfo "Starting audit server in cron mode ..."
  echoBlue "Starting go-crond as a background task ...\n"
  CRON_CMD="go-crond -v --default-user=${UID} --working-directory=$(pwd) --allow-unprivileged ${AUDIT_CONF}"
  exec ${CRON_CMD} &
  wait
}

trap shutDown EXIT TERM

startCron