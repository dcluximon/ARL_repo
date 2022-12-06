import time
from datetime import date, datetime
from pydicom.dataset import Dataset
from pynetdicom import (AE, evt, debug_logger)
from pynetdicom.pdu_primitives import SOPClassExtendedNegotiation
from pynetdicom.sop_class import (Verification,
                                  PatientRootQueryRetrieveInformationModelFind,
                                  StudyRootQueryRetrieveInformationModelFind,
                                  PatientRootQueryRetrieveInformationModelMove,
                                  StudyRootQueryRetrieveInformationModelMove)

# Uncomment to see additional output from DICOM operations - VerificationSOPClass
#debug_logger()

#scu class
class Retriever_SCU(object):
    def __init__(self, SOURCE_AETITLE, SOURCE_HOST, SOURCE_PORT, SELF_AETITLE, SCP_AETITLE):
        self.SOURCE_AETITLE = SOURCE_AETITLE
        self.SOURCE_HOST = SOURCE_HOST
        self.SOURCE_PORT = int(SOURCE_PORT)
        self.SCP_AETITLE = SCP_AETITLE
        self.AETITLE = SELF_AETITLE
        self.result = {}
        # Initialise the Application Entity
        self.ae = AE(SELF_AETITLE)
        # Set timeouts
        self.ae.acse_timeout = 60
        self.ae.dimse_timeout = 61
        self.ae.network_timeout = 62
        # Unlimited PDU size
        #self.ae.maximum_pdu_size = 0
        # Add the requested presentation contexts (Storage SCU)
        self.ae.add_requested_context(Verification)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelMove)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)
        self.query = False
        self.assoc = None

    def launch_echo(self):
        print(" ********************* ASSOCIATE SCU & ECHO ********************* ")
        ext_neg = []
        app_info = b''
        app_info += b'\x01'
        #app_info += b'\x00'
        #app_info += b'\x00'
        #app_info += b'\x00'
        #app_info += b'\x00'
        item1 = SOPClassExtendedNegotiation()
        item1.sop_class_uid = StudyRootQueryRetrieveInformationModelFind
        item1.service_class_application_information = app_info
        item2 = SOPClassExtendedNegotiation()
        item2.sop_class_uid = PatientRootQueryRetrieveInformationModelFind
        item2.service_class_application_information = app_info
        ext_neg = [item1, item2]

        # Associate with peer AE
        self.assoc = self.ae.associate(self.SOURCE_HOST, self.SOURCE_PORT, ae_title=self.SOURCE_AETITLE, ext_neg=ext_neg)

        if self.assoc.is_established:
            # Use the C-ECHO service to send the request
            # returns the response status a pydicom Dataset
            status = self.assoc.send_c_echo()
            self.query = True
            # If the verification request succeeded this will be 0x0000
            #print(' C-ECHO request status: 0x{0:04x}'.format(status.Status))
            if status and status.Status in [0xFE00]:
                print(" ********************* C-ECHO CANCEL ********************* ")
                self.query = False
            elif status and status.Status in [0x0000]:
                print(" ********************* C-ECHO SUCCESS ********************* ")
            elif status and status.Status in [0x0122]:
                print(" ********************* C-ECHO FAILURE - SOP Class Not Supported ********************* ")
                self.query = False
            elif status and status.Status in [0xA700]:
                print(" ********************* C-ECHO FAILURE - Out Of Resources ********************* ")
                self.query = False
            elif status and status.Status in [0xA900]:
                print(" ********************* C-ECHO FAILURE - Identifier Does Not Match SOP Class ********************* ")
                self.query = False
            elif status and status.Status in [0xC000]:
                print(" ********************* C-ECHO FAILURE - Unable To Process ********************* ")
                self.query = False
            elif status and status.Status in [0xC100]:
                print(" ********************* C-ECHO FAILURE - More Than 1 Match Found ********************* ")
                self.query = False
            elif status and status.Status in [0xC200]:
                print(" ********************* C-ECHO FAILURE - Unable To Support Requested Template ********************* ")
                self.query = False
            elif status and status.Status in [0xFF00, 0xFF01]:
                print(" ********************* C-ECHO PENDING - Matches Are Continuing ********************* ")

    def check_status(self):
        while not self.assoc.is_established:
            time.sleep(10)
            self.launch_echo()

    # SCU QUERY
    def find_daily_treatments(self, day):
        #print(" ********************* SCU FIND QUERY ********************* ")
        if self.assoc.is_established:
            if self.query:
                query_day = date.fromisoformat(day)
                print("QUERYING TREATMENTS ON: ", query_day.strftime('%Y%m%d'))
                # go through plans and create dicom tree
                study_query = True
                if study_query:
                    study_ds = Dataset()
                    study_ds.QueryRetrieveLevel = 'IMAGE'
                    #Patient
                    study_ds.PatientID = ''
                    study_ds.PatientName = ''
                    #Study
                    study_ds.StudyID = ''
                    study_ds.StudyInstanceUID = ''
                    study_ds.StudyDate = '' #yesterday.strftime('%Y%m%d') + '-' + today.strftime('%Y%m%d')
                    #Series
                    study_ds.SeriesInstanceUID = ''
                    study_ds.SeriesDescription = ''
                    study_ds.SeriesNumber = ''
                    study_ds.SeriesDate = ''
                    study_ds.Modality = ''
                    #Image
                    study_ds.SOPInstanceUID = ''
                    study_ds.SOPClassUID = []
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.66.1') #REG
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.5') #RTPlan
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.2') #RTDose
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.3') #RTStructureSet 
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.2') #CTImageSTorage
                    study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.4') #RTBeamsTreatmentRecordStorage
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.6') #RTBrachyTreatmentRecordStorage
                    study_ds.TreatmentDate = query_day.strftime('%Y%m%d') + '-' + query_day.strftime('%Y%m%d')
                    study_ds.TreatmentTime = ''
                    study_ds.TreatmentDeliveryType = ''
                    study_ds.TreatmentTerminationStatus = ''
                    study_ds.AcquisitionDate = ''
                    study_ds.ContentDate = ''
                    study_ds.ApprovalStatus = '' # APPROVED
                    #Composite : Referenced RTPlan Sequence
                    study_ds.ReferencedSOPClassUID = ''
                    study_ds.ReferencedSOPInstanceUID = ''
                    #RTPlan
                    study_ds.RTPlanLabel = ''
                    study_ds.RTPlanDate = '' #yesterday.strftime('%Y%m%d')
                    study_ds.RTPlanDescription = ''
                    #RTDose
                    study_ds.DoseSummationType = ''
                    study_ds.CurrentFractionNumber = ''
                    # study_ds.ReferencedFractionGroupNumber = ''
                    study_ds.TreatmentSessionBeamSequence = ''
                    self.result['patients'] = []

                    # PATIENT LEVEL RETRIEVE
                    #print("\n\n ********************* PATIENT LEVEL C-FIND ********************* \n\n")
                    #responses = self.assoc.send_c_find(study_ds, PatientRootQueryRetrieveInformationModelFind)
                    responses = self.assoc.send_c_find(study_ds, StudyRootQueryRetrieveInformationModelFind)
                    counter = 1
                    for (status, identifier) in responses:
                        #if status and status.Status in [0xFF00, 0xFF01]:
                            #print('\n C-FIND query status: 0x{0:04X}\n'.format(status.Status))
                        #print('\nIdentifier: {}\n'.format(identifier))
                        if identifier is not None:
                            ds = Dataset()
                            ds = identifier
                            add_record = True
                            # Use with RT Beams Treatment Record 
                            list_of_patients = [a_dict['ReferencedSOPInstanceUID'] for a_dict in self.result['patients']]
                            # Use with CT Images 
                            #list_of_patients = [a_dict['SeriesInstanceUID'] for a_dict in self.result['patients']]
                            if list_of_patients is not None:
                                if ds.ReferencedSOPInstanceUID in list_of_patients:
                                #if ds.SeriesInstanceUID in list_of_patients:
                                    add_record = False
                            if add_record:
                                # print(ds)
                                pt_obj = {}
                                pt_obj['index'] = counter
                                counter += 1
                                if 'PatientID' in ds.dir():
                                    pt_obj['PatientID'] = ds.PatientID
                                if 'PatientName' in ds.dir():
                                    pt_obj['PatientName'] = ds.PatientName.family_comma_given()
                                if 'StudyID' in ds.dir():
                                    pt_obj['StudyID'] = ds.StudyID
                                if 'StudyDate' in ds.dir():
                                    pt_obj['StudyDate'] = ds.StudyDate
                                if 'StudyInstanceUID' in ds.dir():
                                    pt_obj['StudyInstanceUID'] = ds.StudyInstanceUID
                                if 'Modality' in ds.dir():
                                    pt_obj['Modality'] = ds.Modality
                                if 'SOPClassUID' in ds.dir():
                                    if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.5':
                                        pt_obj['SOPClassUID'] = 'RT Plan'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.2':
                                        pt_obj['SOPClassUID'] = 'RT Dose'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.3':
                                        pt_obj['SOPClassUID'] = 'RT Structure Set'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.66.1':
                                        pt_obj['SOPClassUID'] = 'Registration'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2':
                                        pt_obj['SOPClassUID'] = 'CT Images'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.4':
                                        pt_obj['SOPClassUID'] = 'RT Beams Treatment Record'
                                    else:
                                        pt_obj['SOPClassUID'] = ds.SOPClassUID
                                if 'SeriesInstanceUID' in ds.dir():
                                    pt_obj['SeriesInstanceUID'] = ds.SeriesInstanceUID
                                if 'SeriesDescription' in ds.dir():
                                    pt_obj['SeriesDescription'] = ds.SeriesDescription
                                if 'SeriesDate' in ds.dir():
                                    pt_obj['SeriesDate'] = ds.SeriesDate
                                if 'RTPlanLabel' in ds.dir():
                                    pt_obj['RTPlanLabel'] = ds.RTPlanLabel
                                if 'RTPlanDescription' in ds.dir():
                                    pt_obj['RTPlanDescription'] = ds.RTPlanDescription
                                if 'RTPlanDate' in ds.dir():
                                    pt_obj['RTPlanDate'] = ds.RTPlanDate
                                if 'AcquisitionDate' in ds.dir():
                                    pt_obj['AcquisitionDate'] = ds.AcquisitionDate
                                if 'ContentDate' in ds.dir():
                                    pt_obj['ContentDate'] = ds.ContentDate
                                if 'ReferencedSOPClassUID' in ds.dir():
                                    pt_obj['ReferencedSOPClassUID'] = ds.ReferencedSOPClassUID
                                if 'ReferencedSOPInstanceUID' in ds.dir():
                                    pt_obj['ReferencedSOPInstanceUID'] = ds.ReferencedSOPInstanceUID
                                if 'ApprovalStatus' in ds.dir():
                                    pt_obj['ApprovalStatus'] = ds.ApprovalStatus
                                if 'DoseSummationType' in ds.dir():
                                    pt_obj['DoseSummationType'] = ds.DoseSummationType
                                if 'TreatmentDate' in ds.dir():
                                    pt_obj['TreatmentDate'] = ds.TreatmentDate
                                if 'TreatmentTime' in ds.dir():
                                    pt_obj['TreatmentTime'] = ds.TreatmentTime
                                if 'TreatmentDeliveryType' in ds.dir():
                                    pt_obj['TreatmentDeliveryType'] = ds.TreatmentDeliveryType
                                if 'TreatmentTerminationStatus' in ds.dir():
                                    pt_obj['TreatmentTerminationStatus'] = ds.TreatmentTerminationStatus
                                if 'CurrentFractionNumber' in ds.dir():
                                    pt_obj['CurrentFractionNumber'] = ds.CurrentFractionNumber
                                #if 'ReferencedFractionGroupNumber' in ds.dir():
                                #    pt_obj['ReferencedFractionGroupNumber'] = ds.ReferencedFractionGroupNumber

                                self.result['patients'].append(pt_obj)
                        else:
                            #if 'Status' in status:
                            #    print('\n C-FIND query status: 0x{0:04X}\n'.format(status.Status))
                            print(' Connection timed out, was aborted, received invalid response, or completed.')
                    #print("\n ---------------------------------------- \n")
        else:
            print('Association rejected, aborted or never connected')
        return sorted(self.result['patients'], key=lambda x: x['TreatmentTime'])

    def find_daily_cts(self, day):
        #print(" ********************* SCU FIND QUERY ********************* ")
        if self.assoc.is_established:
            if self.query:
                query_day = date.fromisoformat(day)
                print("QUERYING CTs ON: ", query_day.strftime('%Y%m%d'))
                # go through plans and create dicom tree
                study_query = True
                if study_query:
                    study_ds = Dataset()
                    study_ds.QueryRetrieveLevel = 'IMAGE'
                    #Patient
                    study_ds.PatientID = ''
                    study_ds.PatientName = ''
                    #Study
                    study_ds.StudyID = ''
                    study_ds.StudyInstanceUID = ''
                    study_ds.StudyDate = '' #yesterday.strftime('%Y%m%d') + '-' + today.strftime('%Y%m%d')
                    #Series
                    study_ds.SeriesInstanceUID = ''
                    study_ds.SeriesDescription = ''
                    study_ds.SeriesNumber = ''
                    study_ds.SeriesDate = ''
                    study_ds.Modality = ''
                    #Image
                    study_ds.SOPInstanceUID = ''
                    study_ds.SOPClassUID = []
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.66.1') #REG
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.5') #RTPlan
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.2') #RTDose
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.3') #RTStructureSet 
                    study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.2') #CTImageSTorage
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.4') #RTBeamsTreatmentRecordStorage
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.6') #RTBrachyTreatmentRecordStorage
                    study_ds.TreatmentDate = ''
                    study_ds.TreatmentTime = ''
                    study_ds.TreatmentDeliveryType = ''
                    study_ds.TreatmentTerminationStatus = ''
                    study_ds.AcquisitionDate = query_day.strftime('%Y%m%d') + '-' + query_day.strftime('%Y%m%d')
                    study_ds.ContentDate = ''
                    study_ds.ApprovalStatus = '' # APPROVED
                    #Composite : Referenced RTPlan Sequence
                    study_ds.ReferencedSOPClassUID = ''
                    study_ds.ReferencedSOPInstanceUID = ''
                    #RTPlan
                    study_ds.RTPlanLabel = ''
                    study_ds.RTPlanDate = '' #yesterday.strftime('%Y%m%d')
                    study_ds.RTPlanDescription = ''
                    #RTDose
                    study_ds.DoseSummationType = ''
                    study_ds.CurrentFractionNumber = ''
                    # study_ds.ReferencedFractionGroupNumber = ''
                    study_ds.TreatmentSessionBeamSequence = ''
                    self.result['patients'] = []

                    # PATIENT LEVEL RETRIEVE
                    #print("\n\n ********************* PATIENT LEVEL C-FIND ********************* \n\n")
                    #responses = self.assoc.send_c_find(study_ds, PatientRootQueryRetrieveInformationModelFind)
                    responses = self.assoc.send_c_find(study_ds, StudyRootQueryRetrieveInformationModelFind)
                    counter = 1
                    for (status, identifier) in responses:
                        #if status and status.Status in [0xFF00, 0xFF01]:
                            #print('\n C-FIND query status: 0x{0:04X}\n'.format(status.Status))
                        #print('\nIdentifier: {}\n'.format(identifier))
                        if identifier is not None:
                            ds = Dataset()
                            ds = identifier
                            add_record = True
                            # Use with RT Beams Treatment Record 
                            #list_of_patients = [a_dict['ReferencedSOPInstanceUID'] for a_dict in self.result['patients']]
                            # Use with CT Images 
                            list_of_patients = [a_dict['SeriesInstanceUID'] for a_dict in self.result['patients']]
                            if list_of_patients is not None:
                                #if ds.ReferencedSOPInstanceUID in list_of_patients:
                                if ds.SeriesInstanceUID in list_of_patients:
                                    add_record = False
                            if add_record:
                                # print(ds)
                                pt_obj = {}
                                pt_obj['index'] = counter
                                counter += 1
                                if 'PatientID' in ds.dir():
                                    pt_obj['PatientID'] = ds.PatientID
                                if 'PatientName' in ds.dir():
                                    pt_obj['PatientName'] = ds.PatientName.family_comma_given()
                                if 'StudyID' in ds.dir():
                                    pt_obj['StudyID'] = ds.StudyID
                                if 'StudyDate' in ds.dir():
                                    pt_obj['StudyDate'] = ds.StudyDate
                                if 'StudyInstanceUID' in ds.dir():
                                    pt_obj['StudyInstanceUID'] = ds.StudyInstanceUID
                                if 'Modality' in ds.dir():
                                    pt_obj['Modality'] = ds.Modality
                                if 'SOPClassUID' in ds.dir():
                                    if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.5':
                                        pt_obj['SOPClassUID'] = 'RT Plan'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.2':
                                        pt_obj['SOPClassUID'] = 'RT Dose'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.3':
                                        pt_obj['SOPClassUID'] = 'RT Structure Set'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.66.1':
                                        pt_obj['SOPClassUID'] = 'Registration'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2':
                                        pt_obj['SOPClassUID'] = 'CT Images'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.4':
                                        pt_obj['SOPClassUID'] = 'RT Beams Treatment Record'
                                    else:
                                        pt_obj['SOPClassUID'] = ds.SOPClassUID
                                if 'SeriesInstanceUID' in ds.dir():
                                    pt_obj['SeriesInstanceUID'] = ds.SeriesInstanceUID
                                if 'SeriesDescription' in ds.dir():
                                    pt_obj['SeriesDescription'] = ds.SeriesDescription
                                if 'SeriesDate' in ds.dir():
                                    pt_obj['SeriesDate'] = ds.SeriesDate
                                if 'RTPlanLabel' in ds.dir():
                                    pt_obj['RTPlanLabel'] = ds.RTPlanLabel
                                if 'RTPlanDescription' in ds.dir():
                                    pt_obj['RTPlanDescription'] = ds.RTPlanDescription
                                if 'RTPlanDate' in ds.dir():
                                    pt_obj['RTPlanDate'] = ds.RTPlanDate
                                if 'AcquisitionDate' in ds.dir():
                                    pt_obj['AcquisitionDate'] = ds.AcquisitionDate
                                if 'ContentDate' in ds.dir():
                                    pt_obj['ContentDate'] = ds.ContentDate
                                if 'ReferencedSOPClassUID' in ds.dir():
                                    pt_obj['ReferencedSOPClassUID'] = ds.ReferencedSOPClassUID
                                if 'ReferencedSOPInstanceUID' in ds.dir():
                                    pt_obj['ReferencedSOPInstanceUID'] = ds.ReferencedSOPInstanceUID
                                if 'ApprovalStatus' in ds.dir():
                                    pt_obj['ApprovalStatus'] = ds.ApprovalStatus
                                if 'DoseSummationType' in ds.dir():
                                    pt_obj['DoseSummationType'] = ds.DoseSummationType
                                if 'TreatmentDate' in ds.dir():
                                    pt_obj['TreatmentDate'] = ds.TreatmentDate
                                if 'TreatmentTime' in ds.dir():
                                    pt_obj['TreatmentTime'] = ds.TreatmentTime
                                if 'TreatmentDeliveryType' in ds.dir():
                                    pt_obj['TreatmentDeliveryType'] = ds.TreatmentDeliveryType
                                if 'TreatmentTerminationStatus' in ds.dir():
                                    pt_obj['TreatmentTerminationStatus'] = ds.TreatmentTerminationStatus
                                if 'CurrentFractionNumber' in ds.dir():
                                    pt_obj['CurrentFractionNumber'] = ds.CurrentFractionNumber
                                #if 'ReferencedFractionGroupNumber' in ds.dir():
                                #    pt_obj['ReferencedFractionGroupNumber'] = ds.ReferencedFractionGroupNumber

                                self.result['patients'].append(pt_obj)
                        else:
                            #if 'Status' in status:
                             #   print('\n C-FIND query status: 0x{0:04X}\n'.format(status.Status))
                            print(' Connection timed out, was aborted, received invalid response, or completed.')
                    #print("\n ---------------------------------------- \n")
        else:
            print('Association rejected, aborted or never connected')
        return sorted(self.result['patients'], key=lambda x: x['PatientID'])

    def find_daily_rtimages(self, day):
        #print(" ********************* SCU FIND QUERY ********************* ")
        if self.assoc.is_established:
            if self.query:
                query_day = date.fromisoformat(day)
                print("QUERYING RTIMAGEs ON: ", query_day.strftime('%Y%m%d'))
                # go through plans and create dicom tree
                study_query = True
                if study_query:
                    study_ds = Dataset()
                    study_ds.QueryRetrieveLevel = 'IMAGE'
                    #Patient
                    study_ds.PatientID = ''
                    study_ds.PatientName = ''
                    #Study
                    study_ds.StudyID = ''
                    study_ds.StudyInstanceUID = ''
                    study_ds.StudyDate = '' #yesterday.strftime('%Y%m%d') + '-' + today.strftime('%Y%m%d')
                    #Series
                    study_ds.SeriesInstanceUID = ''
                    study_ds.SeriesDescription = ''
                    study_ds.SeriesNumber = ''
                    study_ds.SeriesDate = ''
                    study_ds.Modality = ''
                    #Image
                    study_ds.SOPInstanceUID = ''
                    study_ds.SOPClassUID = []
                    study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.1') #RTImageStorage
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.66.1') #REG
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.5') #RTPlan
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.2') #RTDose
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.3') #RTStructureSet 
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.2') #CTImageSTorage
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.4') #RTBeamsTreatmentRecordStorage
                    #study_ds.SOPClassUID.append('1.2.840.10008.5.1.4.1.1.481.6') #RTBrachyTreatmentRecordStorage
                    study_ds.TreatmentDate = ''
                    study_ds.TreatmentTime = ''
                    study_ds.TreatmentDeliveryType = ''
                    study_ds.TreatmentTerminationStatus = ''
                    study_ds.AcquisitionDate = query_day.strftime('%Y%m%d') + '-' + query_day.strftime('%Y%m%d')
                    study_ds.ContentDate = ''
                    study_ds.ApprovalStatus = '' # APPROVED
                    #Composite : Referenced RTPlan Sequence
                    study_ds.ReferencedSOPClassUID = ''
                    study_ds.ReferencedSOPInstanceUID = ''
                    #RTPlan
                    study_ds.RTPlanLabel = ''
                    study_ds.RTPlanDate = '' #yesterday.strftime('%Y%m%d')
                    study_ds.RTPlanDescription = ''
                    #RTDose
                    study_ds.DoseSummationType = ''
                    study_ds.CurrentFractionNumber = ''
                    # study_ds.ReferencedFractionGroupNumber = ''
                    study_ds.TreatmentSessionBeamSequence = ''
                    self.result['patients'] = []

                    # PATIENT LEVEL RETRIEVE
                    #print("\n\n ********************* PATIENT LEVEL C-FIND ********************* \n\n")
                    #responses = self.assoc.send_c_find(study_ds, PatientRootQueryRetrieveInformationModelFind)
                    responses = self.assoc.send_c_find(study_ds, StudyRootQueryRetrieveInformationModelFind)
                    counter = 1
                    for (status, identifier) in responses:
                        #if status and status.Status in [0xFF00, 0xFF01]:
                            #print('\n C-FIND query status: 0x{0:04X}\n'.format(status.Status))
                        #print('\nIdentifier: {}\n'.format(identifier))
                        if identifier is not None:
                            ds = Dataset()
                            ds = identifier
                            add_record = True
                            # Use with RT Beams Treatment Record 
                            #list_of_patients = [a_dict['ReferencedSOPInstanceUID'] for a_dict in self.result['patients']]
                            # Use with CT Images 
                            list_of_patients = [a_dict['SeriesInstanceUID'] for a_dict in self.result['patients']]
                            if list_of_patients is not None:
                                #if ds.ReferencedSOPInstanceUID in list_of_patients:
                                if ds.SeriesInstanceUID in list_of_patients:
                                    add_record = False
                            if add_record:
                                # print(ds)
                                pt_obj = {}
                                pt_obj['index'] = counter
                                counter += 1
                                if 'PatientID' in ds.dir():
                                    pt_obj['PatientID'] = ds.PatientID
                                if 'PatientName' in ds.dir():
                                    pt_obj['PatientName'] = ds.PatientName.family_comma_given()
                                if 'StudyID' in ds.dir():
                                    pt_obj['StudyID'] = ds.StudyID
                                if 'StudyDate' in ds.dir():
                                    pt_obj['StudyDate'] = ds.StudyDate
                                if 'StudyInstanceUID' in ds.dir():
                                    pt_obj['StudyInstanceUID'] = ds.StudyInstanceUID
                                if 'Modality' in ds.dir():
                                    pt_obj['Modality'] = ds.Modality
                                if 'SOPClassUID' in ds.dir():
                                    if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.5':
                                        pt_obj['SOPClassUID'] = 'RT Plan'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.2':
                                        pt_obj['SOPClassUID'] = 'RT Dose'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.3':
                                        pt_obj['SOPClassUID'] = 'RT Structure Set'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.66.1':
                                        pt_obj['SOPClassUID'] = 'Registration'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2':
                                        pt_obj['SOPClassUID'] = 'CT Images'
                                    elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.4':
                                        pt_obj['SOPClassUID'] = 'RT Beams Treatment Record'
                                    else:
                                        pt_obj['SOPClassUID'] = ds.SOPClassUID
                                if 'SeriesInstanceUID' in ds.dir():
                                    pt_obj['SeriesInstanceUID'] = ds.SeriesInstanceUID
                                if 'SeriesDescription' in ds.dir():
                                    pt_obj['SeriesDescription'] = ds.SeriesDescription
                                if 'SeriesDate' in ds.dir():
                                    pt_obj['SeriesDate'] = ds.SeriesDate
                                if 'RTPlanLabel' in ds.dir():
                                    pt_obj['RTPlanLabel'] = ds.RTPlanLabel
                                if 'RTPlanDescription' in ds.dir():
                                    pt_obj['RTPlanDescription'] = ds.RTPlanDescription
                                if 'RTPlanDate' in ds.dir():
                                    pt_obj['RTPlanDate'] = ds.RTPlanDate
                                if 'AcquisitionDate' in ds.dir():
                                    pt_obj['AcquisitionDate'] = ds.AcquisitionDate
                                if 'ContentDate' in ds.dir():
                                    pt_obj['ContentDate'] = ds.ContentDate
                                if 'ReferencedSOPClassUID' in ds.dir():
                                    pt_obj['ReferencedSOPClassUID'] = ds.ReferencedSOPClassUID
                                if 'ReferencedSOPInstanceUID' in ds.dir():
                                    pt_obj['ReferencedSOPInstanceUID'] = ds.ReferencedSOPInstanceUID
                                if 'ApprovalStatus' in ds.dir():
                                    pt_obj['ApprovalStatus'] = ds.ApprovalStatus
                                if 'DoseSummationType' in ds.dir():
                                    pt_obj['DoseSummationType'] = ds.DoseSummationType
                                if 'TreatmentDate' in ds.dir():
                                    pt_obj['TreatmentDate'] = ds.TreatmentDate
                                if 'TreatmentTime' in ds.dir():
                                    pt_obj['TreatmentTime'] = ds.TreatmentTime
                                if 'TreatmentDeliveryType' in ds.dir():
                                    pt_obj['TreatmentDeliveryType'] = ds.TreatmentDeliveryType
                                if 'TreatmentTerminationStatus' in ds.dir():
                                    pt_obj['TreatmentTerminationStatus'] = ds.TreatmentTerminationStatus
                                if 'CurrentFractionNumber' in ds.dir():
                                    pt_obj['CurrentFractionNumber'] = ds.CurrentFractionNumber
                                #if 'ReferencedFractionGroupNumber' in ds.dir():
                                #    pt_obj['ReferencedFractionGroupNumber'] = ds.ReferencedFractionGroupNumber

                                self.result['patients'].append(pt_obj)
                        else:
                            #if 'Status' in status:
                            #    print('\n C-FIND query status: 0x{0:04X}\n'.format(status.Status))
                            print(' Connection timed out, was aborted, received invalid response, or completed.')
                    #print("\n ---------------------------------------- \n")
                # GET PLAN INFORMATION
                # plan_query = True
                # if plan_query:
                #    plan_ds = Dataset()
                #    plan_ds.QueryRetrieveLevel = 'IMAGE'
        else:
            print('Association rejected, aborted or never connected')
        return sorted(self.result['patients'], key=lambda x: x['PatientID'])

    def release(self):
        # Release the association
        self.assoc.release()
        print(" ********************* SCU RELEASE ASSOCIATION ********************* ")

    def shutdown(self):
        #shutdown scu
        self.ae.shutdown()
        print(" ********************* SCU SHUTDOWN ********************* ")

    # SCU TRANSFER
    def retrieve_reg(self, mrn):
        #print(" ********************* ASSOCIATE SCU ********************* ")
        if self.assoc.is_established:
            if self.query:
                temp_ds = Dataset()
                temp_ds.PatientID = str(mrn)
                temp_ds.QueryRetrieveLevel = 'SERIES'
                temp_ds.StudyInstanceUID = ''
                temp_ds.SeriesInstanceUID = ''
                temp_ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.66.1' #REG
                #print(temp_ds)
                print(" SCU >>>>> Retrieving REG for Patient: ", str(mrn))
                
                # SERIES LEVEL RETRIEVE
                #print(" ********************* SERIES LEVEL C-MOVE ********************* ")
                responses = self.assoc.send_c_move(temp_ds, self.SCP_AETITLE, StudyRootQueryRetrieveInformationModelMove)
                for (status, identifier) in responses:
                    if status:
                        print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
                    else:
                        print('Connection timed out, was aborted or received invalid response')
        else:
            print('Association rejected, aborted or never connected')

    def retrieve_plan(self, mrn, study_uid, sop_uid):
        #print(" ********************* ASSOCIATE SCU ********************* ")
        if self.assoc.is_established:
            if self.query:
                temp_ds = Dataset()
                temp_ds.PatientID = str(mrn)
                temp_ds.QueryRetrieveLevel = 'SERIES'
                temp_ds.StudyInstanceUID = str(study_uid)
                temp_ds.SOPInstanceUID = str(sop_uid)
                temp_ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.5'
                print(" SCU >>>>> Retrieving RTPLAN for Patient: ", str(mrn))
                #print(temp_ds)
                
                # SERIES LEVEL RETRIEVE
                #print("\n\n ********************* SERIES LEVEL C-MOVE ********************* \n\n")
                responses = self.assoc.send_c_move(temp_ds, self.SCP_AETITLE, StudyRootQueryRetrieveInformationModelMove)
                for (status, identifier) in responses:
                    if status:
                        print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
                    else:
                        print('Connection timed out, was aborted or received invalid response')
        else:
            print('Association rejected, aborted or never connected')

    def retrieve_struct(self, mrn, study_uid, sop_uid):
        #print(" ********************* ASSOCIATE SCU ********************* ")
        if self.assoc.is_established:
            if self.query:
                temp_ds = Dataset()
                temp_ds.PatientID = str(mrn)
                temp_ds.QueryRetrieveLevel = 'SERIES'
                temp_ds.StudyInstanceUID = str(study_uid)
                temp_ds.SOPInstanceUID = str(sop_uid)
                temp_ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'
                print(" SCU >>>>> Retrieving RTSTRUCT for Patient: ", str(mrn))
                #print(temp_ds)
                
                # SERIES LEVEL RETRIEVE
                #print("\n\n ********************* SERIES LEVEL C-MOVE ********************* \n\n")
                responses = self.assoc.send_c_move(temp_ds, self.SCP_AETITLE, StudyRootQueryRetrieveInformationModelMove)
                for (status, identifier) in responses:
                    if status:
                        print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
                    else:
                        print('Connection timed out, was aborted or received invalid response')
        else:
            print('Association rejected, aborted or never connected')

    def retrieve_dose(self, mrn, study_uid, sop_uid):
        #print(" ********************* ASSOCIATE SCU ********************* ")
        if self.assoc.is_established:
            if self.query:
                temp_ds = Dataset()
                temp_ds.PatientID = str(mrn)
                temp_ds.QueryRetrieveLevel = 'SERIES'
                temp_ds.StudyInstanceUID = str(study_uid)
                temp_ds.SOPInstanceUID = str(sop_uid)
                temp_ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
                print(" SCU >>>>> Retrieving RTDOSE for Patient: ", str(mrn))
                #print(temp_ds)
                
                # SERIES LEVEL RETRIEVE
                #print("\n\n ********************* SERIES LEVEL C-MOVE ********************* \n\n")
                responses = self.assoc.send_c_move(temp_ds, self.SCP_AETITLE, StudyRootQueryRetrieveInformationModelMove)
                for (status, identifier) in responses:
                    if status:
                        print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
                    else:
                        print('Connection timed out, was aborted or received invalid response')
        else:
            print('Association rejected, aborted or never connected')

    def retrieve_ct(self, mrn, study_uid, sop_uid):
        #print(" ********************* ASSOCIATE SCU ********************* ")
        if self.assoc.is_established:
            if self.query:
                temp_ds = Dataset()
                temp_ds.PatientID = str(mrn)
                temp_ds.QueryRetrieveLevel = 'IMAGE'
                temp_ds.StudyInstanceUID = str(study_uid)
                temp_ds.SeriesInstanceUID = str(sop_uid)
                temp_ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.2'
                print(" SCU >>>>> Retrieving CT for Patient: ", str(mrn))
                #print(temp_ds)
                
                # SERIES LEVEL RETRIEVE
                #print("\n\n ********************* IMAGE LEVEL C-MOVE ********************* \n\n")
                responses = self.assoc.send_c_move(temp_ds, self.SCP_AETITLE, StudyRootQueryRetrieveInformationModelMove)
                for (status, identifier) in responses:
                    if status:
                        print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
                    else:
                        print('Connection timed out, was aborted or received invalid response')
        else:
            print('Association rejected, aborted or never connected')

    def retrieve_rtrecords(self, mrn, study_uid, series_uid, day):
        #print(" ********************* SCU FIND QUERY ********************* ")
        if self.assoc.is_established:
            if self.query:
                query_day = date.fromisoformat(day)
                temp_ds = Dataset()
                temp_ds.QueryRetrieveLevel = 'IMAGE'
                temp_ds.PatientID = str(mrn)
                temp_ds.StudyInstanceUID = str(study_uid)
                temp_ds.SeriesInstanceUID = str(series_uid)
                temp_ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.4' #RTBeamsTreatmentRecordStorage
                temp_ds.TreatmentDate = query_day.strftime('%Y%m%d') + '-' + query_day.strftime('%Y%m%d')
                print(" SCU >>>>> Retrieving RTRECORDS for Patient: ", str(mrn))
                #print(temp_ds)
                
                # SERIES LEVEL RETRIEVE
                #print("\n\n ********************* IMAGE LEVEL C-MOVE ********************* \n\n")
                responses = self.assoc.send_c_move(temp_ds, self.SCP_AETITLE, StudyRootQueryRetrieveInformationModelMove)
                for (status, identifier) in responses:
                    if status:
                        print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
                    else:
                        print('Connection timed out, was aborted or received invalid response')
        else:
            print('Association rejected, aborted or never connected')
