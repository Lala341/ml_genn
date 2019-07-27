import numpy as np 
import math

import tensorflow as tf 
import tensorflow.keras.backend as K
from pygenn import genn_model, genn_wrapper

class DataBased():
    def __init__(self,data = None):
        self.x_train = data
        self.batch_size = 100

    def normalize(self,tf_model):
        wts_exist = [layer.get_weights() != [] for layer in tf_model.layers]
        wts_exist_inds = [i for i, x in enumerate(wts_exist) if x == True]
        get_output_from_layer = K.function([tf_model.layers[0].input],
                                           [tf_model.layers[i].output for i in wts_exist_inds])
        n_batches = math.ceil(len(self.x_train)/self.batch_size)
        max_wts = [np.max(wt) for wt in tf_model.get_weights()]
        max_acts = [0]*len(wts_exist_inds)
        for bi in range(n_batches):
            # get batch
            if bi < n_batches - 1:
                x = self.x_train[bi*self.batch_size:(bi+1)*self.batch_size]
            else:
                x = self.x_train[bi*self.batch_size:]

            layer_outputs = get_output_from_layer([x])
            b_macts = [np.max(op) for op in layer_outputs]
            max_acts = [max(b_macts[i],max_acts[i]) for i in range(len(b_macts))]
        
        scale_factors = [max(max_acts[i],max_wts[i]) for i in range(len(max_acts))]
        
        applied_factors = [scale_factors[0]] + [scale_factors[i]/scale_factors[i-1] for i in range(1,len(scale_factors))]    
        scaled_weights = [tf_model.get_weights()[i]/applied_factors[i] for i in range(len(applied_factors))]
        return scaled_weights