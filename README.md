[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Lifecycle:Stable](https://img.shields.io/badge/Lifecycle-Stable-97ca00)](https://github.com/bcgov/repomountie/blob/master/doc/lifecycle-badges.md)

# Audit scripts for Aries VCR/OrgBook and BC Registries Issuer

This repository provides scripts to audit the OrgBook search database and agent wallet against the source BC Registries data.

These scripts require access to:

- Source BC Registries COLIN database
- The BC Registries issuer database (to check for future-dated orgs)
- The OrgBook search database
- The OrgBook wallet database

Due to the processing time required to read the OrgBook wallet credentials, the wallet id's are cached in a local text file.  New wallet id's are appended each time the audit script runs.

These scripts all have the option to run against local csv exports of the databases, rather than reading the database in real-time.

## BC Registries / OrgBook Search Database Audit

Run the script as follows:

```bash
BC_REG_DB_USER=<user> \
   BC_REG_DB_PASSWORD=<password> \
   EVENT_PROC_DB_USER=<user> \
   EVENT_PROC_DB_PASSWORD=<password> \
   ... etc ... \
   USE_CSV=false \
   python ./detail_audit_report.py
```

Note that the connection information and credentials must be provided for all target databases.  Defaults are provided in a local [config.py](https://github.com/bcgov/von-bc-registries-audit/blob/master/scripts/config.py) configuration file - the provided defaults will work for a local installation of von-network, OrgBook and the BC Registries issuer.


Database connection information and credentials need to be provided.  The environment variables are included in the above [config.py](https://github.com/bcgov/von-bc-registries-audit/blob/master/scripts/config.py) configuration file.

## OrgBook Search Database / Wallet Audit

Run the script as follows:

```bash
ORGBOOK_DB_PORT=<port> \
   ORGBOOK_DB_USER=<user> \
   ORGBOOK_DB_PASSWORD=<password> \
   ORGBOOK_DB_DATABASE=OrgBook \
   AGENT_API_URL=<acapy admin url>/credential/ \
   AGENT_API_KEY="acapy api key" \
   python ./detail_audit_report_agent.py
```

This script reads and updates an extract of the OrgBook wallet credential id's (since it takes so long to extract these id's).  Each time the script runs it reads this file into an in-memory cache, and then reads each OrgBook credential.  For Credentials with a wallet id not in cache the wallet is queried using the aca-py API url and key, and if the wallet record exists the id is appended to the extract file.

Note that by default this script only compares *non-revoked* credentials (as these are the only credentials that can be verified through the OrgBook API).  To audit *all* credentials specify an additional environment variable:

```bash
AUDIT_ALL_CREDENTIALS=true ... python ./detail_audit_report_agent.py
```

## OrgBook Search Database / Wallet Audit - Script Output

This script prints out admin commands required to correct the data in OrgBook.  This can include deleting the existing OrgBook data and re-queuing data data from the BC Reg issuer.  Commands will look like the following example:

```
./manage -e prod queueOrganization CP0009876
./manage -e prod queueOrganization 3456543
./manage -e prod queueOrganization 3456789
./manage -p bc -e prod deleteTopic BC1234567
./manage -e prod requeueOrganization 1234567
./manage -p bc -e prod deleteTopic BC1234589
./manage -e prod requeueOrganization 1234589
```

The first 3 lines represent companies missing in OrgBook, and must be queued from BC Reg.

The last 4 lines represent 2 companies in OrgBook that are incorrect and must be deleted and re-processed.

These commands are run using `orgbook-configurations` or `von-bc-registries-agent-configurations` scripts.

## Running the audit in steps, using exported csv files.

The audit process can be run in steps, where the initial steps extract data from each database, and then the final step reads data from the extracted csv files.  (For example, if you are running locally, want to audit the production databases, and can only port-map one database at a time.)

The steps are:

Port-map the BC Reg COLIN database:

```bash
BC_REG_DB_USER=<user> \
   BC_REG_DB_PASSWORD=<password> \
   python ./detail_audit_report_0.py
```

Port-map the BC Reg issuer database:

```bash
EVENT_PROC_DB_PASSWORD=<password> \
   EVENT_PROC_DB_USER=<user> \
   EVENT_PROC_DB_PASSWORD=<password> \
   EVENT_PROC_DB_PORT=<port> \
   python ./detail_audit_report_1.py
```

Port-map the OrgBook search database:

```bash
ORGBOOK_DB_PORT=<port> \
   ORGBOOK_DB_USER=<user> \
   ORGBOOK_DB_PASSWORD=<password> \
   ORGBOOK_DB_DATABASE=OrgBook \
   python ./detail_audit_report_2.py
```

... and then the final audit step (using all the locally cached csv files) is:

```bash
USE_CSV=true \
   python ./detail_audit_report.py
```

No database information needs to be provided on the last step.

## Running on Docker

The [./manage](./manage) script can be used to build and start a container for running the scripts.  The container was designed for use in OpenShift and by default starts the scripts using a cron tab [audit.conf](./docker/audit.conf).  Once the container is running you can shell into the container and run the scripts manually.  When running in docker add all of your environment variables to the `./env/.env` file.  This file will be created for you the first time you start the container.

When running locally the various databases will have to be port forwarded to your machine.  In order for the container to be able to connect with the databases you will need to specify the host names as `host.docker.internal` and forward the databases to separate ports.

Example:

From the command line (after updating your .env file):
```
./manage build
./manage start
./manage shell audit
```

From the shell inside the container:
```
(app-root) bash-4.4$ cd scripts/
(app-root) bash-4.4$ python ./detail_audit_report.py 
Get corp stats from OrgBook DB 2021-11-22 08:29:49.528329
Get corp stats from BC Registries DB 2021-11-22 08:29:52.320647
...
```

Type `exit` when complete, and then `./manage stop` to stop the container.

## Running in OpenShift

The audit container was designed to be run in OpenShift.  Once configured it runs the scripts on a schedule and posts the results to the `von-notifications` channel in the BCGov rocket.chat instance.

The [openshift-developer-tools](https://github.com/BCDevOps/openshift-developer-tools/tree/master/bin) compatible OpenShift configurations are contained in the [openshift](./openshift) folder.

The [openshift](./openshift) folder also contains a [./manage](./openshift/manage) script that can be used to build and deploy container images from your local source code.

Example (run from the `openshift` folder) - Build and deploy the `dev` and `test`:
```
./manage -e tools buildAndTag dev
./manage -e tools -e tools tag dev test
```