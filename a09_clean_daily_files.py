import os
import sys
import json
import shutil
import datetime
from xml.dom.minidom import ReadOnlySequentialNamedNodeMap

def cleanup(day):
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)
    f.close()

    save_dicoms = False
    if info['save_dicom_data_switch'] == "True":
        save_dicoms = True
    archive_path = info['archive_path']
    log_path = info['log_path']
    log_filepath = os.path.join(log_path, day.strftime('%Y-%m-%d') + "_logfile.txt")
    log = open(log_filepath, 'a')

    day_path = os.path.join(archive_path, day.strftime('%Y-%m-%d'))
    try:
        os.makedirs(day_path, exist_ok=True)
    except Exception as exc:
        log.write(' !!!!! Unable to create daily archive directory !!!!!')
        log.write(exc)
    """
    dtx_file = os.path.join(info['staging_path'], "daily_tx_list.xlsx")
    dtx_archive = os.path.join(day_path, day.strftime('%Y-%m-%d') + "_daily_tx_list.xlsx")
    if os.path.isfile(dtx_file):
        try:
            log.write('Archiving daily tx list...\n')
            shutil.move(dtx_file, dtx_archive)
        except Exception as exc:
            log.write(' !!!!! Unable to archive daily tx list\n')
            log.write(exc)

    dct_file = os.path.join(info['staging_path'], "daily_ct_list.xlsx")
    dct_archive = os.path.join(day_path, day.strftime('%Y-%m-%d') + "_daily_ct_list.xlsx")
    if os.path.isfile(dct_file):
        try:
            log.write('Archiving daily ct list...\n')
            shutil.move(dct_file, dct_archive)
        except Exception as exc:
            log.write(' !!!!! Unable to archive daily ct list\n')
            log.write(exc)

    tx_ct_file = os.path.join(info['staging_path'], "tx_ct_list.xlsx")
    tx_ct_archive = os.path.join(day_path, day.strftime('%Y-%m-%d') + "_tx_ct_list.xlsx")
    if os.path.isfile(tx_ct_file):
        try:
            log.write('Archiving cross reference tx-ct list...\n')
            shutil.move(tx_ct_file, tx_ct_archive)
        except Exception as exc:
            log.write(' !!!!! Unable to cross reference tx-ct list\n')
            log.write(exc)
    
    predict_file = os.path.join(info['staging_path'], "predict_list.xlsx")
    predict_archive = os.path.join(day_path, day.strftime('%Y-%m-%d') + "_predict_list.xlsx")
    if os.path.isfile(predict_file):
        try:
            log.write('Archiving prediction list...\n')
            shutil.move(predict_file, predict_archive)
        except Exception as exc:
            log.write(' !!!!! Unable to archive prediction list\n')
            log.write(exc)

    plans_with_cts = os.path.join(info['staging_path'], 'daily_cbct_data')
    if os.path.isdir(plans_with_cts):
        if save_dicoms:
            rename_plans_with_cts = os.path.join(info['staging_path'], day.strftime('%Y-%m-%d') + '_daily_cbct_data')
            try:
                log.write('DICOM data files remain at ... ' + plans_with_cts)
                #log.write('DICOM data files renamed to ... ' + rename_plans_with_cts)
                #os.rename(plans_with_cts, rename_plans_with_cts)
            except Exception as exc:
                log.write(' !!!!! Error occurred attempting to rename DICOM data directory to ... ' + rename_plans_with_cts)
                log.write(exc)
        else:
            try:
                log.write('Deleting temporary DICOM files...\n')
                shutil.rmtree(plans_with_cts)
            except Exception as exc:
                log.write(' !!!!! Error occurred deleting temporary DICOM files\n')
                log.write(exc)
    """
    log_archive = os.path.join(log_path, day.strftime('%Y-%m-%d') + "_logfile.txt")
    if os.path.exists(log_filepath):
        try:
            log.write('Archiving log...\n')
            log.close()
            #shutil.move(log_filepath, log_archive)
        except Exception as exc:
            log.write(' !!!!! Unable to archive log\n')
            log.write(exc)
            log.close()

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
        print(" !!!!! clean_daily_files takes 0 or 1 date argument in iso format (i.e. YYYY-MM-DD).\n")
        exit

    print("Cleaning up temporary files for " + query_day.strftime('%Y%m%d'))
    cleanup(query_day)