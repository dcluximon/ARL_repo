import tensorflow as tf
from tensorflow.keras.layers import *
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import Model


def Dense_layer(prev_layer,num_filter):
    eps = 1.1e-5

    #dense layer 1
    batch = BatchNormalization(axis=1, epsilon=eps)(prev_layer)
    conv = Conv2D(num_filter,(3,3),activation=None,padding='same')(batch)
    batch2 = BatchNormalization(axis=1, epsilon=eps)(conv)
    Act = Activation('relu')(batch2)
    conv2 = Conv2D(num_filter,(5,5),activation=None,padding='same')(Act)
    Act2 = Activation('relu')(conv2)
    drop_1 = Dropout(0.1)(Act2)

    # dense layer 2
    cat = concatenate([prev_layer,drop_1])
    batch = BatchNormalization(axis=1, epsilon=eps)(cat)
    conv = Conv2D(num_filter, (3, 3), activation=None, padding='same')(batch)
    batch2 = BatchNormalization(axis=1, epsilon=eps)(conv)
    Act = Activation('relu')(batch2)
    conv2 = Conv2D(num_filter, (5, 5), activation=None, padding='same')(Act)
    Act2 = Activation('relu')(conv2)
    drop_2 = Dropout(0.1)(Act2)

    # # dense layer 3
    cat = concatenate([prev_layer, drop_1, drop_2])
    batch = BatchNormalization(axis=1, epsilon=eps)(cat)
    conv = Conv2D(num_filter, (3, 3), activation=None, padding='same')(batch)
    batch2 = BatchNormalization(axis=1, epsilon=eps)(conv)
    Act = Activation('relu')(batch2)
    conv2 = Conv2D(num_filter, (5, 5), activation=None, padding='same')(Act)
    Act2 = Activation('relu')(conv2)
    drop_3 = Dropout(0.1)(Act2)

    # dense layer 4
    result = concatenate([prev_layer, drop_1, drop_2, drop_3])

    return result

def Transition_block(input,num_filter, layer_number):
    eps = 1.1e-5
    batch = BatchNormalization(axis=1, epsilon=eps)(input)
    conv = Conv2D(num_filter, (1, 1), activation=None, padding='same')(batch)

    if layer_number == 1:
        pool = MaxPooling2D(pool_size=(2,2),padding='same')(conv)
    if layer_number == 2:
        pool = MaxPooling2D(pool_size=(3,2),padding='same')(conv)
    if layer_number == 3:
        pool = MaxPooling2D(pool_size=(5,2),padding='same')(conv)
    if layer_number == 4:
        pool = MaxPooling2D(pool_size=(1,2),padding='same')(conv)
    if layer_number == 5:
        pool = MaxPooling2D(pool_size=(1,5),padding='same')(conv)
    return pool

def Dense_Net_AnatomyLabel(Cor_input_shape):
    #define inputs
    Cor_input = Input(Cor_input_shape)

    # coronal branch
    n = 16
    # encoder 1
    layer_number = 1
    Cor_num_filter = n*2
    Cor_conv_1 = Conv2D(Cor_num_filter, (3, 3), activation='relu', padding='same')(Cor_input)
    Cor_dense1 = Dense_layer(Cor_conv_1, Cor_num_filter)
    Cor_Transition1 = Transition_block(Cor_dense1, Cor_num_filter, layer_number)

    # encoder 2
    layer_number = 2
    Cor_num_filter = n*4
    Cor_dense2 = Dense_layer(Cor_Transition1, Cor_num_filter)
    Cor_Transition2 = Transition_block(Cor_dense2, Cor_num_filter, layer_number)

    # encoder 3
    layer_number = 3
    Cor_num_filter = n*8
    Cor_dense3 = Dense_layer(Cor_Transition2, Cor_num_filter)
    Cor_Transition3 = Transition_block(Cor_dense3, Cor_num_filter, layer_number)

    # encoder 4
    layer_number = 4
    Cor_num_filter = n*12
    Cor_dense4 = Dense_layer(Cor_Transition3, Cor_num_filter)
    Cor_Transition4 = Transition_block(Cor_dense4, Cor_num_filter, layer_number)
    #Cor_flatten = Flatten()(Cor_Transition4)

    # encoder 5
    layer_number = 5
    Cor_num_filter = n*16
    Cor_dense5 = Dense_layer(Cor_Transition4, Cor_num_filter)
    Cor_Transition5 = Transition_block(Cor_dense5, Cor_num_filter, layer_number)
    Cor_flatten = Flatten()(Cor_Transition5)

    output = Dense(4, activation='sigmoid')(Cor_flatten)

    model = Model(inputs=[Cor_input], outputs=output)
    print(model.summary())

    return model




