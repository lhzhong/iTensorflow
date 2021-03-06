#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr  2 21:43:13 2018

@author: zhong
"""

import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
from tensorflow.contrib.layers.python.layers.regularizers import l1_regularizer
from tensorflow.contrib.layers.python.layers.regularizers import l2_regularizer


#%%
def conv(layer_name, x, out_channels, kernel_size=[3, 3], stride=[1, 1, 1, 1], method='SAME', is_trainable=True):
    '''Convolution op wrapper, use RELU activation after convolution
    Args:
        layer_name: e.g. conv1, pool1...
        x: input tensor, [batch_size, height, width, channels]
        out_channels: number of output channels (or comvolutional kernels)
        kernel_size: the size of convolutional kernel, VGG paper used: [3,3]
        stride: A list of ints. 1-D of length 4. VGG paper used: [1, 1, 1, 1]
        method: 'SAME' or 'VALID'
        is_pretrain: if load pretrained parameters, freeze all conv layers. 
        Depending on different situations, you can just set part of conv layers to be freezed.
        the parameters of freezed layers will not change when training.
    Returns:
        4D tensor
    '''

#    initializer=tf.contrib.layers.xavier_initializer()
    in_channels = x.get_shape()[-1]
    with tf.variable_scope(layer_name):
        w = tf.get_variable(name='weights',
                            trainable=is_trainable,
                            shape=[kernel_size[0], kernel_size[1], in_channels, out_channels],
                            initializer=tf.truncated_normal_initializer(stddev=0.1)) # default is uniform distribution initialization
        b = tf.get_variable(name='biases',
                            trainable=is_trainable,
                            shape=[out_channels],
                            initializer=tf.constant_initializer(0.1))
        x = tf.nn.conv2d(x, w, stride, padding=method, name='conv')
        x = tf.nn.bias_add(x, b, name='bias_add')
        x = tf.nn.relu(x, name='relu')
        
#        tf.add_to_collection('loss', l2_regularizer(.1)(w))
#        tf.add_to_collection('loss', l2_regularizer(.1)(b))
        
        return x


#%%
def pool(layer_name, x, kernel=[1, 2, 2, 1], stride=[1, 2, 2, 1], is_max_pool=True, method='SAME'):
    '''Pooling op
    Args:
        x: input tensor
        kernel: pooling kernel, VGG paper used [1,2,2,1], the size of kernel is 2X2
        stride: stride size, VGG paper used [1,2,2,1]
        padding:
        is_max_pool: boolen
                    if True: use max pooling
                    else: use avg pooling
        method:'SAME' or 'VALID'
    '''
    with tf.variable_scope(layer_name):
        
        if is_max_pool:
            x = tf.nn.max_pool(x, kernel, strides=stride, padding=method, name=layer_name)
        else:
            x = tf.nn.avg_pool(x, kernel, strides=stride, padding=method, name=layer_name)
        
        return x


#%%
def lrn(layer_name, x, radius=2, alpha=0.001 / 9.0, beta=0.75, bias=1.0):
    with tf.variable_scope(layer_name):
        x = tf.nn.local_response_normalization(x,
                                               alpha=alpha,
                                               beta=beta,
                                               depth_radius=radius,
                                               bias=bias,
                                               name=layer_name)
        return x


#%%
def batch_norm(layer_name, x):
    '''Batch normlization(I didn't include the offset and scale)
    '''
    with tf.variable_scope(layer_name):
        epsilon = 1e-3
        batch_mean, batch_var = tf.nn.moments(x, [0])
        x = tf.nn.batch_normalization(x,
                                      mean=batch_mean,
                                      variance=batch_var,
                                      offset=None,
                                      scale=None,
                                      variance_epsilon=epsilon)
        return x


#%%
def fc_layer(layer_name, x, out_nodes, use_relu=True):
    '''Wrapper for fully connected layers with RELU activation as default
    Args:
        layer_name: e.g. 'FC1', 'FC2'
        x: input feature map
        out_nodes: number of neurons for current FC layer
    '''
    shape = x.get_shape()
    if len(shape) == 4:
        size = shape[1].value * shape[2].value * shape[3].value
    else:
        size = shape[-1].value

    with tf.variable_scope(layer_name):
        w = tf.get_variable('weights',
                            shape=[size, out_nodes],
                            initializer=tf.truncated_normal_initializer(stddev=0.1))
        b = tf.get_variable('biases',
                            shape=[out_nodes],
                            initializer=tf.constant_initializer(0.1))
        flat_x = tf.reshape(x, [-1, size]) # flatten into 1D
        
        x = tf.nn.bias_add(tf.matmul(flat_x, w), b)
        
        tf.add_to_collection('loss', l2_regularizer(.1)(w))
        tf.add_to_collection('loss', l2_regularizer(.1)(b))
        
        if use_relu:
            return tf.nn.relu(x)
        else:
            return x


#%%
def dropout(layer_name, x, keep_prob):
    """Create a dropout layer."""
    with tf.variable_scope(layer_name):
        
        return tf.nn.dropout(x, keep_prob)

#%%
def loss(logits, labels):
    '''Compute loss
    Args:
        logits: logits tensor, [batch_size, n_classes]
        labels: one-hot labels
    '''
    with tf.name_scope('loss') as scope:
        cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=logits, labels=tf.argmax(labels,1),name='cross-entropy')
        loss = tf.reduce_mean(cross_entropy, name='loss')
        tf.summary.scalar(scope+'/loss', loss)
        return loss


#%%
def accuracy(logits, labels):
  """Evaluate the quality of the logits at predicting the label.
  Args:
    logits: Logits tensor, float - [batch_size, NUM_CLASSES].
    labels: Labels tensor, 
  """
  with tf.name_scope('accuracy') as scope:
      correct = tf.nn.in_top_k(logits, tf.argmax(labels,1), 1)
      correct = tf.cast(correct, tf.float32)
      accuracy = tf.reduce_mean(correct)*100.0
#      correct = tf.equal(tf.argmax(logits, 1), tf.argmax(labels, 1))
#      correct = tf.cast(correct, tf.float32)
#      accuracy = tf.reduce_mean(correct)*100.0
      tf.summary.scalar(scope+'/accuracy', accuracy)
      return accuracy


#%%
def optimize(loss, learning_rate):
    '''optimization, use Gradient Descent as default
    '''
    with tf.name_scope('optimizer'):
#        optimizer = tf.train.GradientDescentOptimizer(learning_rate=learning_rate)
        optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
#        optimizer = tf.train.MomentumOptimizer(learning_rate, 0.9)
        global_step = tf.Variable(0, name='global_step', trainable=False) 
        train_op = optimizer.minimize(loss, global_step=global_step)
        return train_op


#%%
def plot_feature_map(feature_map):
    
    fig, axes = plt.subplots(4, 4)
    for i, ax in enumerate(axes.flat):
        feature_map = np.array(feature_map)
        feature_map = np.squeeze(feature_map)
        img = feature_map[0,:,:,i]
#        ax.imshow(img, interpolation='nearest', cmap='seismic')
        ax.imshow(img, interpolation='nearest', cmap='binary')
        ax.set_xticks([])
        ax.set_yticks([])
    plt.show()


#%%
def print_all_variables(train_only=True):
    if train_only:
        t_vars = tf.trainable_variables()
        print("Trainable variables:------------------------")
    else:
        t_vars = tf.global_variables()
        print("Global variables:------------------------")
    for idx, v in enumerate(t_vars):
        print("  var {:3}: {:15}   {}".format(idx, str(v.get_shape()), v.name))   

#%%
def plot_images(images, label_true, label_pred=None):
    assert len(images) == len(label_true) == 9
    img_shape = (28, 28)
    
    fig, axes = plt.subplots(3, 3)
    fig.subplots_adjust(hspace=0.3, wspace=0.3)

    for i, ax in enumerate(axes.flat):
        
        ax.imshow(images[i].reshape(img_shape), cmap='binary')
        if label_pred is None:
            xlabel = "True: {0}".format(label_true[i])
        else:
            xlabel = "True: {0}, Pred: {1}".format(label_true[i], label_pred[i])

        ax.set_xlabel(xlabel)
        ax.set_xticks([])
        ax.set_yticks([])

    plt.show()

#%%
def plot_example_errors(data, label_pred, correct):
    
    incorrect = (correct == False)
    images = data.test.images[incorrect]
    label_pred = label_pred[incorrect]
    data.test.labels_one = np.argmax(data.test.labels, axis=1)
    label_true = data.test.labels_one[incorrect]
    
    # Plot the first 9 images.
    plot_images(images=images[0:9],
                label_true=label_true[0:9],
                label_pred=label_pred[0:9])
#%%
def plot_confusion_matrix(label_true, label_pred, num_classes):

#    label_true = data.test.labels_one
    cm = confusion_matrix(y_true=label_true, y_pred=label_pred)
    
    print(cm)
    plt.matshow(cm)
    plt.colorbar()
    tick_marks = np.arange(num_classes)
    plt.xticks(tick_marks, range(num_classes))
    plt.yticks(tick_marks, range(num_classes))
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.show()


#%%                
def load_with_skip(data_path, session, skip_layer):
    data_dict = np.load(data_path, encoding='latin1').item()
    for key in data_dict:
        if key not in skip_layer:
            with tf.variable_scope(key, reuse=True):
                for subkey, data in zip(('weights', 'biases'), data_dict[key]):
                    session.run(tf.get_variable(subkey).assign(data))
#%%