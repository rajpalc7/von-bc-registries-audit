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
from orgbook_data_load import get_event_proc_future_corps, get_event_proc_audit_corps


# mainline
if __name__ == "__main__":
    """
    Detail audit report - second step.
    Reads from the event processor database and writes to a csv file:
    - corps queued for future processing (we don't check if these are in orgbook or not)
    - all corps in the event processor audit log
    """
    get_event_proc_future_corps()
    get_event_proc_audit_corps()
