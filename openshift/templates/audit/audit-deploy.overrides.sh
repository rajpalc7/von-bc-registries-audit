#! /bin/bash
_includeFile=$(type -p overrides.inc)
if [ ! -z ${_includeFile} ]; then
  . ${_includeFile}
else
  _red='\033[0;31m'; _yellow='\033[1;33m'; _nc='\033[0m'; echo -e \\n"${_red}overrides.inc could not be found on the path.${_nc}\n${_yellow}Please ensure the openshift-developer-tools are installed on and registered on your path.${_nc}\n${_yellow}https://github.com/BCDevOps/openshift-developer-tools${_nc}"; exit 1;
fi

# ========================================================================
# Special Deployment Parameters needed for the backup instance.
# ------------------------------------------------------------------------
# The generated config map is used to update the Backup configuration.
# ========================================================================
CONFIG_MAP_NAME=audit-conf
SOURCE_FILE=$( dirname "$0" )/../../../docker/audit.conf

OUTPUT_FORMAT=json
OUTPUT_FILE=${CONFIG_MAP_NAME}-configmap_DeploymentConfig.json

printStatusMsg "Generating ConfigMap; ${CONFIG_MAP_NAME} ..."
generateConfigMap "${CONFIG_MAP_NAME}" "${SOURCE_FILE}" "${OUTPUT_FORMAT}" "${OUTPUT_FILE}"


if createOperation; then
  readParameter "BC_REG_DB_HOST - Please provide the name of the database host:" BC_REG_DB_HOST "" "false"
  readParameter "BC_REG_DB_PORT - Please provide the port number for the database:" BC_REG_DB_PORT "" "false"
  readParameter "BC_REG_DB_DATABASE - Please provide the name of the database:" BC_REG_DB_DATABASE "" "false"
  readParameter "BC_REG_DB_USER - Please provide the database username:" BC_REG_DB_USER "" "false"
  readParameter "BC_REG_DB_PASSWORD - Please provide the password for the database:" BC_REG_DB_PASSWORD "" "false"

  readParameter "LEAR_DB_HOST - Please provide the name of the database host:" LEAR_DB_HOST "" "false"
  readParameter "LEAR_DB_PORT - Please provide the port number for the database:" LEAR_DB_PORT "" "false"
  readParameter "LEAR_DB_DATABASE - Please provide the name of the database:" LEAR_DB_DATABASE "" "false"
  readParameter "LEAR_DB_USER - Please provide the database username:" LEAR_DB_USER "" "false"
  readParameter "LEAR_DB_PASSWORD - Please provide the password for the database:" LEAR_DB_PASSWORD "" "false"

  readParameter "EVENT_PROC_DB_HOST - Please provide the name of the database host:" EVENT_PROC_DB_HOST "" "false"
  readParameter "EVENT_PROC_DB_PORT - Please provide the port number for the database:" EVENT_PROC_DB_PORT "" "false"
  readParameter "EVENT_PROC_DB_DATABASE - Please provide the name of the database:" EVENT_PROC_DB_DATABASE "" "false"
  readParameter "EVENT_PROC_DB_USER - Please provide the database username:" EVENT_PROC_DB_USER "" "false"
  readParameter "EVENT_PROC_DB_PASSWORD - Please provide the password for the database:" EVENT_PROC_DB_PASSWORD "" "false"

  readParameter "ORGBOOK_DB_HOST - Please provide the name of the database host:" ORGBOOK_DB_HOST "" "false"
  readParameter "ORGBOOK_DB_PORT - Please provide the port number for the database:" ORGBOOK_DB_PORT "" "false"
  readParameter "ORGBOOK_DB_DATABASE - Please provide the name of the database:" ORGBOOK_DB_DATABASE "" "false"
  readParameter "ORGBOOK_DB_USER - Please provide the database username:" ORGBOOK_DB_USER "" "false"
  readParameter "ORGBOOK_DB_PASSWORD - Please provide the password for the database:" ORGBOOK_DB_PASSWORD "" "false"

  # Get the webhook URL
  readParameter "WEBHOOK_URL - Please provide the webhook endpoint URL.  If left blank, the webhook integration feature will be disabled:" WEBHOOK_URL "" "false"

  # Get the settings for delivering email notifications to the business
  readParameter "FEEDBACK_TARGET_EMAIL - Please provide the target email address where notifications will be sent.  The default is a blank string." FEEDBACK_TARGET_EMAIL "" "false"
  readParameter "SMTP_SERVER_ADDRESS - Please provide the address of the outgoing smtp server.  The default is a blank string." SMTP_SERVER_ADDRESS "" "false"
else
  printStatusMsg "Update operation detected ...\nSkipping the prompts for the all the secrets ...\n"

  writeParameter "BC_REG_DB_HOST" "prompt_skipped" "false"
  writeParameter "BC_REG_DB_PORT" "prompt_skipped" "false"
  writeParameter "BC_REG_DB_DATABASE" "prompt_skipped" "false"
  writeParameter "BC_REG_DB_USER" "prompt_skipped" "false"
  writeParameter "BC_REG_DB_PASSWORD" "prompt_skipped" "false"

  writeParameter "LEAR_DB_HOST" "prompt_skipped" "false"
  writeParameter "LEAR_DB_PORT" "prompt_skipped" "false"
  writeParameter "LEAR_DB_DATABASE" "prompt_skipped" "false"
  writeParameter "LEAR_DB_USER" "prompt_skipped" "false"
  writeParameter "LEAR_DB_PASSWORD" "prompt_skipped" "false"

  writeParameter "EVENT_PROC_DB_HOST" "prompt_skipped" "false"
  writeParameter "EVENT_PROC_DB_PORT" "prompt_skipped" "false"
  writeParameter "EVENT_PROC_DB_DATABASE" "prompt_skipped" "false"
  writeParameter "EVENT_PROC_DB_USER" "prompt_skipped" "false"
  writeParameter "EVENT_PROC_DB_PASSWORD" "prompt_skipped" "false"

  writeParameter "ORGBOOK_DB_HOST" "prompt_skipped" "false"
  writeParameter "ORGBOOK_DB_PORT" "prompt_skipped" "false"
  writeParameter "ORGBOOK_DB_DATABASE" "prompt_skipped" "false"
  writeParameter "ORGBOOK_DB_USER" "prompt_skipped" "false"
  writeParameter "ORGBOOK_DB_PASSWORD" "prompt_skipped" "false"

  writeParameter "WEBHOOK_URL" "prompt_skipped" "false"
  writeParameter "FEEDBACK_TARGET_EMAIL" "prompt_skipped" "false"
  writeParameter "SMTP_SERVER_ADDRESS" "prompt_skipped" "false"
fi

SPECIALDEPLOYPARMS="--param-file=${_overrideParamFile}"
echo ${SPECIALDEPLOYPARMS}