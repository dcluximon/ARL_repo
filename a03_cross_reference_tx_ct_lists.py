import os
import sys
import json
import datetime
import pandas as pd

def cross_reference(day):
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)

    dtx_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + '_daily_tx_list.xlsx')
    dct_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + '_daily_ct_list.xlsx')

    dtx_df = pd.read_excel(dtx_file, dtype = str)
    dct_df = pd.read_excel(dct_file, dtype = str)

    tx_ct_df = pd.merge(dtx_df, dct_df, on=['PatientID', 'StudyInstanceUID'], left_index=False, right_index=False)
    tx_ct_df['StudyID'] = ""
    tx_ct_df['RTPlanLabel'] = ""
    tx_ct_df['SIMCT_SOPInstanceUID'] = ""
    tx_ct_df['RTSTRUCT_SOPInstanceUID'] = ""
    tx_ct_df['REG_SOPInstanceUID'] = ""
    tx_ct_df['Confidence'] = ""
    tx_ct_df.rename(columns={"ReferencedSOPInstanceUID": "RTPLAN_SOPInstanceUID", "SeriesInstanceUID_y": "CBCT_SOPInstanceUID"}, inplace=True)

    count = len(tx_ct_df.index)
    print(' >>> ' + str(count) + ' entries in cross-referenced tx-ct list.')

    try:
        dataframe_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_tx_ct_list.xlsx")
        tx_ct_df.to_excel(dataframe_file, index=False)
    except Exception as exc:
        print(' !!!!! Unable to write cross referenced list to file: ' + dataframe_file)
        print(exc)

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
        print(" !!!!! find_daily_ct_list takes 0 or 1 date argument in iso format (i.e. YYYY-MM-DD).\n")
        exit

    print("Cross-referencing Treatments and CTs from " + query_day.strftime('%Y%m%d'))
    cross_reference(query_day)