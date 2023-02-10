#!/usr/bin/python
import os 
import argparse
import psycopg2
import datetime
import time
import json
import decimal
import csv

from config import get_rw_connection, get_db_sql, get_sql_record_count, CORP_TYPES_IN_SCOPE, corp_num_with_prefix, bare_corp_num
from orgbook_data_load import get_bc_reg_corps


USE_LEAR = (os.environ.get('USE_LEAR', 'false').lower() == 'true')


# mainline
if __name__ == "__main__":
    """
    Delete presentation request records from the OrgBook wallet.
    """
    # user needs to supply a record id which is a "known" presentation request
    parser = argparse.ArgumentParser(
        description="Deletes presentation request items from the OrgBook wallet."
    )
    parser.add_argument(
        "--id",
        type=int,
        required=True,
        help="Record ID (in 'items' table) of a *known* presentation request.",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=1000,
        required=False,
        help="Number of items records per batch delete (default 1000).",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=100000,
        required=False,
        help="Maximum number of items records to delete (default 100000).",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        required=False,
        help="Don't delete, just return a record count.",
    )
    args = parser.parse_args()

    # connect to OrgBook wallet DB
    conn = None
    try:
        conn = get_rw_connection('orgbook_wallet')
    except (Exception) as error:
        print(error)
        raise

    # get the type (encrypted) describing a pres req
    sql_pres = """select type from items where id = %s"""
    # get a record count
    sql_count = """select count(*) from items where type = %s"""
    # get items records that are pres reqs
    sql_items = """select id from items where type = %s limit """ + str(args.batch)
    # delete tags associated with the pres req
    sql_del_etags = """delete from tags_encrypted where item_id in """
    sql_del_utags = """delete from tags_plaintext where item_id in """
    # delete the pres req item record
    sql_del_items = """delete from items where id in """

    pres_type = None
    pres_count = 0

    # get the type (encrypted) describing a pres req
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql_pres, (args.id,))
        row = cur.fetchone()
        if row is None:
            raise Exception("Error no record found for supplied record id")
        pres_type = row[0]
        cur.close()
        cur = None
    except (Exception, psycopg2.DatabaseError) as error:
        print("EventProcessor exception reading DB: " + str(error))
        raise
    finally:
        if cur is not None:
            cur.close()

    # get a record count
    try:
        cur = conn.cursor()
        cur.execute(sql_count, (pres_type,))
        row = cur.fetchone()
        if row is None:
            raise Exception("Error no records found with correct record type")
        pres_count = row[0]
        cur.close()
        cur = None
    except (Exception, psycopg2.DatabaseError) as error:
        print("EventProcessor exception reading DB: " + str(error))
        raise
    finally:
        if cur is not None:
            cur.close()

    print(">>> record count:", pres_count)

    if not args.count:
        deleted_count = 0
        batch_count = args.batch
        while 0 < batch_count and deleted_count < args.max:
            # get items records that are pres reqs
            try:
                cur = conn.cursor()
                cur.execute(sql_items, (pres_type,))
                batch_count = 0
                ids = "("
                row = cur.fetchone()
                while row is not None:
                    if 0 < batch_count:
                        ids += ","
                    ids += str(row[0])
                    batch_count += 1
                    row = cur.fetchone()
                ids += ")"
                cur.close()
                cur = None

                if 0 < batch_count:
                    # delete tags associated with the pres req
                    print(">>> deleting:", batch_count)
                    cur = conn.cursor()
                    cur.execute(sql_del_etags + ids)
                    cur.execute(sql_del_utags + ids)

                    # delete the pres req item record
                    cur.execute(sql_del_items + ids)
                    cur.execute("commit")

                    deleted_count += batch_count
                    cur.close()
                    cur = None

            except (Exception, psycopg2.DatabaseError) as error:
                print("EventProcessor exception updating DB: " + str(error))
                raise
            finally:
                if cur is not None:
                    cur.close()

        print(">>> deleted:", deleted_count)
