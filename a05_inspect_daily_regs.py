import os
import sys
import json
import time
import pydicom
import datetime
import pandas as pd
from dicom_scp_class import Retriever_SCP
from dicom_scu_class import Retriever_SCU

def inspect_regs(day):
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)
    f.close()

    tx_ct_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_tx_ct_list.xlsx")
    tx_ct_df = pd.read_excel(tx_ct_file)
    tx_ct_df = tx_ct_df.astype(str)

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
        print(pt_list)

        for i in range (0, len(pt_list)):
            check_path = os.path.join(info['dicom_path'], pt_list[i])
            #print(check_path)
            ptid = pt_list[i]
            studyid = ''
            date = ''
            for root, dirs, files in os.walk(check_path):
                path = root.split(os.sep)
                #print(path)
                if (len(path) == 3):
                    studyid = str(os.path.basename(root))
                    #print(studyid)
                elif (len(path) == 4):
                    date = str(os.path.basename(root))
                    print(date)
                for file in files:
                    # print(date)
                    # print(date != day.strftime('%Y-%m-%d'))
                    if date != day.strftime('%Y-%m-%d'):
                        continue
                    if 'REG' in file:
                        print('---', ptid)
                        print(2 * '---', studyid)
                        print(3 * '---', date)
                        try:
                            f = os.path.join(root,file)
                            ds = pydicom.dcmread(f)
                            reg_id = ds.SOPInstanceUID
                            if 'ReferencedSeriesSequence' in ds.dir():
                                ct_ct_registration = True
                                first_id = ds.ReferencedSeriesSequence[0].SeriesInstanceUID
                                #print(ds.ReferencedSeriesSequence[0].ReferencedInstanceSequence[0].ReferencedSOPClassUID)
                                if (ds.ReferencedSeriesSequence[0].ReferencedInstanceSequence[0].ReferencedSOPClassUID != '1.2.840.10008.5.1.4.1.1.2'):
                                    ct_ct_registration = False
                                    #print('Referenced SOP Class UID: ' + ds.ReferencedSeriesSequence[0].ReferencedInstanceSequence[0].ReferencedSOPClassUID)
                                second_id = ds.ReferencedSeriesSequence[1].SeriesInstanceUID
                                #print(ds.ReferencedSeriesSequence[1].ReferencedInstanceSequence[0].ReferencedSOPClassUID)
                                if (ds.ReferencedSeriesSequence[1].ReferencedInstanceSequence[0].ReferencedSOPClassUID != '1.2.840.10008.5.1.4.1.1.2'):
                                    ct_ct_registration = False
                                    #print('Referenced SOP Class UID: ' + ds.ReferencedSeriesSequence[1].ReferencedInstanceSequence[0].ReferencedSOPClassUID)
                                
                                if ct_ct_registration:
                                    #print('CT-CT REGISTRATION FOUND!')
                                    char_first_el = first_id[0:3]
                                    char_second_el = second_id[0:3]
                                    len_first_el = len(first_id)
                                    len_second_el = len(second_id)

                                    if (char_first_el == '1.2') & ((char_second_el == '1.3') or (char_second_el == '2.1')):
                                        cbct_id = first_id
                                        ct_id = second_id
                                    elif ((char_first_el == '1.3') or (char_first_el == '2.1')) & (char_second_el == '1.2'):
                                        ct_id = first_id
                                        cbct_id = second_id
                                    elif (char_first_el == '1.2') & (char_second_el == '1.2') & (len_first_el == 56):
                                        cbct_id = first_id
                                        ct_id = second_id
                                    elif (char_first_el == '1.2') & (char_second_el == '1.2') & (len_second_el == 56):
                                        ct_id = first_id
                                        cbct_id = second_id

                                    #print((1+len(path)) * '---', 'CT = ' + ct_id)
                                    #print((1+len(path)) * '---', 'CBCT = ' + cbct_id)
                                    
                                    index = tx_ct_df[tx_ct_df['CBCT_SOPInstanceUID'] == cbct_id].index
                                    #print(index)
                                    for idx in index:
                                        tx_ct_df.at[idx,'StudyID'] = str(studyid)
                                        tx_ct_df.at[idx,'SIMCT_SOPInstanceUID'] = ct_id
                                        tx_ct_df.at[idx,'REG_SOPInstanceUID'] = reg_id
                                        #tx_ct_df.at[idx,'REG_Status'] = status
                                        #print((2+len(path)) * '---', 'Index = ' + str(idx))
                                        stu_uid = tx_ct_df.iloc[idx]['StudyInstanceUID']
                                        #print((2+len(path)) * '---', 'Study UID = ' + stu_uid)
                                        rpt_uid = tx_ct_df.iloc[idx]['RTPLAN_SOPInstanceUID']
                                        #print((2+len(path)) * '---', 'RTPlan UID = ' + rpt_uid)
                                        #checkfile = os.path.join(root, 'RTP.' + rpt_uid + '.dcm')
                                        checkfile = os.path.join(plans_with_cts, ptid, studyid, 'RTP.' + rpt_uid + '.dcm')
                                        if not os.path.isfile(checkfile):
                                            print((1+len(path)) * '---', 'Retrieving RTPLAN: ' + rpt_uid)
                                            scu.check_status()
                                            scu.retrieve_plan(str(ptid), str(stu_uid), str(rpt_uid))
                                        else:
                                            print((1+len(path)) * '---', '-- RTP already exists...')
                        except Exception as exc:
                            print(' !!!!! Error occured inspecting REG file: ' + file)
                            print(exc)
                        
        #nanindex = tx_ct_df[tx_ct_df['REG_SOPInstanceUID'] == "nan"].index

        try:
            tx_ct_df.to_excel(tx_ct_file, index=False)
        except Exception as exc:
            print(' !!!!! Unable to write cross referenced list to file: ' + tx_ct_file)
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
        print(" !!!!! inspect_daily_regs takes 0 or 1 date argument in iso format (i.e. YYYY-MM-DD).\n")
        exit

    print("Inspecting REGs from " + query_day.strftime('%Y%m%d'))
    inspect_regs(query_day)
