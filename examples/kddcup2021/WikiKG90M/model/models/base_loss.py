# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Base loss function.
"""

import paddle
import paddle.nn as nn
import paddle.fluid as fluid
from paddle.nn.functional import log_sigmoid, sigmoid


class LossFunc(object):
    def __init__(self,
                 args,
                 loss_type='LogSigmoid',
                 neg_adv_sampling=False,
                 adv_temp_value=0.0,
                 pairwise=False):
        super(LossFunc, self).__init__()
        self.margin = args.margin
        self.loss_type = loss_type
        self.neg_adv_sampling = neg_adv_sampling
        self.adv_temp_value = adv_temp_value
        self.pairwise = pairwise
        self.get_loss_criterion()

    def get_total_loss(self, pos_score, neg_score):
        # ipdb.set_trace()

        if self.pairwise:
            pos_score = paddle.unsqueeze(pos_score, -1)
            loss = paddle.mean(self.loss_criterion(pos_score - neg_score, 1))
            return loss

        pos_loss = self.loss_criterion(pos_score, 1)
        neg_loss = self.loss_criterion(neg_score, self.neg_label)
        if self.neg_adv_sampling:
            neg_loss = neg_loss * self.adverarial_weight(neg_score)
            neg_loss = paddle.sum(neg_loss, axis=-1)
        else:
            neg_loss = paddle.mean(neg_loss, axis=-1)

        pos_loss = paddle.mean(pos_loss)
        neg_loss = paddle.mean(neg_loss)
        loss = (pos_loss + neg_loss) / 2
        return loss

    def adverarial_weight(self, score):
        """
        Adverarial the weight for softmax.
        """
        adv_score = self.adv_temp_value * score
        adv_softmax = nn.functional.softmax(adv_score)
        adv_softmax.stop_gradient = True
        return adv_softmax

    def get_loss_criterion(self):
        if self.loss_type == 'Hinge':
            self.hinge_loss()
        elif self.loss_type == 'Logsigmoid':
            self.log_sigmoid_loss()
        elif self.loss_type == 'BCE':
            self.bce_loss()

    def hinge_loss(self):
        class HingeLoss(object):
            def __init__(self, margin):
                super(HingeLoss, self).__init__()
                self.margin = margin

            def __call__(self, score, label):
                loss = self.margin - label * score
                loss = fluid.layers.relu(loss)
                return loss

        self.loss_criterion = HingeLoss(self.margin)
        self.neg_label = -1

    def log_sigmoid_loss(self):
        class LogSigmoidLoss(object):
            def __init__(self):
                super(LogSigmoidLoss, self).__init__()

            def __call__(self, score, label):
                return -log_sigmoid(label * score)

        self.loss_criterion = LogSigmoidLoss()
        self.neg_label = -1

    def bce_loss(self):
        class BCELoss(object):
            def __init__(self):
                super(BCELoss, self).__init__()

            def __call__(self, score, label):
                return -(label * paddle.log(sigmoid(score)) +
                         (1 - label) * paddle.log(1 - sigmoid(score)))

        self.loss_criterion = BCELoss()
        self.neg_label = 0
