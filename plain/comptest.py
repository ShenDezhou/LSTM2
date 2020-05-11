import codecs


with codecs.open('msr_test.utf8', 'w', encoding='utf8') as wf:
    with codecs.open('msr_test_gold.utf8', 'r', encoding='utf8') as f:
        lines = f.readlines()
        for line in lines:
            nline = "".join(line.strip().split(' '))
            wf.write(nline + "\n")
    print("FIN")
