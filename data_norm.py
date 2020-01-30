import numpy as np 
import math

import tensorflow.keras.backend as K
from tensorflow.keras.layers import Conv2D

'''
References: 
Peter U. Diehl, Daniel Neil, Jonathan Binas, Matthew Cook, Shih-Chii Liu, and Michael Pfeiffer. 2015. 
Fast-Classifying, High-Accuracy Spiking Deep Networks Through Weight and Threshold Balancing. IJCNN (2015)
'''

class DataNorm():
    def __init__(self, data, batch_size=None):
        self.data = data
        if batch_size == None:
            self.batch_size = len(data)
        else:
            self.batch_size = batch_size

    '''
    The maximum activation encountered in the training data is a good estimate of the highest
    activation possible in the model. This 'scale factor' is computed separately for each layer 
    of the network.
    The 'applied factor' is the scaled factor of each layer, divided by that of the previous layer. This
    brings all the factors to a uniform range of values (with respect to the input layer).
    Weights of each layer in the model are then divided by the corresponding applied factor to compute the
    final normalized weights.
    Only Convolution2D layer weights are normalized.
    '''

    def normalize(self, tg_model):
        print('Data Norm')
        tf_model = tg_model.tf_model
        g_model = tg_model.g_model

        # Get output functions for weighted layers.
        idx = [i for i, l in enumerate(tf_model.layers) if l.get_weights() != []]
        get_outputs = K.function([tf_model.input], [tf_model.layers[i].output for i in idx])

        # Find the maximum activation in each layer, given data.
        activation = np.empty(len(idx), dtype=np.float64)
        max_activation = np.zeros(len(idx), dtype=np.float64)
        n_batches = math.ceil(len(self.data) / self.batch_size)
        for i in range(n_batches):
            if i < n_batches - 1:
                x = self.data[i*self.batch_size : (i+1)*self.batch_size]
            else:
                x = self.data[i*self.batch_size : ]
            activation[:] = [np.max(out) for out in get_outputs(x)]
            max_activation[:] = np.max([max_activation, activation], 0)

        # Find the maximum weight in each layer.
        weights = tf_model.get_weights()
        max_weights = np.array([np.max(w) for w in weights], dtype=np.float64)

        # Compute scale factors and normalize weights.
        scale_factors = np.max([max_activation, max_weights], 0)

        # # === CONV2D LAYERS ONLY
        # for i, j in enumerate(idx):
        #     if not isinstance(tf_model.layers[j], Conv2D):
        #         scale_factors[i] = 1.0

        applied_factors = np.empty(len(idx))
        applied_factors[0] = scale_factors[0]
        for i in range(1, len(idx)):
            applied_factors[i] = scale_factors[i] / scale_factors[i-1]

        # Update this neuron population's threshold
        for i, name in enumerate([tf_model.layers[i].name for i in idx]):
            neurons = g_model.neuron_populations[name + '_nrn']
            neurons.extra_global_params['Vthr'].view[:] = applied_factors[i]
