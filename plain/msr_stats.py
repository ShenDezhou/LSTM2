import  codecs

with codecs.open('msr_test.utf8', 'r', encoding='utf8') as ft:
    with codecs.open('msr_training.utf8', 'r', encoding='utf8') as f:
        lines = f.readlines()
        tlines = ft.readlines()
        mx = [len("".join(l.strip().split(' '))) for l in lines]
        print(max(mx))
        mx = [len("".join(l.strip().split(' '))) for l in tlines]
        print(max(mx))
print("FIN")