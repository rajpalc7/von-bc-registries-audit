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


# compare registration dates
def compare_dates(orgbook_reg_dt, bc_reg_reg_dt):
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

def compare_bc_reg_orgbook(bc_reg_corp_types, bc_reg_corp_names, bc_reg_corp_infos, orgbook_corp_types, orgbook_corp_names, orgbook_corp_infos, future_corps):
    missing_in_orgbook = []
    missing_in_bcreg = []
    wrong_corp_type = []
    wrong_corp_name = []
    wrong_corp_status = []
    wrong_corp_reg_dt = []
    wrong_corp_juris = []

    # check if all the BC Reg corps are in orgbook (with the same corp type)
    for bc_reg_corp_num in bc_reg_corp_types:
        bc_reg_corp_type = bc_reg_corp_types[bc_reg_corp_num]
        bc_reg_corp_name = bc_reg_corp_names[bc_reg_corp_num]
        bc_reg_corp_info = bc_reg_corp_infos[bc_reg_corp_num]
        if bare_corp_num(bc_reg_corp_num) in future_corps:
            #print("Future corp ignore:", row["corp_num"])
            pass
        elif not bc_reg_corp_num in orgbook_corp_types:
            # not in orgbook
            #print("Topic not found for:", row)
            missing_in_orgbook.append(bc_reg_corp_num)
            print("./manage -e prod queueOrganization " + bare_corp_num(bc_reg_corp_num))
            pass
        elif (not orgbook_corp_types[bc_reg_corp_num]) or (orgbook_corp_types[bc_reg_corp_num] != bc_reg_corp_type):
            # in orgbook but has the wrong corp type in orgbook
            #print("Corp Type mis-match for:", row, orgbook_corp_types[row["corp_num"]])
            wrong_corp_type.append(bc_reg_corp_num)
            print("./manage -p bc -e prod deleteTopic " + bc_reg_corp_num)
            print("./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num))
        elif (orgbook_corp_names[bc_reg_corp_num] != bc_reg_corp_name):
            # in orgbook but has the wrong corp name in orgbook
            print("Corp Name mis-match for:", bc_reg_corp_num, 'BC Reg: "'+bc_reg_corp_name+'",', ' OrgBook: "'+orgbook_corp_names[bc_reg_corp_num]+'"')
            wrong_corp_name.append(bc_reg_corp_num)
            print("./manage -p bc -e prod deleteTopic " + bc_reg_corp_num)
            print("./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num))
        elif (orgbook_corp_infos[bc_reg_corp_num]["entity_status"] != bc_reg_corp_info["op_state_typ_cd"]):
            # wrong entity status
            print("Corp Status mis-match for:", bc_reg_corp_num, 'BC Reg: "'+bc_reg_corp_info["op_state_typ_cd"]+'",', ' OrgBook: "'+orgbook_corp_infos[bc_reg_corp_num]["entity_status"]+'"')
            wrong_corp_status.append(bc_reg_corp_num)
            print("./manage -p bc -e prod deleteTopic " + bc_reg_corp_num)
            print("./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num))
        elif (not compare_dates(orgbook_corp_infos[bc_reg_corp_num]["registration_date"], bc_reg_corp_info["recognition_dts"])):
            # wrong registration date
            print("Corp Registration Date mis-match for:", bc_reg_corp_num, 'BC Reg: "'+bc_reg_corp_info["recognition_dts"]+'",', ' OrgBook: "'+orgbook_corp_infos[bc_reg_corp_num]["registration_date"]+'"')
            wrong_corp_reg_dt.append(bc_reg_corp_num)
            print("./manage -p bc -e prod deleteTopic " + bc_reg_corp_num)
            print("./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num))
        elif (orgbook_corp_infos[bc_reg_corp_num]["home_jurisdiction"] != get_corp_jurisdiction(bc_reg_corp_info["corp_type"], bc_reg_corp_info["corp_class"], bc_reg_corp_info["can_jur_typ_cd"], bc_reg_corp_info["othr_juris_desc"])):
            # wrong jurisdiction
            calc_juris = get_corp_jurisdiction(bc_reg_corp_info["corp_type"], bc_reg_corp_info["corp_class"], bc_reg_corp_info["can_jur_typ_cd"], bc_reg_corp_info["othr_juris_desc"])
            print("Corp Jurisdiction mis-match for:", bc_reg_corp_num, 'BC Reg: "'+calc_juris+'",', ' OrgBook: "'+orgbook_corp_infos[bc_reg_corp_num]["home_jurisdiction"]+'"')
            wrong_corp_juris.append(bc_reg_corp_num)
            print("./manage -p bc -e prod deleteTopic " + bc_reg_corp_num)
            print("./manage -e prod requeueOrganization " + bare_corp_num(bc_reg_corp_num))

    # now check if there are corps in orgbook that are *not* in BC Reg database
    for orgbook_corp in orgbook_corp_types:
        if not (orgbook_corp in bc_reg_corp_types):
            missing_in_bcreg.append(orgbook_corp)
            #print("OrgBook corp not in BC Reg:", orgbook_corp)
            #print("./manage -p bc -e prod deleteTopic " + orgbook_corp)

    #print("Missing in OrgBook:      ", len(missing_in_orgbook), missing_in_orgbook)
    #print("Missing in BC Reg:       ", len(missing_in_bcreg), missing_in_bcreg)
    print("Wrong corp type:         ", len(wrong_corp_type), wrong_corp_type)
    print("Wrong corp name:         ", len(wrong_corp_name), wrong_corp_name)
    print("Wrong corp status:       ", len(wrong_corp_status), wrong_corp_status)
    print("Wrong corp registration: ", len(wrong_corp_reg_dt), wrong_corp_reg_dt)
    print("Wrong corp jurisdiction: ", len(wrong_corp_juris), wrong_corp_juris)
