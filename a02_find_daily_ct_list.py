import os
import sys
import json
import datetime
import pandas as pd
from dicom_scu_class import Retriever_SCU

def find_daily_cts(day):
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)

    scu = Retriever_SCU(info['ARIA']['AETITLE'], 
                        info['ARIA']['HOST'], 
                        info['ARIA']['PORT'], 
                        info['LOCAL_SCU']['AETITLE'], 
                        info['LOCAL_SCP']['AETITLE'])
    scu.launch_echo()
    results = scu.find_daily_cts(day.strftime('%Y-%m-%d'))
    scu.release()
    scu.shutdown()

    count = len(results)
    print(' >>> ' + str(count) + ' CT acquisitions found.')
    df = pd.DataFrame(results)

    try:
        dataframe_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_daily_ct_list.xlsx")
        df.to_excel(dataframe_file, index=False)
    except Exception as exc:
        print(' !!!!! Unable to save daily ct list: ' + dataframe_file)
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

    print("Querying CTs from " + query_day.strftime('%Y%m%d'))
    find_daily_cts(query_day)
