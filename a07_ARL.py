import os
import json
import pandas as pd
import numpy as np
import pydicom
import datetime
from CBCT_AI.losses import *
from tensorflow import keras as k
from CBCT_AI.Data_preprocessing_v2 import process_raw_patient_data
from CBCT_AI.Dense_Net_Region import Dense_Net_AnatomyLabel
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import cv2

np.set_printoptions(threshold=sys.maxsize)

def process_GradCAM(model, Cor_input):
    cor_layer = 'conv2d_35'
    cor_shape = (5,25)


    with tf.GradientTape() as tape:
        last_cor_conv_layer = model.get_layer(cor_layer)

        iterate_cor = tf.keras.models.Model([model.inputs], [model.output, last_cor_conv_layer.output])
        model_out_cor, last_cor_conv_layer = iterate_cor((Cor_input))
        class_out_cor = model_out_cor[:, np.argmax(model_out_cor[0])]
        cor_grads = tape.gradient(class_out_cor, last_cor_conv_layer)
        #print('Ax_grad_shape: ', ax_grads.shape)
        pooled_grads_cor = k.backend.mean(cor_grads, axis = (1,2))

    #Axial
    heatmap_cor = tf.reduce_mean(tf.multiply(pooled_grads_cor, last_cor_conv_layer), axis=-1)
    heatmap_cor = np.maximum(heatmap_cor, 0)
    heatmap_cor /= np.max(heatmap_cor)
    #print(heatmap_ax.shape)
    heatmap_cor = heatmap_cor.reshape(cor_shape)

    return heatmap_cor

def launch_algorithm(data_info, ARL_model):

    #print("Processing raw images")
    print(data_info)
    #print(cord_extraction_model)

    #dictionary for outputs
    outputs = {
        "Region_Label": None,
        "Region_Scores": None
    }

    #process raw data to get planes (the region prediction points to the preprocessing method(s))
    Region_Prediction, ARL_input = process_raw_patient_data(data_info, ARL_model)
    #print(str(Region_Prediction))

    outputs["Region_Scores"] = Region_Prediction

    #index of region with highest probability [HN, PL, TH]
    Region_Label_Index = np.argmax(Region_Prediction)

    try:
        heatmap_cor = process_GradCAM(ARL_model, ARL_input)
    except:
        print('Error producing activation heatmaps')
        heatmap_cor = [0]

    if Region_Label_Index == 0:
        outputs["Region_Label"] = 'HN'

    elif Region_Label_Index == 1:
        outputs["Region_Label"] = 'PL'

    elif Region_Label_Index == 2:
        outputs["Region_Label"] = 'TH'

    elif Region_Label_Index == 3:
        outputs["Region_Label"] = 'EX'

    #print(outputs)
    return outputs, ARL_input, heatmap_cor

def main(day):
    #do the error check
    infofile = "setup_information.json"
    f = open(infofile)
    info = json.load(f)
    f.close()

    ##build Anaromy Region Label (ARL)
    ARL_input_size = (150,400,1)
    ARL_model = Dense_Net_AnatomyLabel(ARL_input_size)
    ARL_model.build(((1,150,400,1)))
    cwd = os.getcwd()
    ARL_weights = os.path.join(cwd, info['arl_model'])
    print(' >>> Loading ARL model: ', info['arl_model'])
    ARL_model.load_weights(ARL_weights)

    predict_file = os.path.join(info['archive_path'], day.strftime('%Y-%m-%d'), day.strftime('%Y-%m-%d') + "_predict_list.xlsx")

    if os.path.isfile(predict_file):
        predict_df = pd.read_excel(predict_file, dtype = str)

        if len(predict_df['index_x']) > 0:
            predict_df['Region'] = ""
            predict_df['EX_Classification'] = ""
            predict_df['TH_Classification'] = ""
            predict_df['PL_Classification'] = ""
            predict_df['HN_Classification'] = ""
            predict_df['AcquisitionTime'] = ""
            predict_df['Machine'] = ""
            predict_df['ARL_Model'] = ""

            for i in range (0, predict_df['index_x'].count()):
                print("Analyzing " + predict_df.iloc[i]['PatientID'] + ' / ' + predict_df.iloc[i]['StudyID'] + " / " + predict_df.iloc[i]['RTPlanLabel'] + ' ...')
                entry = {
                    "root": os.path.join(info['dicom_path'], predict_df.iloc[i]['PatientID'], predict_df.iloc[i]['StudyID']),
                    "datepath": os.path.join(info['dicom_path'], predict_df.iloc[i]['PatientID'], predict_df.iloc[i]['StudyID'], day.strftime('%Y-%m-%d')),
                    "ptid": predict_df.iloc[i]['PatientID'],
                    "studyid": predict_df.iloc[i]['StudyID'],
                    "regfile": "REG." + predict_df.iloc[i]['REG_SOPInstanceUID'] + ".dcm",
                    "planfile": "RTP." + predict_df.iloc[i]['RTPLAN_SOPInstanceUID'] + ".dcm",
                    "structfile": "RTS." + predict_df.iloc[i]['RTSTRUCT_SOPInstanceUID'] + ".dcm",
                    "cbct_dir": "CBCT." + predict_df.iloc[i]['CBCT_SOPInstanceUID'],
                    "simct_dir": "CT." + predict_df.iloc[i]['SIMCT_SOPInstanceUID'],
                }

                ct_exists = os.path.isdir( os.path.join(entry['root'], entry['simct_dir']) )
                cbct_exists = os.path.isdir( os.path.join(entry['datepath'], entry['cbct_dir']) )

                analyze = True

                try:
                    if ct_exists and cbct_exists:
                        flist = os.listdir( os.path.join(entry['datepath'], entry['cbct_dir']) )

                        if len(flist)>0:
                            image0file = os.path.join( os.path.join(entry['datepath'], entry['cbct_dir']), flist[0])
                            image0 = pydicom.dcmread(image0file)

                        else:
                            print('!!!!!Dicom files absent from folder!!!!!')

                        if 'AcquisitionTime' in image0.dir():
                            predict_df.at[i,'AcquisitionTime'] = image0.AcquisitionTime
                        if 'StationName' in image0.dir():
                            predict_df.at[i,'Machine'] = image0.StationName

                        try:
                            ref_rtplan_sop_uid = image0.ReferencedInstanceSequence[0].ReferencedSOPInstanceUID
                            analyze = (ref_rtplan_sop_uid == predict_df.iloc[i]['RTPLAN_SOPInstanceUID'])
                        except:
                            ref_rtplan_stuID_uid = image0.StudyInstanceUID
                            analyze = (ref_rtplan_stuID_uid == predict_df.iloc[i]['StudyInstanceUID'])

                        if analyze:
                            try:
                                outputs, ARL_input, heatmap_cor = launch_algorithm(entry, ARL_model)

                                predict_df.at[i,'Region'] = outputs['Region_Label']
                                predict_df.at[i,'ARL_Model'] = info['arl_model']
                                predict_df.at[i,'EX_Classification'] = outputs['Region_Scores'][3]
                                predict_df.at[i,'TH_Classification'] = outputs['Region_Scores'][2]
                                predict_df.at[i,'PL_Classification'] = outputs['Region_Scores'][1]
                                predict_df.at[i,'HN_Classification'] = outputs['Region_Scores'][0]

                                # save images in entry.datepath
                                try:
                                    cor_cbct = str(i) + "_cbct-coronal.npy"
                                    cor_cbct_file = os.path.join(entry['datepath'], cor_cbct)
                                    np.save(cor_cbct_file, ARL_input)


                                    cor_heatmap = str(i) + "_heatmap-coronal.npy"
                                    cor_heatmap_file = os.path.join(entry['datepath'], cor_heatmap)
                                    np.save(cor_heatmap_file, heatmap_cor)

                                    predict_df.at[i,'cor_cbct_image'] = cor_cbct
                                    predict_df.at[i,'cor_heatmap_image'] = cor_heatmap
                                except:
                                    print(' !!!!! Unable to save slice arrays for patient / study / plan: ' + entry['ptid'] + ' / ' + entry['studyid'] + ' / ' + predict_df.iloc[i]['RTPlanLabel'])

                                print("REGION: ", outputs['Region_Label'])
                                print("CLASSIFIER [HN, PL, TH]: ", outputs['Region_Scores'])

                            except Exception as exc:
                               predict_df.at[i,'Region'] = -1
                               print(' !!!!! Error occurred during prediction analysis for patient / study / plan: ' + entry['ptid'] + ' / ' + entry['studyid'] + ' / ' + predict_df.iloc[i]['RTPlanLabel'])
                               print(exc)
                        else:
                            predict_df.at[i,'Region'] = -2
                            print(' !!!!! CBCT mismatch for patient / study / plan: ' + entry['ptid'] + ' / ' + entry['studyid'] + ' / ' + predict_df.iloc[i]['RTPlanLabel'])
                    else:
                        predict_df.at[i,'Region'] = -3
                        print(' !!!!! No DICOM imaging data available for patient / study / plan: ' + entry['ptid'] + ' / ' + entry['studyid'] + ' / ' + predict_df.iloc[i]['RTPlanLabel'])
                except:
                    print('!!!!!Error in Prediction!!!!!')

            try:
                predict_df.to_excel(predict_file, index=False)
            except Exception as exc:
                print(' !!!!! Unable to save updated predict list')
                print(exc)

if __name__ == "__main__":
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

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

    print('Analyzing image from ' + query_day.strftime('%Y-%m-%d'))
    main(query_day)
