from tensor_genn.layers import ConnectionType, PadMode
from tensor_genn.layers import Layer, Conv2DConnection
from tensor_genn.layers.neuron_models import if_model


class Conv2D(Layer):

    def __init__(self, model, params, vars_init, global_params, name, filters,
                 conv_size, conv_strides=None, conv_padding='valid', connection_type='procedural'):
        super(Conv2D, self).__init__(model, params, vars_init, global_params, name)
        self.filters = filters
        self.conv_size = conv_size
        if conv_strides == None:
            self.conv_strides = (1, 1)
        else:
            self.conv_strides = conv_strides
        self.conv_padding = PadMode(conv_padding)
        self.connection_type = ConnectionType(connection_type)


    def connect(self, sources):
        connections = [Conv2DConnection(
            self.filters, self.conv_size, self.conv_strides, self.conv_padding, self.connection_type
        ) for i in range(len(sources))]
        super(Conv2D, self).connect(sources, connections)


class IFConv2D(Conv2D):

    def __init__(self, name, filters, conv_size, conv_strides=None, conv_padding='valid',
                 connection_type='procedural', threshold=1.0):
        super(IFConv2D, self).__init__(
            if_model, {}, {'Vmem': 0.0, 'nSpk': 0}, {'Vthr': threshold},
            name, filters, conv_size, conv_strides, conv_padding, connection_type
        )


    def set_threshold(self, threshold):
        self.global_params['Vthr'] = threshold

        if self.tg_model:
            for batch_i in range(self.tg_model.batch_size):
                nrn_name = '{}_nrn_{}'.format(self.name, batch_i)
                nrn = self.tg_model.g_model.neuron_populations[nrn_name]
                nrn.extra_global_params['Vthr'].view[:] = threshold
