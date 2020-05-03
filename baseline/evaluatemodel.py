import codecs

from sklearn_crfsuite import metrics

MODE = 1

GOLD = '../plain/msr_test_states.txt'

if MODE == 1:
    TEST = 'pku_test_pretrained_context_unigram_states.txt'

with codecs.open(TEST, 'r', encoding='utf8') as fj:
    with codecs.open(GOLD, 'r', encoding='utf8') as fg:
        jstates = fj.readlines()
        states = fg.readlines()
        y = []
        for state in states:
            state = state.strip()
            y.append(list(state))
        yp = []
        for jstate in jstates:
            jstate = jstate.strip()
            yp.append(list(jstate))
        for i in range(len(y)):
            assert len(yp[i]) == len(y[i])
        m = metrics.flat_classification_report(
            y, yp, labels=list("BMES"), digits=4
        )
        print(m)
