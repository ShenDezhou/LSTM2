import codecs


with codecs.open('msr_training.utf8', 'r', encoding='utf8') as fa:
    with codecs.open('../msr_dic/msr_bigram.utf8' , 'w', encoding='utf8') as fb:
        lines = fa.readlines()
        bigrams = []
        for line in lines:
            line = line.replace(" ", "").strip()
            chars = list(line)
            if len(chars) < 2:
                continue
            for i in range(len(chars)-1):
                bigrams.append(chars[i]+chars[i+1]+"\n")
        # counter = Counter(bigrams)
        # bigrams = [k for k,v in counter.items()]
        bigrams = list(set(bigrams))
        bigrams.sort()
        fb.writelines(bigrams)

print("FIN")
