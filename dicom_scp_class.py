from asyncio.windows_events import NULL
import os
from datetime import date
from pydicom import dcmread
from pydicom.dataset import Dataset
from pynetdicom import (AE, evt, debug_logger,
                        StoragePresentationContexts)

# Uncomment to see additional output from DICOM operations
#debug_logger()

#SCP class and handlers
class Retriever_SCP(object):
    def __init__(self, saveLocation, SOURCE_AETITLE, SOURCE_HOST, SOURCE_PORT, CLIENT_AETITLE, CLIENT_HOST, CLIENT_PORT, day):
        self.CLIENT_AE = CLIENT_AETITLE
        self.CLIENT_HO = CLIENT_HOST
        self.CLIENT_PO = int(CLIENT_PORT)
        self.SOURCE_AE = SOURCE_AETITLE
        self.SOURCE_HO = SOURCE_HOST
        self.SOURCE_PO = int(SOURCE_PORT)
        self.saveLocation = saveLocation
        self.is_active = False
        self.query_day = date.fromisoformat(day)
        #print(' --- QUERY DAY --- ' + self.query_day.strftime('%Y-%m-%d'))
        # Create application entity
        self.ae = AE(CLIENT_AETITLE)
        # Set timeouts
        self.ae.acse_timeout = 120
        self.ae.dimse_timeout = 121
        self.ae.network_timeout = 122
        # Unlimited PDU size
        #self.ae.maximum_pdu_size = 0
        # Add presentation contexts with specified transfer syntaxes
        self.ae.supported_contexts = StoragePresentationContexts
        #setup handles
        self.handlers = [(evt.EVT_CONN_OPEN, Retriever_SCP.handle_open),
                         (evt.EVT_ACCEPTED, Retriever_SCP.handle_accepted),
                         (evt.EVT_CONN_CLOSE, Retriever_SCP.handle_close),
                         (evt.EVT_C_STORE, Retriever_SCP.handle_store, [self.saveLocation, self.query_day])]
        print(' ****************  SCP Started  ****************')
        self.scp = self.ae.start_server((self.CLIENT_HO, self.CLIENT_PO), block=False, evt_handlers=self.handlers)
        #self.scp = self.ae.start_server((self.CLIENT_HO, self.CLIENT_PO), evt_handlers=self.handlers)
        self.is_active = True

    def stop(self):
        #self.scp.unbind(evt.EVT_CONN_OPEN, Retriever_SCP.handle_open)
        #self.scp.bind(evt.EVT_CONN_CLOSE, Retriever_SCP.handle_close)
        self.scp.shutdown()
        self.is_active = False
        print(' ****************  SCP Shutdown  ****************')

    def check_status(self):
        return self.is_active
    
    @staticmethod
    def handle_open(event):
        """Print the remote's (host, port) when connected."""
        msg = ' SCP connected with remote at {}'.format(event.address)
        print(msg)

    @staticmethod
    def handle_accepted(event):
        """Demonstrate the use of the optional extra parameters"""
        print(" SCP accepted connection.") # Extra args? : '{}' and '{}'".format(arg1, arg2))

    @staticmethod
    def handle_close(event):
        """Print the remote's (host, port) when disconnected."""
        msg = ' SCP disconnected from remote at {}'.format(event.address)
        print(msg)

    @staticmethod
    # Implement the handler for evt.EVT_C_STORE -- CHECK
    def handle_store(event, tempdir, query_day):
        #print(' ****** SCP C-STORE EVENT TRIGGERED ****** ')
        status_ds = Dataset()
        status_ds.Status = 0x0000

        try:
            # """Handle a C-STORE request event."""
            ds = event.dataset
            ds.file_meta = event.file_meta
        except Exception as exc:
            print(
                "Unable to decode the received dataset or missing 'SOP Class "
                "UID' and/or 'SOP Instance UID' elements"
            )
            print(exc)
            # Unable to decode dataset
            status_ds.Status = 0xC210
            return status_ds

        # Because pydicom uses deferred reads for its decoding, decoding errors
        #   are hidden until encountered by accessing a faulty element
        try:
            sop_class = str(ds.SOPClassUID)
            sop_instance = str(ds.SOPInstanceUID)
            modal = str(ds.Modality)
            seriesuid = str(ds.SeriesInstanceUID)
            studid = str(ds.StudyID)
            pt_path = os.path.join(tempdir, ds.PatientID)
            study_path = os.path.join(tempdir, ds.PatientID, studid) #, seriesuid)
            date_path = os.path.join(tempdir, ds.PatientID, studid, query_day.strftime('%Y-%m-%d'))
            print(sop_class)
        except Exception as exc:
            print(
                "Unable to decode the received dataset or missing 'SOP Class "
                "UID' and/or 'SOP Instance UID' elements"
            )
            print(exc)
            # Unable to decode dataset
            status_ds.Status = 0xC210
            return status_ds

        try:
            os.makedirs(pt_path, exist_ok=True)
            os.makedirs(study_path, exist_ok=True)
            os.makedirs(date_path, exist_ok=True)
        except Exception as exc:
            print('Unable to create the output directory:')
            #print(f"    {date_path}")
            print(exc)
            # Failed - Out of Resources - IOError
            status_ds.Status = 0xA700
            return status_ds
              
        # if image is RTPlan, check if plan is of interest using the list of plans
        # will build a list of approved plans (studyUID and SeriesUID) -- potential candidates
        filename = ''

        if modal == 'RTPLAN':
            #print('\n ****** CHECKING PLAN ****** ')
            # check if plan type match
            try:
                if 'RTPlanLabel' in ds.dir():
                    plan_name = ds.RTPlanLabel
                    print(" SCP >>>>> Found RTPLAN: {} ({} / {})".format(plan_name, ds.PatientID, studid))
                    filename = os.path.join(study_path, 'RTP.' + sop_instance + '.dcm')
                else:
                    # Unable to decode dataset
                    status_ds.Status = 0xC210
                    return status_ds
            except Exception as exc:
                filename = ''
                print('Unable to construct RTP file path')
                print(exc)
                status_ds.Status = 0xC211
                return status_ds

        # if REG file, then get the frame UID to check the RTstruct
        # also get referenced CT and CBCT IDs
        # then save REG files
        elif modal == 'REG':
            #print(' ****** CHECKING REG ****** ')
            # check reg date
            if 'SeriesDate' in ds.dir():
                if ds.SeriesDate == query_day.strftime('%Y%m%d'): 
                    try:
                        filename = os.path.join(date_path, 'REG.' + sop_instance + '.dcm')
                        print(" SCP >>>>> Found REG: ", filename)
                    except Exception as exc:
                        filename = ''
                        print('Unable to construct REG file path')
                        print(exc)
                        status_ds.Status = 0xC211
                        return status_ds
            else:
                # Unable to decode dataset
                status_ds.Status = 0xC210
                return status_ds

        elif (modal == 'CT'):
            #print(' ****** GETTING CT ****** ')
            Manufacturer = ''
            if 'Manufacturer' in ds.dir():
                Manufacturer = ds.Manufacturer
                #print(Manufacturer)
            else:
                # Unable to decode dataset
                status_ds.Status = 0xC210
                return status_ds
            #check if CT or CBCT based on Manufacturer name
            try:
                if "Varian" in Manufacturer:
                    if ds.InstanceNumber == 1:
                        print(" SCP >>>>> Saving ", Manufacturer, " CBCT to daily_cbct_data/", str(ds.PatientID), '/', str(studid))
                    ctpath = os.path.join(date_path,  'CBCT.' + seriesuid)
                    os.makedirs(ctpath, exist_ok=True)
                    filename = os.path.join(ctpath, 'CBCT.' + sop_instance + '.dcm')
                #else it is a planning CT
                else:
                    if ds.InstanceNumber == 1:
                        print(" SCP >>>>> Saving ", Manufacturer, " CT to daily_cbct_data/", str(ds.PatientID), '/', str(studid))
                    ctpath = os.path.join(study_path, 'CT.' + seriesuid)
                    os.makedirs(ctpath, exist_ok=True)
                    filename = os.path.join(ctpath, 'CT.' + sop_instance + '.dcm')
            except Exception as exc:
                filename = ''
                print('Unable to construct CT file path: ', sop_instance)
                print(exc)
                status_ds.Status = 0xC211
                return status_ds
        
        elif (modal == 'RTSTRUCT'):
            #print(' ****** CHECKING RTSTRUCT ****** ')
            try:
                filename = os.path.join(study_path, 'RTS.' + sop_instance + '.dcm')
                print(" SCP >>>>> Found RTSTRUCT: ", filename)
            except Exception as exc:
                filename = ''
                print('Unable to construct RTS file path')
                print(exc)
                status_ds.Status = 0xC211
                return status_ds
        
        elif (modal == 'RTDOSE'):
            #print(' ****** CHECKING RTDOSE ****** ')
            try:
                filename = os.path.join(study_path, 'RTD.' + sop_instance + '.dcm')
                print(" SCP >>>>> Found RTDOSE: ", filename)
            except Exception as exc:
                filename = ''
                print('Unable to construct RTD file path')
                print(exc)
                status_ds.Status = 0xC211
                return status_ds
        
        elif (modal == 'RTRECORD'):
            #print(' ****** CHECKING RTRECORD ****** ')
            try:
                if 'TreatmentDate' in ds.dir():
                    tx_day = ds.TreatmentDate
                    query_day = tx_day[0:4] + "-" + tx_day[4:6] + "-" + tx_day[6:8]
                    date_path = os.path.join(study_path, query_day)
                    os.makedirs(date_path, exist_ok=True)
                    filename = os.path.join(date_path, 'BEAM.' + sop_instance + '.dcm')
                    print(" SCP >>>>> Found RTRECORD: ", filename)
            except Exception as exc:
                filename = ''
                print('Unable to construct RTRECORD file path')
                print(exc)
                status_ds.Status = 0xC211
                return status_ds
        
        elif (modal == 'RTIMAGE'):
            #print(' ****** CHECKING RTIMAGE ****** ')
            try:
                filename = os.path.join(date_path, 'RTI.' + sop_instance + '.dcm')
                print(" SCP >>>>> Found RTIMAGE: ", filename)
            except Exception as exc:
                filename = ''
                print('Unable to construct RTIMAGE file path')
                print(exc)
                status_ds.Status = 0xC211
                return status_ds

        if filename != '':
            if os.path.isfile(filename):
                print('DICOM file already exists...')
                status_ds.Status = 0x0000
                return status_ds

            try:
                #outfile = os.path.join(path, filename)
                ds.save_as(filename, write_like_original=False)
                status_ds.Status = 0x0000  # Success
                return status_ds
            except IOError as exc:
                print('Could not write file to specified directory:')
                print(f"    {os.path.dirname(filename)}")
                print(exc)
                # Failed - Out of Resources - IOError
                status_ds.Status = 0xA700
                return status_ds
            except Exception as exc:
                print('Could not write file to specified directory:')
                print(f"    {os.path.dirname(filename)}")
                print(exc)
                # Failed - Out of Resources - Miscellaneous error
                status_ds.Status = 0xA701
                return status_ds
        else:
            status_ds.Status = 0x0000
            return status_ds
