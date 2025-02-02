import tensorflow as tf
import numpy as np
from tqdm import tqdm

from ml_genn.layers import InputType
from ml_genn.layers import IFNeurons
from ml_genn.layers import SpikeInputNeurons
from ml_genn.layers import PoissonInputNeurons
from ml_genn.layers import IFInputNeurons

class SpikeNorm(object):
    def __init__(self, norm_data, norm_time, input_type=InputType.POISSON):
        self.norm_data = norm_data
        self.norm_time = norm_time
        self.input_type = InputType(input_type)

    def validate_tf_layer(self, tf_layer):
        if tf_layer.activation != tf.keras.activations.relu:
            raise NotImplementedError('{} activation not supported'.format(type(tf_layer.activation)))
        if tf_layer.use_bias == True:
            raise NotImplementedError('bias tensors not supported')

    def create_input_neurons(self, pre_compile_output):
        if self.input_type == InputType.SPIKE:
            return SpikeInputNeurons()
        elif self.input_type == InputType.SPIKE_SIGNED:
            return SpikeInputNeurons(signed_spikes=True)
        elif self.input_type == InputType.POISSON:
            return PoissonInputNeurons()
        elif self.input_type == InputType.POISSON_SIGNED:
            return PoissonInputNeurons(signed_spikes=True)
        elif self.input_type == InputType.IF:
            return IFInputNeurons()

    def create_neurons(self, tf_layer, pre_compile_output):
        return IFNeurons(threshold=1.0)

    def pre_compile(self, tf_model):
        pass

    def post_compile(self, mlg_model):
        g_model = mlg_model.g_model
        n_samples = self.norm_data[0].shape[0]

        # Set layer thresholds high initially
        for layer in mlg_model.layers[1:]:
            layer.neurons.set_threshold(np.inf)

        # For each weighted layer
        for layer in mlg_model.layers[1:]:
            threshold = np.float64(0.0)

            # For each sample presentation
            progress = tqdm(total=n_samples)
            for batch_start in range(0, n_samples, g_model.batch_size):
                batch_end = min(batch_start + g_model.batch_size, n_samples)
                batch_n = batch_end - batch_start
                batch_data = [x[batch_start:batch_end]
                              for x in self.norm_data]

                # Set new input
                mlg_model.reset()
                mlg_model.set_input_batch(batch_data)

                # Main simulation loop
                while g_model.t < self.norm_time:
                    # Step time
                    mlg_model.step_time()

                    # Get maximum activation
                    nrn = layer.neurons.nrn
                    nrn.pull_var_from_device('Vmem')
                    if nrn.vars['Vmem'].view.ndim == 1:
                        output_view = nrn.vars['Vmem'].view[np.newaxis]
                    else:
                        output_view = nrn.vars['Vmem'].view[:batch_n]
                    threshold = np.max([threshold, output_view.max()])
                    output_view[:] = np.float64(0.0)
                    nrn.push_var_to_device('Vmem')

                progress.update(batch_n)

            progress.close()

            # Update this layer's threshold
            print('layer <{}> threshold: {}'.format(layer.name, threshold))
            layer.neurons.set_threshold(threshold)
