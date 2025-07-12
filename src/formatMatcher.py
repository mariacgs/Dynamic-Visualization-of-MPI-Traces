import json
import os

def transmissionTime(baseDelay, numBytes, bandwidth):
    numBits = numBytes*8
    bandwidthBitsPerSec = bandwidth * 1e9
    delaySec = numBits/bandwidthBitsPerSec
    return baseDelay + (delaySec*1e6)

def main(vefFile, packets):
    baseDelay = 1.5
    simTime = 0
    startTime = 0

    """ CHANGE TO USER SPECIFIED"""
    bandwidth = 200

    listDicts = []
    msgTimeMapping = {}
    with open(vefFile, mode="r") as f:
        for i in f.readlines()[2:]:
            i = i.split()

            #check if its not a wait
            if i[3] != 0 and i[1] != i[2]:
                numBytes = int(i[3])
                timeMicro = int(i[5])*1e-6*1000 # multiply by a 1000 because we get how many picoseconds a cycle takes: 1000ps
                msgID = int(i[0])
                dTime = int(i[6])
                dep = int(i[4])

                #reset dictionary
                dict = {"A" : 0, "B": 0, "t": "", "d": 0}

                #add source, dest and length
                dict["A"] = int(i[1])
                dict["B"] = int(i[2])
                dict["d"] = numBytes

                #check if its a message that depends on another message
                if dep == 0 or dep == 4:

                    #adding time to dict for independent messages, in microseconds
                    dict["t"] = round(timeMicro, 5)

                    #adding time(in microseconds) and message ID to mapping
                    msgTimeMapping[msgID] = timeMicro

                #for messages dependent on others
                else:

                    #if its a receive dependency:
                    if dep == 2 or dep == 6:

                        #get transmission time of the message
                        transTime = transmissionTime(baseDelay, numBytes, bandwidth)

                        #get the timestamp it was received considering send and transmission time
                        recvTime = msgTimeMapping[dTime] + transTime

                        #add send timestamp of message in microseconds to the dictionary
                        dict["t"] = round(timeMicro + recvTime, 5)

                        #adding timestamp (in microseconds) and message ID to mapping
                        msgTimeMapping[msgID] = timeMicro + recvTime

                    else:
                        #get the timestamp the message depends on
                        depTime = msgTimeMapping[dTime]

                        #add send timestamp of message in microseconds to the dictionary
                        dict["t"] = round(timeMicro + depTime, 5)

                        #adding timestamp (in microseconds) and message ID to mapping
                        msgTimeMapping[msgID] = timeMicro + depTime
                
                #adds dictionary to list, only if its not a wait
                listDicts.append(dict)
    with open(packets, mode ="w") as f:
        json.dump(listDicts, f, indent=2)


    #print(listDicts)
    print(msgTimeMapping)

main("data/output_trace_dummyRecv.vef", "packets.yaml")