#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  3 16:35:00 2018

@author: zhong
"""

import math
import numpy as np
import tensorflow as tf

import cifar10_input

from models.lenet5 import LeNet5
from models.alexnet import AlexNet
from models.vgg16 import VGG16

num_classes = 10
batch_size = 128
n_test = 10000
test_data_path = './data/'
checkpoint_path = './checkpoints/lenet5/'


def evaluate_running():
    with tf.Graph().as_default():

        # reading test data
        images, labels = cifar10_input.read_cifar10(data_path=test_data_path,
                                                    is_train=False,
                                                    batch_size= batch_size,
                                                    shuffle=False)
        
        model = LeNet5(images, num_classes)
        logits = model.logits
        labels = tf.cast(labels,tf.int64)
        top_k_op = tf.nn.in_top_k(logits, tf.argmax(labels, 1), 1)
        saver = tf.train.Saver(tf.global_variables())
        
        with tf.Session() as sess:
            
            print("Reading checkpoints...")
            ckpt = tf.train.get_checkpoint_state(checkpoint_path)
            if ckpt and ckpt.model_checkpoint_path:
                global_step = ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1]
                saver.restore(sess, ckpt.model_checkpoint_path)
                print('Loading success, global_step is %s' % global_step)
            else:
                print('No checkpoint file found')
                return
        
            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(sess = sess, coord = coord)
            
            try:
                num_iter = int(math.ceil(n_test / batch_size))
                true_count = 0
                total_sample_count = num_iter * batch_size
                step = 0

                while step < num_iter and not coord.should_stop():
                    predictions = sess.run([top_k_op])
                    true_count += np.sum(predictions)
                    step += 1
                    precision = true_count / total_sample_count *100.0
                print('precision = %.2f%%' % precision)
            except Exception as e:
                coord.request_stop(e)
            finally:
                coord.request_stop()
                coord.join(threads)
                
                
if __name__ == '__main__':
    evaluate_running()