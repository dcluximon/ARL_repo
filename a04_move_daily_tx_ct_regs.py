import os
import sys
import json
import time
import datetime
import pandas as pd
from dicom_scp_class import Retriever_SCP
from dicom_scu_class import Retriever_SCU

def move_daily_regs(day):
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)
    f.close()

    tx_ct_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_tx_ct_list.xlsx")
    tx_ct_df = pd.read_excel(tx_ct_file, dtype = str)

    if len(tx_ct_df['index_x']) > 0:
        plans_with_cts = info['dicom_path']

        # start scp
        scp = Retriever_SCP(plans_with_cts,
                            info['ARIA']['AETITLE'],
                            info['ARIA']['HOST'], 
                            info['ARIA']['PORT'], 
                            info['LOCAL_SCP']['AETITLE'], 
                            info['LOCAL_SCP']['HOST'], 
                            info['LOCAL_SCP']['PORT'],
                            day.strftime('%Y-%m-%d'))

        # start scu
        scu = Retriever_SCU(info['ARIA']['AETITLE'], 
                            info['ARIA']['HOST'], 
                            info['ARIA']['PORT'], 
                            info['LOCAL_SCU']['AETITLE'], 
                            info['LOCAL_SCP']['AETITLE'])
        scu.launch_echo()

        pt_list = tx_ct_df['PatientID'].unique().tolist()
        for i in range (0, len(pt_list)):
            try:
                #check_path = os.path.join(plans_with_cts, tx_ct_df.iloc[i]['PatientID'])
                check_path = os.path.join(plans_with_cts, pt_list[i])
                #print(check_path)
                studyid = ''
                date = ''
                reg_found = False
                for root, dirs, files in os.walk(check_path):
                    path = root.split(os.sep)
                    #print(path)
                    if (len(path) == 3):
                        studyid = str(os.path.basename(root))
                    elif (len(path) == 4):
                        date = str(os.path.basename(root))
                    #print((len(path) - 1) * '---', os.path.basename(root))
                    #print(studyid, date)
                    for file in files:
                        if date != day.strftime('%Y-%m-%d'):
                            continue
                        if 'REG' in file:
                            #print('---', studyid)
                            #print(2 * '---', date)
                            #print(len(path) * '---', file)
                            reg_found = True
                if reg_found:
                    print(" >>> Registrations already retrieved for Patient " + pt_list[i] + " on " + day.strftime('%Y-%m-%d'))
                else:
                    #print(" !!! RETRIEVE REGS")
                    #scu.retrieve_reg( tx_ct_df.iloc[i]['PatientID'] )
                    scu.check_status()
                    scu.retrieve_reg( pt_list[i] )
            except Exception as exc:
                print(' !!!!! Unable to retrieve REG for patient: ' + pt_list[i] + " on " + day.strftime('%Y-%m-%d'))
                print(exc)

        # stop scu
        scu.release()
        scu.shutdown()

        # stop scp
        time.sleep(30)
        scp.stop()

if __name__ == '__main__':
    today = datetime.datetime.today()
    yesterday = today - datetime.timedelta(days = 1)
    query_day = yesterday
    if len(sys.argv) == 2:
        try:
            query_day = datetime.date.fromisoformat(sys.argv[1])
        except Exception as exc:
            print(" !!!!! Could not parse date input. Please use iso format (i.e. YYYY-MM-DD)\n")
            print(exc)
            exit
    elif len(sys.argv) > 2:
        print(" !!!!! move_daily_tx_ct_regs takes 0 or 1 date argument in iso format (i.e. YYYY-MM-DD).\n")
        exit

    print("Retrieving REGs from " + query_day.strftime('%Y%m%d'))
    move_daily_regs(query_day)
