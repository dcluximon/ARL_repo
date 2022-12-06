import pydicom
import SimpleITK as sitk
import sys
import numpy as np
import cv2
import matplotlib.pyplot as plt
import os
import scipy.stats as sci
import pickle
from tqdm import tqdm


def read_sitk(data_directory, CT_type):
    # Read the original series. First obtain the reg file directory, then series file names using the
    # image series reader.
    files = []
    for fname in os.listdir(data_directory):
        if (CT_type == "CT"):
            fdir = os.path.join(data_directory, fname)
            files.append(pydicom.dcmread(fdir))

    # skip files with no SliceLocation (eg scout views)
    slices = []
    sorted_uid = []
    skipcount = 0

    if (CT_type == "CT"):
        for f in files:
            if hasattr(f, 'SliceLocation'):
                # print(f)
                slices.append(f)
            else:
                skipcount = skipcount + 1

        slices = sorted(slices, key=lambda s: s.SliceLocation)
        for i, s in enumerate(slices):
            uid = s.SOPInstanceUID
            sorted_uid.append(uid)

        # sorted_uid = sorted_uid[::-1]

    # get image data
    series_IDs = sitk.ImageSeriesReader.GetGDCMSeriesIDs(data_directory)

    if not series_IDs:
        print("ERROR: given directory \"" + data_directory +
              "\" does not contain a DICOM series.")
        sys.exit(1)

    series_file_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(
        data_directory, series_IDs[0])

    series_reader = sitk.ImageSeriesReader()
    series_reader.SetFileNames(series_file_names)

    #print(series_file_names)

    # Configure the reader to load all of the DICOM tags (public+private):
    # By default tags are not loaded (saves time).
    # By default if tags are loaded, the private tags are not loaded.
    # We explicitly configure the reader to load tags, including the
    # private ones.
    series_reader.MetaDataDictionaryArrayUpdateOn()
    series_reader.LoadPrivateTagsOn()
    image3D = series_reader.Execute()

    return image3D, sorted_uid


def find_limits(cbct):
    # to find extent of cbct
    # plt.imshow(cbct, cmap='gray')
    # plt.show()
    cbct_u8 = cbct.astype('uint8')
    rows_mean = np.mean(cbct_u8, axis=1)
    min_val = np.min(rows_mean)+1
    first_slice_found = 0
    last_slice_index = None
    first_slice_index = None
    for i in range(rows_mean.shape[0]):
        if (first_slice_found == 0) & (rows_mean[i] > min_val):
            first_slice_index = i
            first_slice_found = 1

        if (first_slice_found == 1):
            if (rows_mean[i] <= min_val) & ((i-first_slice_index) > 20):
                last_slice_index = i
                break

        if last_slice_index == None:
            last_slice_index = rows_mean.shape[0]

        if first_slice_index == None:
            first_slice_index = 0


    return first_slice_index, last_slice_index


def get_body_mask(rs_dir, ct_vol, ct_origin, ct_spacing, sorted_uid_list):
    try:
        # get body and cord masks
        body_cntrnames_check = ['body', 'skin', 'outer']
        # read rtstruct file
        rs_file = pydicom.read_file(rs_dir)
        contours = rs_file.StructureSetROISequence
        for attribute in contours:
            if hasattr(attribute, "ROIName"):
                # print(attribute.ROIName)
                if any(map((attribute.ROIName).lower().__contains__, body_cntrnames_check)):
                    Body_ROInumber = attribute.ROINumber
                    # print(attribute.ROIName)
                    # print(attribute.ROINumber)
                    break

        # go find sequence index from ROINumber
        body_contour_ref = rs_file.ROIContourSequence
        body_idx_count = 0
        for elem in body_contour_ref:
            if hasattr(elem, "ReferencedROINumber"):
                if elem.ReferencedROINumber == Body_ROInumber:
                    Body_index = body_idx_count
                    # print(Body_index)
                    break
            body_idx_count = body_idx_count + 1

        bodycontour_sequence = rs_file.ROIContourSequence[Body_index].ContourSequence
        # body_slice_number = len(bodycontour_sequence)//2
        sequences = bodycontour_sequence
        # print(len(sequences))
        # for each sequence, get contour data .ContourData
        body_mask3D = np.zeros(ct_vol[:, :, :].shape)

        for sequence in sequences:
            if hasattr(sequence, "ContourImageSequence"):
                CntrImSeq = sequence.ContourImageSequence

                for uid in CntrImSeq:
                    if hasattr(uid, "ReferencedSOPInstanceUID"):
                        if str(uid.ReferencedSOPInstanceUID) in sorted_uid_list:
                            index = sorted_uid_list.index(str(uid.ReferencedSOPInstanceUID))
                            slice_contour = np.asarray(sequence.ContourData)

                            # print(slice_contour.shape)
                            # slice_contour = np.reshape(slice_contour, (int(len(slice_contour)//3), 3))

                            body_contour_coords = []
                            for i in range(0, len(slice_contour), 3):
                                x_mm = slice_contour[i]
                                y_mm = slice_contour[i + 1]

                                x_coord = int((float(x_mm) - float(ct_origin[0])) / float(ct_spacing[0]))
                                y_coord = int((float(y_mm) - float(ct_origin[1])) / float(ct_spacing[1]))

                                body_contour_coords.append([x_coord, y_coord])

                            body_contour_coords = np.asarray(body_contour_coords)
                            # print(body_contour_coords)
                            body_mask = np.zeros(ct_vol[1, :, :].shape)
                            poly = body_contour_coords[:, :2]
                            cv2.fillPoly(body_mask, [poly], color=1)
                            body_mask = body_mask.astype(bool)

                            body_mask3D[index, :, :] = body_mask
    except:
        #print("Body Mask not found")
        body_mask3D = np.zeros(ct_vol[:, :, :].shape)
    return body_mask3D

def get_registered_cbct(cbct_vol, ct_vol, reg_dir):
    reg_file = pydicom.read_file(reg_dir)
    registration_matrix = np.asarray(reg_file.RegistrationSequence[0].MatrixRegistrationSequence[-1].
                                     MatrixSequence[-1].FrameOfReferenceTransformationMatrix).reshape((4, 4))
    registration_matrix = np.linalg.inv(registration_matrix)

    # check if identity matrix, if yes, then other one is the right matrix to use
    if (registration_matrix == np.eye(4)).all():
        # print("IDENTITY MATRIX")
        registration_matrix = np.asarray(reg_file.RegistrationSequence[-1].MatrixRegistrationSequence[-1].
                                         MatrixSequence[-1].FrameOfReferenceTransformationMatrix).reshape((4, 4))
        registration_matrix = np.linalg.inv(registration_matrix)

    # use registration matrix to transform cbct into ct plane
    affine_transform = sitk.AffineTransform(3)
    affine_transform.SetMatrix(registration_matrix[:3, :3].ravel())
    affine_transform.SetTranslation(registration_matrix[:3, -1])

    cbct_vol = sitk.Resample(cbct_vol, ct_vol, affine_transform, sitk.sitkLinear, -500, cbct_vol.GetPixelID())

    return cbct_vol


#function to process image for ARL model
def get_single_cor_plane(cbct_vol):
    # flip the volume as it is in opposite direction in the z axis
    cbct_vol = np.flip(cbct_vol, 0)

    # get first and last indices (z-axis) from a coronal cbct slice

    column_means = cbct_vol.mean(axis=0)
    column_means = column_means.mean(axis=1)
    idx1 = column_means.argmax()
    cbct_image = cbct_vol[:, idx1, :]

    first_idx, last_idx = find_limits(cbct_image)
    cbct_vol = cbct_vol[first_idx:last_idx, :, :]

    cbct_image = cbct_vol[:, idx1, :]

    img_height = np.shape(cbct_image)[0]
    # crop image to desired size
    if img_height < 150:
        additional_slices = 150 - np.shape(cbct_image)[0]
        dark_arrays = np.zeros([additional_slices, np.shape(cbct_image)[1]]) - 500
        cbct_image = np.concatenate((dark_arrays, cbct_image), axis=0)

        cbct_image = cbct_image[:, 56:456]

    else:
        mid_slice = img_height // 2
        cbct_image = cbct_image[mid_slice - 75:mid_slice + 75, 56:456]

    cbct_cor_image = np.array(cbct_image, dtype='float32')
    img_height = cbct_cor_image.shape[0]
    img_width = cbct_cor_image.shape[1]

    cbct_cor_image = sci.zscore(cbct_cor_image, None)
    cbct_cor_image = cbct_cor_image.reshape(img_height, img_width)

    # plt.imshow(cbct_cor_image, cmap='gray')
    # plt.show()

    return cbct_cor_image


def process_raw_volumes(ct_directory, cbct_diretory, reg_filename, struct_filename, ARL_model):

    rs_dir = struct_filename
    reg_dir = reg_filename

    # get sorted ct and cbct volumes, along with directories for reg and rs files
    ct_vol_raw, sorted_uids = read_sitk(ct_directory, "CT")
    ct_origin = ct_vol_raw.GetOrigin()
    ct_spacing = ct_vol_raw.GetSpacing()

    raw_cbct_vol, _ = read_sitk(cbct_diretory, "CBCT")
    ct_vol = ct_vol_raw
    aligned_cbct_vol = get_registered_cbct(raw_cbct_vol, ct_vol, reg_dir)

    # get images (volumes) as np arrays
    ct_vol = sitk.GetArrayFromImage(ct_vol)
    aligned_cbct_vol = sitk.GetArrayFromImage(aligned_cbct_vol)

    # threshold HU
    minHU = -500
    maxHU = 1500
    ct_vol = np.clip(ct_vol, minHU, maxHU)
    aligned_cbct_vol = np.clip(aligned_cbct_vol, minHU, maxHU)

    ##process image for ARL_model
    ARL_input = get_single_cor_plane(aligned_cbct_vol)
    ARL_input = np.expand_dims(ARL_input, axis=0)
    ARL_input = np.expand_dims(ARL_input, axis = 3)
    #print(ARL_input.shape)

    ##run Anatomy Region Labeling and get most probable region
    Region_prediction = ARL_model.predict((ARL_input))
    Region_prediction = Region_prediction[0]
    #print(str(Region_prediction))

    return Region_prediction, ARL_input


def process_raw_patient_data(pat_info, ARL_model):
    #process dicom files to get slices in 3 orthogonal planes
    simct_dir = os.path.join(pat_info['root'], pat_info['simct_dir'])
    cbct_dir = os.path.join(pat_info['datepath'], pat_info['cbct_dir'])
    reg_filename = os.path.join(pat_info['datepath'], pat_info['regfile'])
    struct_filename = os.path.join(pat_info['root'], pat_info['structfile'])

    Region_Pred = process_raw_volumes(simct_dir, cbct_dir, reg_filename, struct_filename, ARL_model)

    return Region_Pred
