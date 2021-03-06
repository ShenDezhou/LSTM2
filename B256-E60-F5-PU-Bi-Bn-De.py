# lstm-crf
import codecs
import os
import re
import string
import pickle

import numpy
from keras import regularizers
from keras.layers import Dense, Embedding, SpatialDropout1D, Input, Bidirectional, CuDNNLSTM, Lambda,  BatchNormalization, Average, Maximum, concatenate
from keras.models import Model
from keras.models import load_model, model_from_json
from keras.optimizers import Adagrad
from scipy import sparse
from sklearn_crfsuite import metrics
from keras.preprocessing.sequence import pad_sequences
import keras.backend as K
from keras_contrib.layers import CRF
from keras_contrib.losses import crf_loss
from keras_contrib.metrics import crf_accuracy
from keras.initializers import Constant

#               precision    recall  f1-score   support
#
#            B     0.4638    0.4680    0.4659     58781
#            M     0.2091    0.2376    0.2225     18704
#            E     0.4134    0.4271    0.4202     58781
#            S     0.1693    0.1516    0.1599     48092
#
#     accuracy                         0.3490    184358
#    macro avg     0.3139    0.3211    0.3171    184358
# weighted avg     0.3451    0.3490    0.3468    184358

dicts = []
unidicts = []
predicts = []
sufdicts = []
longdicts = []
puncdicts = []
digitsdicts = []
chidigitsdicts = []
letterdicts = []
otherdicts = []

Thresholds = 0.95


def getTopN(dictlist):
    adict = {}
    for w in dictlist:
        adict[w] = adict.get(w, 0) + 1
    topN = max(adict.values())
    alist = [k for k, v in adict.items() if v >= topN * Thresholds]
    return alist


with codecs.open('msr_dic/msr_training_words.utf8', 'r', encoding='utf8') as fa:
    # with codecs.open('msr_dic/msr_test_words.utf8', 'r', encoding='utf8') as fb:
    #     with codecs.open('msr_dic/contract_words.utf8', 'r', encoding='utf8') as fc:
            lines = fa.readlines()
            # lines.extend(fb.readlines())
            # lines.extend(fc.readlines())
            lines = [line.strip() for line in lines]
            dicts.extend(lines)
            # uni, pre, suf, long 这四个判断应该依赖外部词典，置信区间为95%，目前没有外部词典，就先用训练集词典来替代
            unidicts.extend([line for line in lines if len(line) == 1 and re.search(u'[\u4e00-\u9fff]', line)])
            predicts.extend([line[0] for line in lines if len(line) > 1 and re.search(u'[\u4e00-\u9fff]', line)])
            predicts = getTopN(predicts)
            sufdicts.extend([line[-1] for line in lines if len(line) > 1 and re.search(u'[\u4e00-\u9fff]', line)])
            sufdicts = getTopN(sufdicts)
            longdicts.extend([line for line in lines if len(line) > 3 and re.search(u'[\u4e00-\u9fff]', line)])
            puncdicts.extend(string.punctuation)
            puncdicts.extend(list("！？。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰–‘’‛“”„‟…‧﹏"))
            digitsdicts.extend(string.digits)
            chidigitsdicts.extend(list("零一二三四五六七八九十百千万亿兆〇零壹贰叁肆伍陆柒捌玖拾佰仟萬億兆"))
            letterdicts.extend(string.ascii_letters)

            somedicts = []
            somedicts.extend(unidicts)
            somedicts.extend(predicts)
            somedicts.extend(sufdicts)
            somedicts.extend(longdicts)
            somedicts.extend(puncdicts)
            somedicts.extend(digitsdicts)
            somedicts.extend(chidigitsdicts)
            somedicts.extend(letterdicts)
            otherdicts.extend(set(dicts) - set(somedicts))

chars = []

with codecs.open('msr_dic/msr_dict.utf8', 'r', encoding='utf8') as f:
    # with codecs.open('msr_diccontract_dict.utf8', 'r', encoding='utf8') as fc:
    lines = f.readlines()
    # lines.extend(fc.readlines())
    for line in lines:
        for w in line:
            if w == '\n':
                continue
            else:
                chars.append(w)
print(len(chars))

bigrams = []
with codecs.open('msr_dic/msr_bigram.utf8', 'r', encoding='utf8') as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip()
        if len(line) > 0:
            bigrams.append(line)
print(len(bigrams))

rxdict = dict(zip(chars, range(1, 1 + len(chars))))
rxdict['\n'] = 0

rbxdict = dict(zip(bigrams, range(1, 1+len(bigrams))))
rbxdict['\n'] = 0

rydict = dict(zip(list("BMES"), range(len("BMES"))))


def getNgram(sentence, i):
    ngrams = []
    ch = sentence[i]
    ngrams.append(rxdict[ch])
    return ngrams


def getFeaturesDict(sentence, i):
    features = []
    features.extend(getNgram(sentence, i))
    assert len(features) == 1
    # featuresdic = dict([(str(j), features[j]) for j in range(len(features))])
    # return featuresdic
    return features

def getCharType(ch):
    types = []

    dictofdicts = [puncdicts, digitsdicts, chidigitsdicts, letterdicts, unidicts, predicts, sufdicts]
    for i in range(len(dictofdicts)):
        if ch in dictofdicts[i]:
            types.append(i)
            break

    extradicts = [longdicts, otherdicts]
    for i in range(len(extradicts)):
        for word in extradicts[i]:
            if ch in word:
                types.append(i + len(dictofdicts))
                break
        if len(types) > 0:
            break

    if len(types) == 0:
        return str(len(dictofdicts) + len(extradicts) - 1)

    assert len(types) == 1 or len(types) == 2, "{} {} {}".format(ch, len(types), types)
    # onehot = [0] * (len(dictofdicts) + len(extradicts))
    # for i in types:
    #     onehot[i] = 1

    return str(types[0])


def safea(sentence, i):
    if i < 0:
        return '\n'
    if i >= len(sentence):
        return '\n'
    return sentence[i]


def getNgram(sentence, i):
    #5 + 4*2 + 2*3=19
    ngrams = []
    for offset in [-2, -1, 0, 1, 2]:
        ngrams.append(safea(sentence, i + offset))

    for offset in [-2, -1, 0, 1]:
        ngrams.append(safea(sentence, i + offset) + safea(sentence, i + offset + 1))

    for offset in [-1, 0]:
        ngrams.append(safea(sentence, i + offset) + safea(sentence, i + offset + 1) + safea(sentence, i + offset + 2))
    return ngrams

def getBigram(sentence, i):
    #5 + 4*2 + 2*3=19
    ngrams = []
    for offset in [0, 1, 2]:
        ngrams.append(safea(sentence, i + offset))
    return ngrams


def getBigramVector(sentence, i):
    ngrams = getBigram(sentence, i)
    ngramv = []
    for ngram in ngrams:
        for ch in ngram:
            ngramv.append(rxdict.get(ch,0))
    return ngramv


def getUBgram(sentence, i):
    #3 + 2 = 5
    ngrams = []
    for offset in [0, 1, 2]:
        ngrams.append(safea(sentence, i + offset))

    for offset in [0, 1]:
        ngrams.append(safea(sentence, i + offset) + safea(sentence, i + offset + 1))

    # for offset in [0]:
    #     ngrams.append(safea(sentence, i + offset) + safea(sentence, i + offset + 1) + safea(sentence, i + offset + 2))
    return ngrams

def getUBgramVector(sentence, i):
    ngrams = getUBgram(sentence, i)
    ngramv = []
    for ngram in ngrams:
        if len(ngram)==1:
            ngramv.append(rxdict.get(ngram,0))
        if len(ngram)==2:
            if '\n' in ngram:
                ngramv.append(0)
            else:
                ngramv.append(rbxdict.get(ngram, 0))
    return ngramv


def getNgramVector(sentence, i):
    ngrams = getNgram(sentence, i)
    ngramv = []
    for ngram in ngrams:
        for word in ngram:
            for ch in word:
                ngramv.append(rxdict.get(ch,0))
    return ngramv

def getReduplication(sentence, i):
    reduplication = []
    for offset in [-2, -1]:
        if safea(sentence, i) == safea(sentence, i + offset):
            reduplication.append('1')
        else:
            reduplication.append('0')
    return reduplication

def getReduplicationVector(sentence, i):
    reduplicationv =[int(e) for e in getReduplication(sentence,i)]
    return reduplicationv

def getType(sentence, i):
    types = []
    for offset in [-1, 0, 1]:
        types.append(getCharType(safea(sentence, i + offset)))
    # types.append(getCharType(safea(sentence, i + offset - 1)) + getCharType(safea(sentence, i + offset)) + getCharType(
    #         safea(sentence, i + offset + 1)))
    return types

def getTypeVector(sentence, i):
    types = getType(sentence,i)
    types = [int(t) for t in types]
    return types

def getFeatures(sentence, i):
    features = []
    features.extend(getUBgramVector(sentence, i))
    # features.extend(getReduplicationVector(sentence, i))
    # features.extend(getTypeVector(sentence, i))
    assert len(features) == 5, (len(features),features)
    return features


def getFeaturesDict(sentence, i):
    features = []
    features.extend(getNgramVector(sentence, i))
    features.extend(getReduplicationVector(sentence, i))
    features.extend(getType(sentence, i))
    assert len(features) == 24
    featuresdic = dict([(str(j), features[j]) for j in range(len(features))])
    return featuresdic

batch_size = 20
maxlen = 581
nFeatures = 3+2
word_size = 100
Hidden = 150
Regularization = 1e-4
Dropoutrate = 0.2
learningrate = 0.2
Marginlossdiscount = 0.2
nState = 4
EPOCHS = 60
modelfile = os.path.basename(__file__).split(".")[0]


MODE = 2

if MODE == 1:
    with codecs.open('plain/msr_training.utf8', 'r', encoding='utf8') as ft:
        with codecs.open('plain/msr_train_states.txt', 'r', encoding='utf8') as fs:
            with codecs.open('model/f5/msr_train_crffeatures.pkl', 'wb') as fx:
                with codecs.open('model/f5/msr_train_crfstates.pkl', 'wb') as fy:
                    xlines = ft.readlines()
                    ylines = fs.readlines()
                    X = []
                    y = []

                    print('process X list.')
                    counter = 0
                    for line in xlines:
                        line = line.replace(" ", "").strip()
                        line = '\n' *(maxlen-len(line)) + line
                        assert len(line)==maxlen
                        X.append([getFeatures(line, i) for i in range(len(line))])
                        # X.append([rxdict.get(e, 0) for e in list(line)])
                        # break
                        counter += 1
                        if counter % 10000 == 0 and counter != 0:
                            print('.')

                    X = numpy.array(X)
                    print(len(X), X.shape)
                    # X = pad_sequences(X, maxlen=maxlen, padding='pre', value=[0]*nFeatures)
                    # print(len(X), X.shape)

                    print('process y list.')
                    for line in ylines:
                        line = line.strip()
                        line = 'S' *(maxlen-len(line)) + line
                        line = [rydict[s] for s in line]
                        sline = numpy.zeros((len(line), len("BMES")), dtype=int)
                        for g in range(len(line)):
                            sline[g, line[g]] = 1
                        y.append(sline)
                        # break
                    print(len(y))
                    # y = pad_sequences(y, maxlen=maxlen, padding='pre', value=3)
                    y = numpy.array(y)
                    print(len(y), y.shape)

                    print('validate size.')
                    for i in range(len(X)):
                        assert len(X[i]) == len(y[i])

                    print('output to file.')
                    sX = pickle.dumps(X)
                    fx.write(sX)
                    sy = pickle.dumps(y)
                    fy.write(sy)

if MODE==2:
    loss = "squared_hinge"
    optimizer = "nadam"
    metric= "accuracy"
    sequence = Input(shape=(maxlen,nFeatures,))
    seqsa, seqsb, seqsc, seqsd, seqse = Lambda(lambda x: [x[:,:,0],x[:,:,1],x[:,:,2],x[:,:,3],x[:,:,4]])(sequence)

    zhwiki_emb = numpy.load("msr_dic/zhwiki_embedding.npy")
    embeddeda = Embedding(len(chars) + 1, word_size,embeddings_initializer=Constant(zhwiki_emb), input_length=maxlen, mask_zero=False)(seqsa)
    embeddedb = Embedding(len(chars) + 1, word_size,embeddings_initializer=Constant(zhwiki_emb), input_length=maxlen, mask_zero=False)(seqsb)
    embeddedc = Embedding(len(chars) + 1, word_size,embeddings_initializer=Constant(zhwiki_emb), input_length=maxlen, mask_zero=False)(seqsc)

    maximuma = Maximum()([embeddeda, embeddedb])
    maximumb = Maximum()([embeddedc, embeddedb])

    # zhwiki_biemb = numpy.load("model/zhwiki_biembedding.npy")
    zhwiki_biemb = sparse.load_npz("model/zhwiki_biembedding.npz").todense()
    embeddedd = Embedding(len(bigrams) + 1, word_size, input_length=maxlen,embeddings_initializer=Constant(zhwiki_biemb),
                          mask_zero=False)(seqsd)
    embeddede = Embedding(len(bigrams) + 1, word_size, input_length=maxlen,embeddings_initializer=Constant(zhwiki_biemb),
                          mask_zero=False)(seqse)

    concat = concatenate([embeddeda, maximuma, maximumb, embeddedd, embeddede])

    dropout = SpatialDropout1D(rate=Dropoutrate)(concat)

    blstm = Bidirectional(CuDNNLSTM(Hidden,batch_input_shape=(maxlen,nFeatures), return_sequences=True), merge_mode='sum')(dropout)
    # dropout = Dropout(rate=Dropoutrate)(blstm)
    batchNorm = BatchNormalization()(blstm)
    dense = Dense(nState, activation='softmax', kernel_regularizer=regularizers.l2(Regularization))(batchNorm)
    # crf = CRF(nState, activation='softmax', kernel_regularizer=regularizers.l2(Regularization))(dropout)

    model = Model(input=sequence, output=dense)
    # model.compile(loss='categorical_crossentropy', optimizer=adagrad, metrics=["accuracy"])
    # optimizer = Adagrad(lr=learningrate)
    model.compile(loss=loss, optimizer=optimizer, metrics=[metric])
    model.summary()

    with codecs.open('model/f5/msr_train_crffeatures.pkl', 'rb') as fx:
        with codecs.open('model/f5/msr_train_crfstates.pkl', 'rb') as fy:
            with codecs.open('model/msr_train_%s_model.pkl'%modelfile, 'wb') as fm:
                bx = fx.read()
                by = fy.read()
                X = pickle.loads(bx)
                y = pickle.loads(by)
                print(X[-1])
                print(y[-1])
                for i in range(len(X)):
                    assert len(X[i]) == len(y[i])
                print('training')

                history = model.fit(X, y, batch_size=batch_size, nb_epoch=EPOCHS, verbose=1)

                print('trained')
                sm = pickle.dumps(model)
                fm.write(sm)

                # yp = model.predict(X)
                # print(yp)
                # m = metrics.flat_classification_report(
                #     y, yp, labels=list("BMES"), digits=4
                # )
                # print(m)
                model_json = model.to_json()
                with open("keras/%s.json"%modelfile, "w") as json_file:
                    json_file.write(model_json)
                model.save_weights("keras/%s-weights.h5"%modelfile)

                model.save("keras/%s.h5"%modelfile)
                print('FIN')

if MODE == 3:
    STATES = list("BMES")
    with codecs.open('plain/msr_test.utf8', 'r', encoding='utf8') as ft:
        with codecs.open('baseline/msr_test_%s_states.txt'%modelfile, 'w', encoding='utf8') as fl:

            json_file = open('keras/%s.json'%modelfile, 'r')
            loaded_model_json = json_file.read()
            json_file.close()
            model = model_from_json(loaded_model_json)
            model.load_weights("keras/%s-weights.h5"%modelfile)

            # model = load_model("keras/pretrained-bigram-dropout-bilstm-bn.h5")
            model.summary()

            xlines = ft.readlines()
            X = []
            print('process X list.')
            counter = 0
            for line in xlines:
                line = line.replace(" ", "").strip()
                line = '\n' * (maxlen - len(line)) + line
                X.append([getFeatures(line, i) for i in range(len(line))])
                # X.append([rxdict.get(e, 0) for e in list(line)])
                counter += 1
                if counter % 1000 == 0 and counter != 0:
                    print('.')
            X = numpy.array(X)
            print(len(X), X.shape)

            yp = model.predict(X)
            print(yp.shape)
            for i in range(yp.shape[0]):
                sl = yp[i]
                lens = len(xlines[i].strip())
                for s in sl[-lens:]:
                    i = numpy.argmax(s)
                    fl.write(STATES[i])
                fl.write('\n')
            print('FIN')

if MODE==4:
    json_file = open('keras/%s.json'%modelfile, 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    model = model_from_json(loaded_model_json)
    model.load_weights("keras/%s-weights.h5"%modelfile)

    model.save(r"C:\Users\Administrator\Desktop\%s.h5"%modelfile)
