import os
import sys
import json
import time
import pydicom
import datetime
import pandas as pd
import numpy as np
from dicom_scp_class import Retriever_SCP
from dicom_scu_class import Retriever_SCU

def inspect_rtplans(day):
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)
    f.close()

    tx_ct_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_tx_ct_list.xlsx")
    tx_ct_df = pd.read_excel(tx_ct_file, dtype = str)
    tx_ct_df['REG_SOPInstanceUID'].replace('', np.nan, inplace=True)
    tx_ct_df.dropna(subset=['REG_SOPInstanceUID'], inplace=True)
    temp_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_temp_list1.xlsx")
    tx_ct_df.to_excel(temp_file, index=False)

    if len(tx_ct_df['index_x']) > 0:

        plan_names = []
        confidence = []
        RTS_SOP = []

        plans_with_cts = os.path.join(info['staging_path'], 'daily_cbct_data')
        #print(plans_with_cts)

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

        print('Number Scans:', tx_ct_df['index_x'].count())

        for i in range (0, tx_ct_df['index_x'].count()):
            ptid = tx_ct_df.iloc[i]['PatientID']
            print('pat---', ptid)
            studyid = tx_ct_df.iloc[i]['StudyID']
            print(2 * '---', studyid)
            root = os.path.join(plans_with_cts, ptid, studyid)
            datepath = os.path.join(root, day.strftime('%Y-%m-%d'))
            planfile = "RTP." + tx_ct_df.iloc[i]['RTPLAN_SOPInstanceUID'] + ".dcm"
            try:
                f = os.path.join(root,planfile)
                ds = pydicom.dcmread(f)
                planid = np.nan
                if len(ds.RTPlanLabel) > 0:
                    planid = ds.RTPlanLabel
                elif len(ds.RTPlanName) > 0:
                    planid = ds.RTPlanName


                print('INDEX: ', i)
                plan_names.append(planid)
                #tx_ct_df.at[i,'RTPlanLabel'] = planid

                print(3 * '---', 'Plan ID = ', str(planid))
                stu_uid = ds.StudyInstanceUID
                rts_uid = ds.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID
                print(4 * '---', 'RTStruct UID = ', str(rts_uid))
                checkfile = os.path.join(root, 'RTS.' + str(rts_uid) + '.dcm')
                if os.path.isfile(checkfile):
                    print(4 * '---', '-- RTS already exists...')
                else:
                    print(4 * '---', 'Retrieving RTSTRUCT: ', str(rts_uid))
                    scu.check_status()
                    scu.retrieve_struct(str(ptid), str(stu_uid), str(rts_uid))

                confidence.append('NA')
                RTS_SOP.append(rts_uid)
                # tx_ct_df.at[i,'Confidence'] = 'NA'
                # tx_ct_df.at[i,'RTSTRUCT_SOPInstanceUID'] = rts_uid
                ctid = tx_ct_df.iloc[i]['SIMCT_SOPInstanceUID']
                checkdir = os.path.join(root, 'CT.' + str(ctid))
                if os.path.isdir(checkdir):
                    print(4 * '---', '-- CT already exists...')
                elif ctid == '':
                    print(4 * '---', '!! CT ID NOT VALID !! ...')
                else:
                    print(4 * '---', 'Retrieving CT Images: ', str(ctid))
                    #print(str(ptid), str(stu_uid), str(ctid))
                    scu.check_status()
                    scu.retrieve_ct(str(ptid), str(stu_uid), str(ctid))
                cbctid = tx_ct_df.iloc[i]['CBCT_SOPInstanceUID']
                checkdir = os.path.join(datepath, 'CBCT.' + str(cbctid))
                if os.path.isdir(checkdir):
                    print(4 * '---', '-- CBCT already exists...')
                elif cbctid == '':
                    print(4 * '---', '!! CBCT ID NOT VALID !! ...')
                else:
                    print(4 * '---', 'Retrieving CBCT Images: ', str(cbctid))
                    #print(str(ptid), str(stu_uid), str(cbctid))
                    scu.check_status()
                    scu.retrieve_ct(str(ptid), str(stu_uid), str(cbctid))
                                    
            except Exception as exc:
                print(' !!!!! Error occurred inspecting RTPLAN file: ' + planfile)
                print(exc)
                plan_names.append(np.nan)
                confidence.append('NA')
                RTS_SOP.append(np.nan)
                continue

        print("Plans Number:", plan_names)

        tx_ct_df2 = tx_ct_df

        tx_ct_df2['RTPlanLabel'] = plan_names
        tx_ct_df2['Confidence'] = confidence
        tx_ct_df2['RTSTRUCT_SOPInstanceUID'] = RTS_SOP

        print(tx_ct_df['RTPlanLabel'])

        try:
            tx_ct_df2.to_excel(tx_ct_file, index=False)
        except Exception as exc:
            print(' !!!!! Unable to write cross reference tx-ct list to file')
            print(exc)

        #tx_ct_df['REG_SOPInstanceUID'].replace('', np.nan, inplace=True)
        tx_ct_df['RTSTRUCT_SOPInstanceUID'].replace('', np.nan, inplace=True)
        predict_df = tx_ct_df.dropna(subset=['REG_SOPInstanceUID','RTSTRUCT_SOPInstanceUID'])

        try:
            dataframe_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_predict_list.xlsx")
            predict_df.to_excel(dataframe_file, index=False)
        except Exception as exc:
            print(' !!!!! Unable to write prediction list to file')
            print(exc)

        # stop scu
        scu.release()
        scu.shutdown()

        # stop scp
        time.sleep(5)
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
        print(" !!!!! inspect_daily_rtplans takes 0 or 1 date argument in iso format (i.e. YYYY-MM-DD).\n")
        exit

    print("Inspecting RTPLANs from " + query_day.strftime('%Y%m%d'))
    inspect_rtplans(query_day)
