import json
import os

def transmissionTime(baseDelay, numBytes, bandwidth):
    numBits = numBytes*8
    bandwidth = bandwidth * 10e3
    return baseDelay + (numBits/bandwidth)

def main(vefFile, packets):
    baseDelay = 1.5
    bandwidth = 200

    listDicts = []
    msgTimeMapping = {}
    with open(vefFile, mode="r") as f:
        for i in f.readlines()[2:]:
            i = i.split()

            #check if its not a wait
            if i[3] != 0 and i[1] != i[2]:
                numBytes = int(i[3])
                timeMicro = int(i[5])*10e-6
                msgID = int(i[0])
                #depTime = int(i[6])

                #reset dictionary
                dict = {"A" : 0, "B": 0, "t": "", "d": 0}

                #add source, dest and length
                dict["A"] = int(i[1])
                dict["B"] = int(i[2])
                dict["d"] = numBytes

                #check if its a message that depends on another message
                if i[4] == "0" or i[4] == "4":

                    #adding time to dict for independent messages, in microseconds
                    dict["t"] = round(timeMicro, 4)

                    #adding time(in microseconds) and message ID to mapping
                    msgTimeMapping[msgID] = timeMicro

                #for messages dependent on others
                else:

                    #if its a receive dependency:
                    if i[4] == "2" or i[4] == "6":

                        #get transmission time of the message
                        transTime = transmissionTime(baseDelay, numBytes, bandwidth)

                        #get the timestamp it was received considering send and transmission time
                        recvTime = msgTimeMapping[int(i[6])] + transTime

                        #add send timestamp of message in microseconds to the dictionary
                        dict["t"] = round(timeMicro + recvTime, 4)

                        #adding timestamp (in microseconds) and message ID to mapping
                        msgTimeMapping[msgID] = timeMicro + recvTime

                    else:
                        #get the timestamp the message depends on
                        depTime = msgTimeMapping[int(i[6])]

                        #add send timestamp of message in microseconds to the dictionary
                        dict["t"] = round(timeMicro + depTime, 4)

                        #adding timestamp (in microseconds) and message ID to mapping
                        msgTimeMapping[msgID] = timeMicro + depTime
                
                #adds dictionary to list, only if its not a wait
                listDicts.append(dict)
    with open(packets, mode ="w") as f:
        json.dump(listDicts, f, indent=2)

    #print(listDicts)
    #print(msgTimeMapping)

main("data/output_trace_dummyRecv.vef", "packets.yaml")