#!/usr/bin/python
import os 
import psycopg2
import datetime
import time
import json
import decimal
import requests
import csv
import asyncio

from config import get_connection, get_db_sql, get_sql_record_count, CORP_TYPES_IN_SCOPE, corp_num_with_prefix, bare_corp_num
from orgbook_data_load import (
    get_orgbook_all_corps, get_orgbook_all_corps_csv,
    get_event_proc_future_corps, get_event_proc_future_corps_csv,
    get_bc_reg_corps, get_bc_reg_corps_csv,
    get_agent_wallet_ids, append_agent_wallet_ids
)


QUERY_LIMIT = '200000'
REPORT_COUNT = 10000
ERROR_THRESHOLD_COUNT = 5

# value for PROD is "https://orgbook.gov.bc.ca/api/v3"
ORGBOOK_API_URL = os.environ.get('ORGBOOK_API_URL', 'http://localhost:8081/api/v3')
TOPIC_QUERY = "/topic/registration.registries.ca/"
TOPIC_NAME_SEARCH = "/search/topic?inactive=false&latest=true&revoked=false&name="
TOPIC_ID_SEARCH = "/search/topic?inactive=false&latest=true&revoked=false&topic_id="

# value for PROD is "https://agent-admin.orgbook.gov.bc.ca/credential/"
AGENT_API_URL = os.environ.get("AGENT_API_URL", "http://localhost:8021/credential/")
AGENT_API_KEY = os.environ.get("AGENT_API_KEY")

# default is to audit active (non-revoked) credentials
AUDIT_ALL_CREDENTIALS = (os.environ.get("AUDIT_ALL_CREDENTIALS", "false").lower() == 'true')


"""
Detail audit report - credential list from orgbook.
Reads from the orgbook database:
- wallet id for each credential
"""

async def process_credential_queue():
    # preload agent wallet id's
    print("Get exported wallet id's from agent", datetime.datetime.now())
    agent_wallet_ids = get_agent_wallet_ids()
    print("# wallet id's:", len(agent_wallet_ids))

    conn = None
    try:
        conn = get_connection('org_book')
    except (Exception) as error:
        print(error)
        raise

    # get all the corps from orgbook
    print("Get credential stats from OrgBook DB", datetime.datetime.now())
    cred_filter = " and not credential.revoked " if not AUDIT_ALL_CREDENTIALS else ""
    sql4 = """select 
                  credential.credential_id, credential.id, credential.topic_id, credential.update_timestamp,
                  topic.source_id, credential.credential_type_id, credential_type.description,
                  credential.revoked, credential.inactive, credential.latest,
                  credential.effective_date, credential.revoked_date, credential.revoked_by_id
                from credential, topic, credential_type
                where topic.id = credential.topic_id""" + cred_filter + """
                and credential_type.id = credential.credential_type_id
                order by id;"""
    corp_creds = []
    try:
        cur = conn.cursor()
        cur.execute(sql4)
        for row in cur:
            corp_creds.append({
                'credential_id': row[0], 'id': row[1], 'topic_id': row[2], 'timestamp': row[3],
                'source_id': row[4], 'credential_type_id': row[5], 'credential_type': row[6],
                'revoked': row[7], 'inactive': row[8], 'latest': row[9],
                'effective_date': row[10], 'revoked_date': row[11], 'revoked_by': row[12]
            })
        cur.close()
    except (Exception) as error:
        print(error)
        raise
    print("# orgbook creds:", len(corp_creds), datetime.datetime.now())

    i = 0
    agent_checks = 0
    cache_checks = 0
    missing = []
    extra_cred = []
    not_in_cache = []
    print("Checking for valid credentials ...", datetime.datetime.now())
    while i < len(corp_creds):
        # if cached we are good, otherwise check agent via api
        if not corp_creds[i]['credential_id'] in agent_wallet_ids.keys():
            agent_checks = agent_checks + 1
            api_key_hdr = {"x-api-key": AGENT_API_KEY}
            url = AGENT_API_URL + corp_creds[i]['credential_id']
            #print(i, url)
            try:
                response = requests.get(url, headers=api_key_hdr)
                response.raise_for_status()
                if response.status_code == 404:
                    raise Exception("404 not found")
                else:
                    wallet_credential = response.json()
                    # exists in agent but is not in cache
                    not_in_cache.append(corp_creds[i])
            except Exception as e:
                if (corp_creds[i]['revoked'] and corp_creds[i]['revoked_by'] is not None and
                    corp_creds[i]['effective_date'] == corp_creds[i]['revoked_date']):
                    print("Extra cred in TOB:", i, corp_creds[i]['credential_id'])
                    extra_cred.append(corp_creds[i])
                else:
                    print(
                        "Exception:", i, corp_creds[i]['credential_id'],
                        corp_creds[i]['topic_id'], corp_creds[i]['source_id'], corp_creds[i]['credential_type'],
                        corp_creds[i]['revoked'], corp_creds[i]['inactive'], corp_creds[i]['latest'],
                        corp_creds[i]['timestamp'],
                        )
                    missing.append(corp_creds[i])
        else:
            cache_checks = cache_checks + 1
        i = i + 1
        if 0 == i % 100000:
            print(i)

    append_agent_wallet_ids(not_in_cache)

    print("Total # missing in wallet:", len(missing), ", Extra:", len(extra_cred), datetime.datetime.now())
    print("Cache checks:", cache_checks, ", Agent checks:", agent_checks)


try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_credential_queue())
except Exception as e:
    print("Exception", e)
    raise

