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
   USE_CSV=false \
   python ./detail_audit_report.py
```

Note that the connection information and credentials must be provided for all target databases.  Defaults are provided in a local [config.py](https://github.com/ianco/von-bc-registries-audit/blob/master/scripts/config.py) configuration file - the provided defaults will work for a local installation of von-network, OrgBook and the BC Registries issuer.


Database connection information and credentials need to be provided.  The environment variables are included in the above config.py](https://github.com/ianco/von-bc-registries-audit/blob/master/scripts/config.py) configuration file.

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

This script reads and updates an extract of the OrgBook wallet credential id's (since it takes so long to extract these id's).  Each time the script runs it reads this file into an in-memory cache, and then reads each OrgBook credential.  For Credentials with a eallet id not in cache the wallet is queried using the aca-py API url and key, and if the wallet record exists the id is appended to the extract file.

Note that by default this script only compares *non-revoked* credentials (as these are the only credentials that can be verified through the OrgBook API).  To audit *all* credentials specify an additional environment variable:

```bash
AUDIT_ALL_CREDENTIALS=true ... python ./detail_audit_report_agent.py
```

## OrgBook Search Database / Wallet Audit - Script Output

This script prints out admin commands required to correct the data in OrgBook.  This can include deletimg the existing OrgBook data and re-queuing data data from the BC Reg issuer.  Commands will look like the following example:

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
