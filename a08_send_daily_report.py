import os
import sys
import json
import datetime
import pandas as pd
import numpy as np
import math

def check_if_highlighted(s, threshold):
    if s == -1:
        return "<td style='color:red;'> Prediction Error </td>\n"
    elif s == -2:
        return "<td> Plan Mis-Match </td>\n"
    elif s == -3:
        return "<td style='color:red;'> Unable to Retrieve Images </td>\n"
    elif math.isnan(s):
        return "<td style='color:red;'> --- </td>\n"
    elif s > threshold:
        return "<td style='color:darkorange;'><b>{0:1.2e}</b></td>\n".format(s)
    else:
        return "<td style='color:darkgreen;'><b>{0:1.2e}</b></td>\n".format(s)

def filter_report(df):
    indices_to_drop = []
    label_list_to_delete = ['dail', 'qa', 'qc', 'match']

    for i,row in df.iterrows():
        # print(row['PatientID'])
        # print(row['TreatmentDate'])
        # print(row['TreatmentTime'])
        # print(row['AcquisitionDate'])
        # print(row['AcquisitionTime'])

        try:
            if '-' in row['PatientID']:
                if i not in indices_to_drop:
                    indices_to_drop.append(i)
                    print('dropped using ID')
                    #print(row['PatientID'])
        except:
            pass

        for item in label_list_to_delete:
            if item in row['RTPlanLabel'].lower():
                if i not in indices_to_drop:
                    indices_to_drop.append(i)
                    print('dropped using label')
                    break

        for j, row2 in df.iterrows():
            if (float(row['TreatmentTime']) - float(row['AcquisitionTime'])) < 0:
                if i not in indices_to_drop:
                    indices_to_drop.append(i)
                    print(indices_to_drop)
                    break
            if j>i:
                if (row['PatientID'] == row2['PatientID']) & (row['TreatmentDate'] == row2['TreatmentDate']) & (row['RTPlanLabel'] == row2['RTPlanLabel']):
                    if (float(row2['TreatmentTime']) - float(row2['AcquisitionTime'])) > (float(row['TreatmentTime']) - float(row['AcquisitionTime'])):
                        if j not in indices_to_drop:
                            indices_to_drop.append(j)
                            print(indices_to_drop)

                    elif (float(row2['TreatmentTime']) - float(row2['AcquisitionTime'])) < 0:
                        if j not in indices_to_drop:
                            indices_to_drop.append(j)
                            print(indices_to_drop)

                    elif (float(row['TreatmentTime']) - float(row['AcquisitionTime'])) > (float(row2['TreatmentTime']) - float(row2['AcquisitionTime'])):
                        if i not in indices_to_drop:
                            indices_to_drop.append(i)
                            print(indices_to_drop)
                            break

    df.drop(df.index[indices_to_drop], inplace=True)

    return df


def send_report(day):
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)

    predict_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_predict_list.xlsx")
    logo_file = os.path.join(info['asset_path'], info['logo'])

    if os.path.isfile(predict_file):
        raw_predict_df = pd.read_excel(predict_file, dtype = str)
        raw_predict_df['Region'].replace('', np.nan, inplace=True)
        raw_predict_df.replace(r'^\s*$', '---', inplace=True)
        predict_df = raw_predict_df.dropna(subset=['Region'])
        predict_df = filter_report(predict_df)

        if len(predict_df['index_x']) > 0:
            try:
                report_df = pd.DataFrame()
                report_df['MRN'] = predict_df['PatientID']
                report_df['Study'] = predict_df['StudyID']
                report_df['Plan'] = predict_df['RTPlanLabel']
                report_df['Machine'] = predict_df['Machine']
                report_df['TxDate'] = predict_df['TreatmentDate'].apply(lambda s : str(s)[0:4] + "-" + str(s)[4:6] + "-" + str(s)[6:8] if len(str(s)) > 0 else 'n/a')
                report_df['TxTime'] = predict_df['TreatmentTime'].apply(lambda s: str(s)[0:2] + ":" + str(s)[2:4] + ":" + str(s)[4:6] if len(str(s)) > 0 else 'n/a')
                report_df['Region'] = predict_df['Region']
                report_df['CBCT_AcquisitionTime'] = predict_df['AcquisitionTime'].apply(lambda s: str(s)[0:2] + ":" + str(s)[2:4] + ":" + str(s)[4:6] if len(str(s)) > 5 else '---')
                report_df['CBCT_SOPInstanceUID'] = predict_df['CBCT_SOPInstanceUID']
                print(report_df)
            except Exception as exc:
                print(' !!!!! Error occurred generating report dataframe')
                print(exc)

            html = "<html>\n"
            html += "<head>\n"
            html += "<style>\n"
            html += "* { font-family: sans-serif; }\n"
            html += "body { padding: 20px; }\n"
            html += "table { border-collapse: collapse; text-align: right; }\n"
            html += "table tr { border-bottom: 1px solid }\n"
            html += "table th, table td { padding: 10px 20px; }\n"
            html += "</style>\n"
            html += "</head>\n"
            html += "<body>\n"
            html += "<img src='" + logo_file + "' width='300'></img>\n"
            html += "<h1>Daily CBCT Alignment Analysis Report</h1>\n"
            html += "<table>\n<thead>\n<tr>\n"
            html += "<th>MRN</th>\n"
            html += "<th>Study</th>\n"
            html += "<th>Plan</th>\n"
            html += "<th>Machine</th>\n"
            html += "<th>Treatment Date</th>\n"
            html += "<th>Treatment Time</th>\n"
            html += "<th>Region</th>\n"
            html += "<th>CBCT Acquisition Time</th>\n"
            html += "<th>CBCT SOP Instance UID</th>\n"
            html += "</tr>\n</thead>\n<tbody>\n"

            try:
                for index, row in report_df.iterrows():
                    if row['Region'] != 'NaN':
                        html += "<tr>\n"
                        html += "<td>" + str(row['MRN']) + "</td>\n"
                        html += "<td>" + str(row['Study']) + "</td>\n"
                        html += "<td>" + str(row['Plan']) + "</td>\n"
                        html += "<td>" + str(row['Machine']) + "</td>\n"
                        html += "<td>" + str(row['TxDate']) + "</td>\n"
                        html += "<td>" + str(row['TxTime']) + "</td>\n"
                        html += "<td>" + str(row['Region']) + "</td>\n"
                        html += "<td>" + str(row['CBCT_AcquisitionTime']) + "</td>\n"
                        html += "<td>" + str(row['CBCT_SOPInstanceUID']) + "</td>\n"
                        html += "</tr>\n"
            except Exception as exc:
                print(' !!!!! Error trying to add table to report')
                print(exc)

            html += "</tbody>\n</table>\n</body>\n</html>\n"
            print(html)

            try:
                # Write the HTML file
                report_name = report_df['TxDate'].iloc[0] + "_DailyReport.html"
                report_path = os.path.join(info['report_path'], report_name)
                print(report_path)
                report_file = open(report_path, "w")
                report_file.write(html)
                report_file.close()
            except Exception as exc:
                print(' !!!!! Error occurred generating report')
                print(exc)

        try:
            predict_df.to_excel(predict_file, index=False)
        except Exception as exc:
            print(' !!!!! Unable to save updated predict list')
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

    print("Compiling report for " + query_day.strftime('%Y%m%d'))
    send_report(query_day)
