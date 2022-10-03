#!/usr/bin/python
import os 
import psycopg2
import datetime
import time
import json
import decimal
import csv

from config import get_connection, get_db_sql, get_sql_record_count, CORP_TYPES_IN_SCOPE, corp_num_with_prefix, bare_corp_num
from orgbook_data_load import get_bc_reg_corps


USE_LEAR = (os.environ.get('USE_LEAR', 'false').lower() == 'true')


# mainline
if __name__ == "__main__":
    """
    Detail audit report - first step.
    Reads all corps and corp types from the BC Reg database and writes to a csv file.
    """
    get_bc_reg_corps(USE_LEAR=USE_LEAR)
