import os
import re
import time

import matplotlib.pyplot as plt
from keras import regularizers
from keras.layers import Dense, Dropout

from configs import params
from configs.params import available_datasets


def train_model(text_match_model, hyperparams, dataset_params):
    text_match_model.setup(hyperparams, dataset_params)
    text_match_model.build()
    text_match_model.compile()
    text_match_model.fit_generator()
    text_match_model.evaluate_generator()


class UnitReduceDense:
    """
    In Keras: input tensor => a series of layers => output tensor.
    The `call` method of the Keras layer cannot call the layer of Keras.
    What called in the `call` method of the Keras layer is the backend function.
    Define a class(not inherit from `Layer` class), then calls Keras layers in its __call__ method.
    """
    def __init__(self, layer_num, initial_unit_num, p_dropout=0.5,
                 kernel_l2_lambda=0, bias_l2_lambda=0, activity_l2_lambda=0,
                 reduce=False):
        self.layers = []
        for i in range(layer_num):
            if reduce:
                # If reduce is set to `True`, the information will be lost
                # as the dimension of the feature vector decreases.
                self.current_unit_num = max(int(initial_unit_num/(2**i)), 32)
            else:
                self.current_unit_num = max(initial_unit_num, 32)
            this_dense = Dense(self.current_unit_num, activation='relu',
                               kernel_regularizer=regularizers.l2(kernel_l2_lambda),
                               bias_regularizer=regularizers.l2(bias_l2_lambda),
                               activity_regularizer=regularizers.l2(activity_l2_lambda))
            self.layers.append(this_dense)
            self.layers.append(Dropout(p_dropout))

    def __call__(self, x):
        for layer in self.layers:
            x = layer(x)
        return x


def remove_symbols(seq, pattern_str):
    """
    remove specified symbol from seq
    :param seq:
    :param pattern_str: 例如text-preprocess项目的remove_comma_from_number()
    :return: new seq
    """
    match_symbol_pattern = re.compile(pattern_str)
    while True:
        matched_obj = match_symbol_pattern.search(seq)
        if matched_obj:
            matched_str = matched_obj.group()
            # print('matched_str:', matched_str)
            matched_symbol = matched_obj.group(1)
            seq = seq.replace(matched_str, matched_str.replace(matched_symbol, ''))
        else:
            break
    return seq

# https://zhidao.baidu.com/question/1830830474764728580.html
addr_to_full = {"n't": 'not', "'m": 'am', "'s": 'is', "'re": 'are',
                "'d": 'would', "'ll": 'will', "'ve": 'have'}


def transform_addr_full_format(token):
    if token in addr_to_full:
        return addr_to_full[token]
    else:
        return token


def get_current_time():
    return time.strftime('%Y-%m-%d %H_%M_%S', time.localtime(time.time()))


# 图片显示图例 => done
# 保存的图片名要包含模型 => done
def plot_figure(model_save_dir, figure_name, x_label, y_label, *args):
    """
    画图，目前最多画四条曲线，传入一个((x, y), label)元组，就画一条曲线，并标注图例
    这是一个阻塞函数
    :param figure_name: 图片的名字
    :param model_save_dir
    :param x_label: x轴轴标
    :param y_label: y轴轴标
    :param args: 变长参数，即参数数目可变
    :return: None
    """
    colors = ['r', 'b', 'g', 'y', 'k']
    styles = ['-', '--', '-.', ':']
    max_args_num = len(styles)
    length = len(args)
    if length > max_args_num:
        print('too much tuple, more than', max_args_num)
        return

    fig = plt.figure(figure_name)
    fig.clear()  # Avoid repeating drawings on the same figure
    # left, bottom, right, top
    axes = fig.add_axes([0.1, 0.1, 0.8, 0.8])
    for i in range(length):
        x, y = args[i][0]
        label = args[i][1]
        axes.plot(x, y, colors[i]+styles[i], lw=3, label=label)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    axes.set_title(figure_name)
    axes.legend(loc=0)

    if not os.path.exists(model_save_dir):
        os.makedirs(model_save_dir)
    save_url = os.path.join(model_save_dir, figure_name + '.png')
    fig.savefig(save_url)
    # plt.show()  # it is a blocking function


def show_save_record(model_save_dir, history, train_begin_time):
    record_info = list()

    record_info.append('\n========================== history ===========================\n')
    acc = history.history.get('acc')
    loss = history.history['loss']
    val_acc = history.history['val_acc']
    val_loss = history.history['val_loss']
    record_info.append('train acc: ' + str(acc) + '\n')
    record_info.append('train loss: ' + str(loss) + '\n')
    record_info.append('val acc: ' + str(val_acc) + '\n')
    record_info.append('val loss: ' + str(val_loss) + '\n')

    record_info.append('\n======================= acc & loss & val_acc & val_loss ============================\n')
    for i in range(len(acc)):
        record_info.append(
            'epoch {0:<3} | acc: {1:5.2f}% | loss: {2:<6.4f} |'
            ' val_acc: {3:5.2f}% | val_loss: {4:<6.4f}\n'.format(i + 1,
                                                                 acc[i] * 100, loss[i],
                                                                 val_acc[i] * 100, val_loss[i]))

    train_start = train_begin_time
    train_end = float(time.time())
    train_time = train_end - train_start
    record_info.append('\n================ Train end ================\n')
    record_info.append('Train time: {0:.2f}s\n'.format(train_time))
    record_str = ''.join(record_info)
    record_url = model_save_dir + os.path.sep + params.TRAIN_RECORD_FNAME
    print_save_str(record_str, record_url)

    # 训练完毕后，将每轮迭代的acc、loss、val_acc、val_loss以画图的形式进行展示 => done
    plt_x = [x + 1 for x in range(len(acc))]
    plt_acc = (plt_x, acc), 'acc'
    plt_loss = (plt_x, loss), 'loss'
    plt_val_acc = (plt_x, val_acc), 'val_acc'
    plt_val_loss = (plt_x, val_loss), 'val_loss'
    plot_figure(model_save_dir,
                'acc & loss & val_acc & val_loss',
                'epoch', 'index',
                plt_acc, plt_loss, plt_val_acc, plt_val_loss)


def print_save_str(to_print_save, save_url, save_encoding='utf-8'):
    print(to_print_save)
    save_url_dir = os.path.dirname(save_url)
    if not os.path.exists(save_url_dir):
        os.makedirs(save_url_dir)
    with open(save_url, 'a', encoding=save_encoding) as file:
        file.write(to_print_save)


def data_statistic(fname, open_encoding='utf-8'):
    # 统计正负样本分布
    total_count = 0
    positive_count = 0
    negative_count = 0
    with open(fname, 'r', encoding=open_encoding) as file:
        for line in file:
            if line and line != '\n':
                field_list = line.split('\t')
                if len(field_list) != 3:
                    continue
                label = int(field_list[2])
                if label == 1:
                    positive_count += 1
                    total_count += 1
                elif label == 0:
                    negative_count += 1
                    total_count += 1

    tmp = fname.split(os.path.sep)
    fname = tmp[len(tmp)-1]
    print('==========', fname, '==========')
    print('total count:', total_count)
    print('positive count:', positive_count)
    print('negative count:', negative_count)


if __name__ == '__main__':
    # ========== test _remove_symbols() func ==========
    # str1 = "'Random Number' is what I don't like at all."
    # str1 = "I don't like 'Random Number'."
    # str1 = "I don't like 'Random Number' at all"
    # print(remove_symbols(str1, params.MATCH_SINGLE_QUOTE_STR))

    # ========== test data_statistic() func ==========
    cikm_en = available_datasets[0]
    cikm_en = params.get_dataset_params(cikm_en)
    fname = cikm_en.raw_url
    data_statistic(fname)
    fname = cikm_en.train_url
    data_statistic(fname)
    fname = cikm_en.val_url
    data_statistic(fname)
    fname = cikm_en.test_url
    data_statistic(fname)
