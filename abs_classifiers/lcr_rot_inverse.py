from abs_classifiers.neural_language_model import NeuralLanguageModel
import tensorflow as tf
from model_layers.attention_layers import attention_function
from model_layers.nn_layers import bi_dynamic_rnn, softmax_layer, reduce_mean_with_len


class LCRRotInverse(NeuralLanguageModel):

    def __init__(self, config, internal_data_loader):
        super().__init__(config, internal_data_loader)

    def model_itself(self, left_sentence_parts, left_sentence_lengths, right_sentence_parts, right_sentence_lengths,
                     target_parts, target_lengths, keep_prob1, keep_prob2):

        print('I am lcr rot inverse.')

        _id = '_lcr_rot_inverse'

        cell = tf.contrib.rnn.LSTMCell

        rate = 1 - self.config.keep_prob1

        # left hidden states
        input_left = tf.nn.dropout(left_sentence_parts, rate=rate)
        left_hidden_state = bi_dynamic_rnn(cell, input_left, self.config.number_hidden_units, left_sentence_lengths,
                                           'l' + _id)
        pool_l = reduce_mean_with_len(left_hidden_state, left_sentence_lengths)

        # right hidden states
        input_right = tf.nn.dropout(right_sentence_parts, rate=rate)
        right_hidden_state = bi_dynamic_rnn(cell, input_right, self.config.number_hidden_units, right_sentence_lengths,
                                            'r' + _id)
        pool_r = reduce_mean_with_len(right_hidden_state, right_sentence_lengths)

        # target hidden states
        target = tf.nn.dropout(target_parts, rate=rate)
        target_hidden_state = bi_dynamic_rnn(cell, target, self.config.number_hidden_units, target_lengths, 't' + _id)

        # attention target left
        att_t_l = attention_function(target_hidden_state, pool_l, target_lengths, 2 * self.config.number_hidden_units,
                                     self.config.max_target_length, self.config.l2_regularization,
                                     self.config.random_base, 'att_t_l' + _id)

        weighted_target_left_hidden_state = tf.math.multiply(tf.transpose(att_t_l, perm=[0, 2, 1]), target_hidden_state)
        target_left_context_representation = tf.squeeze(tf.matmul(att_t_l, target_hidden_state), [1])

        # attention target right
        att_t_r = attention_function(target_hidden_state, pool_r, target_lengths, 2 * self.config.number_hidden_units,
                                     self.config.max_target_length, self.config.l2_regularization,
                                     self.config.random_base, 'att_t_r' + _id)

        weighted_target_right_hidden_state = tf.math.multiply(tf.transpose(att_t_r, perm=[0, 2, 1]),
                                                              target_hidden_state)
        target_right_context_representation = tf.squeeze(tf.matmul(att_t_r, target_hidden_state), [1])

        # attention left
        att_l = attention_function(left_hidden_state, target_left_context_representation, left_sentence_lengths,
                                   2 * self.config.number_hidden_units, self.config.max_sentence_length,
                                   self.config.l2_regularization, self.config.random_base, 'att_l' + _id)

        weighted_left_hidden_state = tf.math.multiply(tf.transpose(att_l, perm=[0, 2, 1]), left_hidden_state)
        left_context_representation = tf.squeeze(tf.matmul(att_l, left_hidden_state), [1])

        # attention right
        att_r = attention_function(right_hidden_state, target_right_context_representation, right_sentence_lengths,
                                   2 * self.config.number_hidden_units, self.config.max_sentence_length,
                                   self.config.l2_regularization, self.config.random_base, 'att_r' + _id)

        weighted_right_hidden_state = tf.math.multiply(tf.transpose(att_r, perm=[0, 2, 1]), right_hidden_state)
        right_context_representation = tf.squeeze(tf.matmul(att_r, right_hidden_state), [1])

        sentence_representation = tf.concat([left_context_representation, target_left_context_representation,
                                             target_right_context_representation, right_context_representation], 1)

        prob = softmax_layer(sentence_representation, 8 * self.config.number_hidden_units, self.config.random_base,
                             self.config.keep_prob2, self.config.l2_regularization, self.config.number_of_classes)

        layer_information = {
            'left_hidden_state': left_hidden_state,
            'right_hidden_state': right_hidden_state,
            'target_hidden_state': target_hidden_state,
            'weighted_left_hidden_state': weighted_left_hidden_state,
            'weighted_right_hidden_state': weighted_right_hidden_state,
            'weighted_target_left_hidden_state': weighted_target_left_hidden_state,
            'weighted_target_right_hidden_state': weighted_target_right_hidden_state,
            'left_attention_score': att_l,
            'right_attention_score': att_r,
            'target_left_attention_score': att_t_l,
            'target_right_attention_score': att_t_r
        }

        return prob, layer_information
