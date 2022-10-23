#!/usr/bin/python
import os 
import psycopg2
import pytz
import datetime
import time
import json
import decimal
import requests
import csv

from config import CORP_TYPES_IN_SCOPE, corp_num_with_prefix, bare_corp_num
from rocketchat_hooks import log_error, log_warning, log_info


MIN_START_DATE = datetime.datetime(datetime.MINYEAR+1, 1, 1)
MIN_VALID_DATE = datetime.datetime(datetime.MINYEAR+10, 1, 1)
MAX_END_DATE   = datetime.datetime(datetime.MAXYEAR-1, 12, 31)

# for now, we are in PST time
timezone = pytz.timezone("PST8PDT")

MIN_START_DATE_TZ = timezone.localize(MIN_START_DATE)
MIN_VALID_DATE_TZ = timezone.localize(MIN_VALID_DATE)
MAX_END_DATE_TZ   = timezone.localize(MAX_END_DATE)


# determine jurisdiction for corp
def get_corp_jurisdiction(corp_typ_cd, corp_class, can_jur_typ_cd, othr_juris_desc):
    registered_jurisdiction = ""
    if corp_class == 'BC':
        registered_jurisdiction = "BC"
    elif corp_class == 'XPRO' or corp_typ_cd == 'XP' or corp_typ_cd == 'XL' or corp_typ_cd == 'XCP' or corp_typ_cd == 'XS':
        if can_jur_typ_cd is not None and 0 < len(can_jur_typ_cd):
            if can_jur_typ_cd == 'OT':
                if othr_juris_desc is not None and 0 < len(othr_juris_desc):
                    registered_jurisdiction = othr_juris_desc
                else:
                    registered_jurisdiction = can_jur_typ_cd
            else:
                registered_jurisdiction = can_jur_typ_cd
    else:
        # default to BC
        registered_jurisdiction = "BC"
    return registered_jurisdiction


def compare_dates_lear(orgbook_reg_dt, bc_reg_reg_dt):
    # convert to string if necessary
    if isinstance(orgbook_reg_dt, datetime.datetime):
        orgbook_reg_dt = orgbook_reg_dt.astimezone(pytz.utc).isoformat()
    if isinstance(bc_reg_reg_dt, datetime.datetime):
        bc_reg_reg_dt = bc_reg_reg_dt.astimezone(pytz.utc).isoformat()
    if bc_reg_reg_dt is None or len(bc_reg_reg_dt) == 0 or bc_reg_reg_dt.startswith('0001-01-01'):
        if orgbook_reg_dt is None or len(orgbook_reg_dt) == 0 or orgbook_reg_dt.startswith('0001-01-01'):
            return True
        return False
    if orgbook_reg_dt is None or len(orgbook_reg_dt) == 0 or orgbook_reg_dt.startswith('0001-01-01'):
        return False
    return (bc_reg_reg_dt == orgbook_reg_dt)

# compare registration dates
def compare_dates_colin(orgbook_reg_dt, bc_reg_reg_dt):
    if bc_reg_reg_dt is None or len(bc_reg_reg_dt) == 0:
        if orgbook_reg_dt is None or len(orgbook_reg_dt) == 0:
            return True
        return MIN_START_DATE_TZ.astimezone(pytz.utc).isoformat() == orgbook_reg_dt
    if orgbook_reg_dt is None or len(orgbook_reg_dt) == 0:
        return bc_reg_reg_dt == '0001-01-01 00:00:00'
    try:
        bc_reg_reg_dt_obj = datetime.datetime.strptime(bc_reg_reg_dt, '%Y-%m-%d %H:%M:%S')
        bc_reg_reg_dt_tz = timezone.localize(bc_reg_reg_dt_obj)
        bc_reg_reg_dt_tz_str = bc_reg_reg_dt_tz.astimezone(pytz.utc).isoformat()
        return bc_reg_reg_dt_tz_str == orgbook_reg_dt
    except (Exception) as error:
        return MIN_START_DATE_TZ.astimezone(pytz.utc).isoformat() == orgbook_reg_dt

# compare registration dates
def compare_dates(orgbook_reg_dt, bc_reg_reg_dt, USE_LEAR: bool = False):
    if USE_LEAR:
        return compare_dates_lear(orgbook_reg_dt, bc_reg_reg_dt)
    else:
        return compare_dates_colin(orgbook_reg_dt, bc_reg_reg_dt)

def compare_bc_reg_orgbook(bc_reg_corp_types, bc_reg_corp_names, bc_reg_corp_infos, orgbook_corp_types, orgbook_corp_names, orgbook_corp_infos, future_corps, USE_LEAR: bool = False):
    missing_in_orgbook = []
    missing_in_bcreg = []
    wrong_corp_type = []
    wrong_corp_name = []
    wrong_corp_status = []
    wrong_bus_num = []
    wrong_corp_reg_dt = []
    wrong_corp_juris = []

    # check if all the BC Reg corps are in orgbook (with the same corp type)
    error_msgs = ""
    error_cmds = ""
    for bc_reg_corp_num in bc_reg_corp_types:
        bc_reg_corp_type = bc_reg_corp_types[bc_reg_corp_num]
        bc_reg_corp_name = bc_reg_corp_names[bc_reg_corp_num]
        bc_reg_corp_info = bc_reg_corp_infos[bc_reg_corp_num]
        if bare_corp_num(bc_reg_corp_num) in future_corps:
            #print("Future corp ignore:", row["corp_num"])
            pass
        elif not bc_reg_corp_num in orgbook_corp_types:
            # not in orgbook
            error_msgs += "Topic not found for: " + bc_reg_corp_num + "\n"
            missing_in_orgbook.append(bc_reg_corp_num)
            error_cmds += "./manage -e prod queueOrganization " + bare_corp_num(bc_reg_corp_num) + "\n"
            pass
        elif (not orgbook_corp_types[bc_reg_corp_num]) or (orgbook_corp_types[bc_reg_corp_num] != bc_reg_corp_type):
            # in orgbook but has the wrong corp type in orgbook
            error_msgs += "Corp Type mis-match for: " + bc_reg_corp_num + '; BC Reg: "'+bc_reg_corp_type+'", OrgBook: "'+orgbook_corp_types[bc_reg_corp_num]+'"' + "\n"
            wrong_corp_type.append(bc_reg_corp_num)
            error_cmds += "./manage -p bc -e prod deleteTopic " + bc_reg_corp_num + "\n"
            error_cmds += "./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num) + "\n"
        elif (orgbook_corp_names[bc_reg_corp_num].strip() != bc_reg_corp_name.strip()):
            # in orgbook but has the wrong corp name in orgbook
            error_msgs += "Corp Name mis-match for: " + bc_reg_corp_num + ' BC Reg: "'+bc_reg_corp_name+'", OrgBook: "'+orgbook_corp_names[bc_reg_corp_num]+'"' + "\n"
            wrong_corp_name.append(bc_reg_corp_num)
            error_cmds += "./manage -p bc -e prod deleteTopic " + bc_reg_corp_num + "\n"
            error_cmds += "./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num) + "\n"
        elif (orgbook_corp_infos[bc_reg_corp_num]["entity_status"] != bc_reg_corp_info["op_state_typ_cd"]):
            # wrong entity status
            error_msgs += "Corp Status mis-match for: " + bc_reg_corp_num + ' BC Reg: "'+bc_reg_corp_info["op_state_typ_cd"]+'", OrgBook: "'+orgbook_corp_infos[bc_reg_corp_num]["entity_status"]+'"' + "\n"
            wrong_corp_status.append(bc_reg_corp_num)
            error_cmds += "./manage -p bc -e prod deleteTopic " + bc_reg_corp_num + "\n"
            error_cmds += "./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num) + "\n"
        elif (orgbook_corp_infos[bc_reg_corp_num]["bus_num"].strip() != bc_reg_corp_info["bn_9"].strip()):
            # wrong BN9 business number
            error_msgs += "Business Number mis-match for: " + bc_reg_corp_num + ' BC Reg: "'+bc_reg_corp_info["bn_9"]+'", OrgBook: "'+orgbook_corp_infos[bc_reg_corp_num]["bus_num"]+'"' + "\n"
            wrong_bus_num.append(bc_reg_corp_num)
            error_cmds += "./manage -p bc -e prod deleteTopic " + bc_reg_corp_num + "\n"
            error_cmds += "./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num) + "\n"
        elif (not compare_dates(orgbook_corp_infos[bc_reg_corp_num]["registration_date"], bc_reg_corp_info["recognition_dts"], USE_LEAR=USE_LEAR)):
            # wrong registration date
            error_msgs += "Corp Registration Date mis-match for: " + bc_reg_corp_num + ' BC Reg: "'+bc_reg_corp_info["recognition_dts"]+'", OrgBook: "'+orgbook_corp_infos[bc_reg_corp_num]["registration_date"]+'"' + "\n"
            wrong_corp_reg_dt.append(bc_reg_corp_num)
            error_cmds += "./manage -p bc -e prod deleteTopic " + bc_reg_corp_num + "\n"
            error_cmds += "./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num) + "\n"
        elif (orgbook_corp_infos[bc_reg_corp_num]["home_jurisdiction"] != get_corp_jurisdiction(bc_reg_corp_info["corp_type"], bc_reg_corp_info["corp_class"], bc_reg_corp_info["can_jur_typ_cd"], bc_reg_corp_info["othr_juris_desc"])):
            # wrong jurisdiction
            calc_juris = get_corp_jurisdiction(bc_reg_corp_info["corp_type"], bc_reg_corp_info["corp_class"], bc_reg_corp_info["can_jur_typ_cd"], bc_reg_corp_info["othr_juris_desc"])
            error_msgs += "Corp Jurisdiction mis-match for: " + bc_reg_corp_num + ' BC Reg: "'+calc_juris+'", OrgBook: "'+orgbook_corp_infos[bc_reg_corp_num]["home_jurisdiction"]+'"' + "\n"
            wrong_corp_juris.append(bc_reg_corp_num)
            error_cmds += "./manage -p bc -e prod deleteTopic " + bc_reg_corp_num + "\n"
            error_cmds += "./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num) + "\n"

    # now check if there are corps in orgbook that are *not* in BC Reg database
    for orgbook_corp in orgbook_corp_types:
        if not (orgbook_corp in bc_reg_corp_types):
            missing_in_bcreg.append(orgbook_corp)
            error_msgs += "OrgBook corp not in BC Reg: " + orgbook_corp + "\n"
            error_cmds += "./manage -p bc -e prod deleteTopic " + orgbook_corp + "\n"

    corp_errors = (len(missing_in_orgbook) +
                    len(missing_in_bcreg) +
                    len(wrong_corp_type) +
                    len(wrong_corp_name) +
                    len(wrong_corp_status) +
                    len(wrong_bus_num) +
                    len(wrong_corp_reg_dt) +
                    len(wrong_corp_juris))

    if 0 < corp_errors:
        log_error(error_msgs)
        log_error(error_cmds)

    error_summary = ""
    error_summary += "Missing in OrgBook:      " + str(len(missing_in_orgbook)) + " " + str(missing_in_orgbook) + "\n"
    error_summary += "Missing in BC Reg:       " + str(len(missing_in_bcreg)) + " " + str(missing_in_bcreg) + "\n"
    error_summary += "Wrong corp type:         " + str(len(wrong_corp_type)) + " " + str(wrong_corp_type) + "\n"
    error_summary += "Wrong corp name:         " + str(len(wrong_corp_name)) + " " + str(wrong_corp_name) + "\n"
    error_summary += "Wrong corp status:       " + str(len(wrong_corp_status)) + " " + str(wrong_corp_status) + "\n"
    error_summary += "Wrong business number:   " + str(len(wrong_bus_num)) + " " + str(wrong_bus_num) + "\n"
    error_summary += "Wrong corp registration: " + str(len(wrong_corp_reg_dt)) + " " + str(wrong_corp_reg_dt) + "\n"
    error_summary += "Wrong corp jurisdiction: " + str(len(wrong_corp_juris)) + " " + str(wrong_corp_juris) + "\n"

    if 0 < corp_errors:
        log_error(error_summary)
    else:
        log_info(error_summary)

    return wrong_bus_num
