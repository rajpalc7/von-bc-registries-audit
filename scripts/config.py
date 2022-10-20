#!/usr/bin/python
import os 
import psycopg2
import traceback
import logging

from rocketchat_hooks import log_error, log_warning, log_info


LOGGER = logging.getLogger(__name__)

BCREG_SYSTEM_TYPE = "BC_REG"
LEAR_SYSTEM_TYPE = "BCREG_LEAR"

CORP_TYPES_IN_SCOPE = {
    "A":   "EXTRA PRO",
    "B":   "EXTRA PRO",
    "BC":  "BC COMPANY",
    "BEN": "BENEFIT COMPANY",
    "C":   "CONTINUE IN",
    "CC":  "BC CCC",
    "CP":  "COOP",
    "CS":  "CONT IN SOCIETY",
    "CUL": "ULC CONTINUE IN",
    "EPR": "EXTRA PRO REG",
    "FOR": "FOREIGN",
    "GP":  "PARTNERSHIP",
    #"FI":  "FINANCIAL", 
    "LIC": "LICENSED",
    "LL":  "LL PARTNERSHIP",
    "LLC": "LIMITED CO",
    "LP":  "LIM PARTNERSHIP",
    "MF":  "MISC FIRM",
    "PA":  "PRIVATE ACT",
    #"PAR": "PARISHES",
    "QA":  "CO 1860",
    "QB":  "CO 1862",
    "QC":  "CO 1878",
    "QD":  "CO 1890",
    "QE":  "CO 1897",
    "REG": "REGISTRATION",
    "S":   "SOCIETY",
    "SP":  "SOLE PROP",
    "ULC": "BC ULC COMPANY",
    "XCP": "XPRO COOP",
    "XL":  "XPRO LL PARTNR",
    "XP":  "XPRO LIM PARTNR",
    "XS":  "XPRO SOCIETY",
}

LEAR_CORP_TYPES_IN_SCOPE = {
    "GP":  "PARTNERSHIP",
    "SP":  "SOLE PROP",
}

def config(db_name):
    db = {}
    if db_name == 'bc_registries':
        db['host'] = os.environ.get('BC_REG_DB_HOST', 'localhost')
        db['port'] = os.environ.get('BC_REG_DB_PORT', '5454')
        db['database'] = os.environ.get('BC_REG_DB_DATABASE', 'BC_REGISTRIES')
        db['user'] = os.environ.get('BC_REG_DB_USER', '')
        db['password'] = os.environ.get('BC_REG_DB_PASSWORD', '')
    elif db_name == 'bc_reg_lear':
        db['host'] = os.environ.get('LEAR_DB_HOST', 'localhost')
        db['port'] = os.environ.get('LEAR_DB_PORT', '5454')
        db['database'] = os.environ.get('LEAR_DB_DATABASE', 'lear')
        db['user'] = os.environ.get('LEAR_DB_USER', '')
        db['password'] = os.environ.get('LEAR_DB_PASSWORD', '')
    elif db_name == 'event_processor':
        db['host'] = os.environ.get('EVENT_PROC_DB_HOST', 'localhost')
        db['port'] = os.environ.get('EVENT_PROC_DB_PORT', '5444')
        db['database'] = os.environ.get('EVENT_PROC_DB_DATABASE', 'bc_reg_db')
        db['user'] = os.environ.get('EVENT_PROC_DB_USER', 'bc_reg_db')
        db['password'] = os.environ.get('EVENT_PROC_DB_PASSWORD', 'bc_reg_db_pwd')
    elif db_name == 'org_book':
        db['host'] = os.environ.get('ORGBOOK_DB_HOST', 'localhost')
        db['port'] = os.environ.get('ORGBOOK_DB_PORT', '5432')
        db['database'] = os.environ.get('ORGBOOK_DB_DATABASE', 'THE_ORG_BOOK')
        db['user'] = os.environ.get('ORGBOOK_DB_USER', 'DB_USER')
        db['password'] = os.environ.get('ORGBOOK_DB_PASSWORD', 'DB_PASSWORD')
    else:
        raise Exception('Section {0} not a valid database'.format(db_name))
 
    return db


# pre-connected databases
db_conns = {}

# get (shared) connection to database
def get_connection(db_name, readonly: bool = True):
    db_cache_name = db_name + "::" + str(readonly)
    if db_cache_name in db_conns and db_conns[db_cache_name]:
        return db_conns[db_cache_name]

    db_config = config(db_name)
    conn = psycopg2.connect(**db_config)
    conn.set_session(readonly=readonly)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
    db_conns[db_cache_name] = conn

    return conn


# get all records and return in an array of dicts
# returns a zero-length array if none found
# optionally takes a WHERE clause and ORDER BY clause (must be valid SQL)
def get_db_sql(db_name, sql, args=None):
    cursor = None
    try:
        conn = get_connection(db_name)
        cursor = conn.cursor()
        if args:
            cursor.execute(sql, args)
        else:
            cursor.execute(sql)
        desc = cursor.description
        column_names = [col[0] for col in desc]
        rows = [dict(zip(column_names, row))  
            for row in cursor]
        cursor.close()
        cursor = None
        return rows
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error(error)
        LOGGER.error(traceback.print_exc())
        log_error("Exception reading DB: " + str(error))
        raise 
    finally:
        if cursor is not None:
            cursor.close()
        cursor = None


# post an update
def post_db_sql(db_name, sql, args=None):
    cursor = None
    try:
        conn = get_connection(db_name, readonly=False)
        cursor = conn.cursor()
        if args:
            cursor.execute(sql, args)
        else:
            cursor.execute(sql)
        count = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        cursor = None
        return count
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error(error)
        LOGGER.error(traceback.print_exc())
        log_error("Exception writing DB: " + str(error))
        raise 
    finally:
        if cursor is not None:
            cursor.close()
        cursor = None


def get_sql_record_count(db_name, sql):
    cur = None
    try:
        conn = get_connection(db_name)
        cur = conn.cursor()
        cur.execute(sql)
        ct = cur.fetchone()[0]
        cur.close()
        cur = None
        return ct
    except (Exception, psycopg2.DatabaseError) as error:
        LOGGER.error(error)
        LOGGER.error(traceback.print_exc())
        raise
    finally:
        if cur is not None:
            cur.close()
        cur = None


def starts_with_bc(corp_num):
    if corp_num.startswith('BC'):
        return corp_num
    return 'BC' + corp_num


# corp num with prefix
def corp_num_with_prefix(corp_typ_cd, corp_num):
    p_corp_num = corp_num
    if corp_typ_cd == 'BC':
        p_corp_num = starts_with_bc(corp_num)
    elif corp_typ_cd == 'ULC':
        p_corp_num = starts_with_bc(corp_num)
    elif corp_typ_cd == 'CC':
        p_corp_num = starts_with_bc(corp_num)
    elif corp_typ_cd == 'BEN':
        p_corp_num = starts_with_bc(corp_num)
    return p_corp_num


# corp num without prefix
def bare_corp_num(corp_num):
    if corp_num.startswith("BC"):
        return corp_num[2:]
    else:
        return corp_num
