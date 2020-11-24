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
from orgbook_data_load import get_orgbook_all_corps
from orgbook_data_audit import compare_bc_reg_orgbook


# mainline
if __name__ == "__main__":
    """
    Detail audit report - final step.
    Reads from the orgbook database and compares:
    """
    # read from orgbook database
    orgbook_corp_types = get_orgbook_all_corps()
