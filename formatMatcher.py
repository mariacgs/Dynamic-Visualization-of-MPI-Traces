import json
import os

def main(vefFile, packetsFile):
    listDicts = []
    with open(vefFile, mode="r") as f:
        for i in f.readlines()[2:]:
            print(i)
            i = i.split()
            if i[3] != 0 and i[1] != i[2]:
                dict = {"A" : 0, "B": 0, "t": "", "d": 0}
                dict["A"] = int(i[1])
                dict["B"] = int(i[2])
                dict["d"] = int(i[3])
                #timestamp is gonna give me a sec
                listDicts.append(dict)
        print(listDicts)

main("data/output_trace_dummyRecv.vef", "result.txt")