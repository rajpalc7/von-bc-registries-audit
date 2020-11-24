#!/usr/bin/python
import os 
import psycopg2
import datetime
import time
import json
import decimal
import requests
import csv

from config import get_connection, get_db_sql, get_sql_record_count, CORP_TYPES_IN_SCOPE, corp_num_with_prefix, bare_corp_num
from orgbook_data_load import get_orgbook_all_corps, get_orgbook_all_corps_csv, get_event_proc_future_corps, get_event_proc_future_corps_csv, get_bc_reg_corps, get_bc_reg_corps_csv
from orgbook_data_audit import compare_bc_reg_orgbook


USE_CSV = (os.environ.get('USE_CSV', 'false').lower() == 'true')


# mainline
if __name__ == "__main__":
    """
    Detail audit report - final step.
    Reads from the orgbook database and compares:
    - corps in BC Reg that are not in orgbook (or that are in orgbook with a different corp type)
    - corps in orgbook that are *not* in BC Reg database (maybe have been removed?)
    """

    # read from orgbook database
    if USE_CSV:
        orgbook_corp_types = get_orgbook_all_corps_csv()
    else:
        orgbook_corp_types = get_orgbook_all_corps()

    # corps that are still in the event processor queue waiting to be processed (won't be in orgbook yet)
    if USE_CSV:
        future_corps = get_event_proc_future_corps_csv()
    else:
        future_corps = get_event_proc_future_corps()

    # check if all the BC Reg corps are in orgbook (with the same corp type)
    if USE_CSV:
        bc_reg_corp_types = get_bc_reg_corps_csv()
    else:
        bc_reg_corp_types = get_bc_reg_corps()

    # do the orgbook/bc reg compare
    compare_bc_reg_orgbook(bc_reg_corp_types, orgbook_corp_types, future_corps)
