import codecs

MODE=1
if MODE==1:

    with codecs.open('msr_train_states.txt', 'w', encoding='utf8') as wf:
        with codecs.open('msr_training.utf8', 'r', encoding='utf8') as f:
            lines = f.readlines()
            for line in lines:
                words = line.strip().split(' ')
                state = ""
                for word in words:
                    if len(word) == 0 or word == "\r\n":
                        continue
                    if len(word) - 2 < 0:
                        state += 'S'
                    else:
                        state += "B" + "M" * (len(word) - 2) + "E"
                wf.write(state + "\n")
        print("FIN")

if MODE == 2:
    with codecs.open('msr_test_states.txt', 'w', encoding='utf8') as wf:
        with codecs.open('msr_test_gold.utf8', 'r', encoding='utf8') as f:
            lines = f.readlines()
            for line in lines:
                words = line.strip().split(' ')
                state = ""
                for word in words:
                    if len(word) == 0 or word == "\r\n":
                        continue
                    if len(word) - 2 < 0:
                        state += 'S'
                    else:
                        state += "B" + "M" * (len(word) - 2) + "E"
                wf.write(state + "\n")
        print("FIN")
