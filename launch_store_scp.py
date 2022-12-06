import os
import sys
import json
import datetime
import pandas as pd
from dicom_scp_class import Retriever_SCP
from threading import Thread


def shutdown_scp():
    user = input("\n\nPress any key to shutdown STORE SCP...\n\n")
    print(user)
    
if __name__ == '__main__':
    print("Starting Up STORE SCP ... ")
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)
    f.close()

    plans_with_cts = os.path.join(info['staging_path'], 'daily_cbct_data')

    # start scp
    scp = Retriever_SCP(plans_with_cts,
                        info['ARIA']['AETITLE'], 
                        info['ARIA']['HOST'], 
                        info['ARIA']['PORT'], 
                        info['LOCAL_SCP']['AETITLE'], 
                        info['LOCAL_SCP']['HOST'], 
                        info['LOCAL_SCP']['PORT'])

    shutdown_thread = Thread(target=shutdown_scp)
    shutdown_thread.start()

    scp.start()
    
    shutdown_thread.join()
    scp.stop()
