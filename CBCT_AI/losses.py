#==============================================================================#
#  Author:       Dominik Müller                                                #
#  Copyright:    2020 IT-Infrastructure for Translational Medical Research,    #
#                University of Augsburg                                        #
#                                                                              #
#  This program is free software: you can redistribute it and/or modify        #
#  it under the terms of the GNU General Public License as published by        #
#  the Free Software Foundation, either version 3 of the License, or           #
#  (at your option) any later version.                                         #
#                                                                              #
#  This program is distributed in the hope that it will be useful,             #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of              #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
#  GNU General Public License for more details.                                #
#                                                                              #
#  You should have received a copy of the GNU General Public License           #
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#==============================================================================#
#-----------------------------------------------------#
#                   Library imports                   #
#-----------------------------------------------------#
# External libraries
from tensorflow.keras import backend as K
import numpy as np
import tensorflow as tf
from scipy.ndimage import distance_transform_edt as distance
import cv2
import sys
import matplotlib.pyplot as plt

#-----------------------------------------------------#
#              Standard Dice coefficient              #
#-----------------------------------------------------#
def dice_coefficient(y_true, y_pred, smooth=0.00001):
    y_true_f = K.flatten(y_true)
    y_pred_f = K.flatten(y_pred)
    intersection = K.sum(y_true_f * y_pred_f)
    return (2. * intersection + smooth) / \
           (K.sum(y_true_f) + K.sum(y_pred_f) + smooth)

def dice_coefficient_loss(y_true, y_pred):
    return 1-dice_coefficient(y_true, y_pred)

#-----------------------------------------------------#
#                Soft Dice coefficient                #
#-----------------------------------------------------#
def dice_soft(y_true, y_pred, smooth=0.00001):
    # Identify axis
    axis = identify_axis(y_true.get_shape())

    # Calculate required variables
    intersection = y_true * y_pred
    intersection = K.sum(intersection, axis=axis)
    y_true = K.sum(y_true, axis=axis)
    y_pred = K.sum(y_pred, axis=axis)

    # Calculate Soft Dice Similarity Coefficient
    dice = ((2 * intersection) + smooth) / (y_true + y_pred + smooth)

    # Obtain mean of Dice & return result score
    dice = K.mean(dice)
    return dice

def dice_soft_loss(y_true, y_pred):
    return 1-dice_soft(y_true, y_pred)

#-----------------------------------------------------#
#              Weighted Dice coefficient              #
#-----------------------------------------------------#
def dice_weighted(weights):
    weights = K.variable(weights)

    def weighted_loss(y_true, y_pred, smooth=0.00001):
        axis = identify_axis(y_true.get_shape())
        intersection = y_true * y_pred
        intersection = K.sum(intersection, axis=axis)
        y_true = K.sum(y_true, axis=axis)
        y_pred = K.sum(y_pred, axis=axis)
        dice = ((2 * intersection) + smooth) / (y_true + y_pred + smooth)
        dice = dice * weights
        return -dice
    return weighted_loss

#-----------------------------------------------------#
#              Dice & Crossentropy loss               #
#-----------------------------------------------------#
def dice_crossentropy(y_truth, y_pred):
    # Obtain Soft DSC
    dice = dice_soft_loss(y_truth, y_pred)
    # Obtain Crossentropy
    crossentropy = K.categorical_crossentropy(y_truth, y_pred)
    crossentropy = K.mean(crossentropy)
    # Return sum
    return dice + crossentropy

#-----------------------------------------------------#
#                    Tversky loss                     #
#-----------------------------------------------------#
#                     Reference:                      #
#                Sadegh et al. (2017)                 #
#     Tversky loss function for image segmentation    #
#      using 3D fully convolutional deep networks     #
#-----------------------------------------------------#
# alpha=beta=0.5 : dice coefficient                   #
# alpha=beta=1   : jaccard                            #
# alpha+beta=1   : produces set of F*-scores          #
#-----------------------------------------------------#
def tversky_loss(y_true, y_pred, smooth=0.000001):
    # Define alpha and beta
    alpha = 0.5
    beta  = 0.5
    # Calculate Tversky for each class
    axis = identify_axis(y_true.get_shape())
    tp = K.sum(y_true * y_pred, axis=axis)
    fn = K.sum(y_true * (1-y_pred), axis=axis)
    fp = K.sum((1-y_true) * y_pred, axis=axis)
    tversky_class = (tp + smooth)/(tp + alpha*fn + beta*fp + smooth)
    # Sum up classes to one score
    tversky = K.sum(tversky_class, axis=[-1])
    # Identify number of classes
    n = K.cast(K.shape(y_true)[-1], 'float32')
    # Return Tversky
    return n-tversky

#-----------------------------------------------------#
#             Tversky & Crossentropy loss             #
#-----------------------------------------------------#
def tversky_crossentropy(y_truth, y_pred):
    # Obtain Tversky Loss
    tversky = tversky_loss(y_truth, y_pred)
    # Obtain Crossentropy
    crossentropy = K.categorical_crossentropy(y_truth, y_pred)
    crossentropy = K.mean(crossentropy)
    # Return sum
    return tversky + crossentropy

def calc_dist_map(seg):
    res = np.zeros_like(seg)
    posmask = seg.astype(np.bool)

    if posmask.any():
        negmask = ~posmask
        inner_dist = (distance(posmask) - 1) * posmask
        res = distance(negmask) - inner_dist
    return res

def calc_dist_map_batch(y_true):
    y_true_numpy = y_true.numpy()
    return np.array([calc_dist_map(y)
                     for y in y_true_numpy]).astype(np.float32)

def surface_loss(y_true, y_pred):
    y_true_dist_map = tf.py_function(func=calc_dist_map_batch,
                                     inp=[y_true],
                                     Tout=tf.float32)
    multipled = y_pred * y_true_dist_map
    return K.mean(multipled)

def gl_sl_wrapper(alpha):
    def gl_sl(y_true, y_pred):
        return alpha * dice_soft_loss(y_true, y_pred) + (1 - alpha) * surface_loss(y_true, y_pred)

    return gl_sl
#-----------------------------------------------------#
#                     Subroutines                     #
#-----------------------------------------------------#
# Identify shape of tensor and return correct axes
def identify_axis(shape):
    # Three dimensional
    if len(shape) == 5 : return [1,2,3]
    # Two dimensional
    elif len(shape) == 4 : return [1,2]
    # Exception - Unknown
    else : raise ValueError('Metric: Shape of tensor is neither 2D or 3D.')

# np.set_printoptions(threshold=sys.maxsize)
# gtIm = cv2.imread("Z:\DLuximon\Abdomen Segmentation\Stmc_Py\Dataset\Testing\Label\Patient-068(0032)_gt.png",cv2.IMREAD_GRAYSCALE)
# dist = calc_dist_map(gtIm)
#
# _,contours,_ = cv2.findContours(gtIm, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
# #image = cv2.drawContours(dist, contours, -1, (255, 0, 0), 1)
# plt.imshow(dist)
# plt.show()

# plt.imshow(dist)
# #plt.imshow(gtIm)
# plt.show()
# print(dist)


# tempprior = cv2.imread("Z:\DLuximon\Abdomen Segmentation\Stmc_Py\Dataset_Interp_4\Testing\Prior_Information\Patient-160(0004)_prior.png", cv2.IMREAD_GRAYSCALE)
# target = cv2.imread("Z:\DLuximon\Abdomen Segmentation\Stmc_Py\Dataset_Interp_4\Testing\Target\Patient-160(0004).png", cv2.IMREAD_GRAYSCALE)
# img_height = target.shape[0]
# img_width = target.shape[1]
# tempprior[tempprior <= 127] = 0
# tempprior[tempprior > 127] = 255
# _,contours,_ = cv2.findContours(tempprior, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
# cnt = contours[0]
# M = cv2.moments(cnt)
# centerX_indx = int(M['m10'] / M['m00'])
# centerY_indx = int(M['m01'] / M['m00'])
# print(img_width,img_height)
# print(centerX_indx,centerY_indx)
# #
# PatchWidth = 160
# limits = int(PatchWidth / 2)
# #
# if (centerX_indx - limits < 0):
#     centerX_indx = limits
# if (centerX_indx + limits > img_width):
#     centerX_indx = img_width-limits
# if (centerY_indx - limits < 0):
#     centerY_indx = limits
# if (centerY_indx + limits > img_height):
#     centerY_indx = img_height-limits
#
# print(centerX_indx,centerY_indx)
#
# concat_patch = target[centerY_indx - limits:centerY_indx + limits,
#                centerX_indx - limits:centerX_indx + limits]
# plt.imshow(concat_patch)
# plt.show()