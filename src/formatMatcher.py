import json
import os
import yaml
import sys
import datetime
import time

def transmissionTime(baseDelay, numBytes, bandwidth):
    numBits = numBytes*8
    bandwidthBitsPerSec = bandwidth * 1e9
    delaySec = numBits/bandwidthBitsPerSec
    return baseDelay + (delaySec*1e6)

def processNetwork(networkFile):
    with open(networkFile, "r") as f:
        networkDict = yaml.safe_load(f)
    startTime = networkDict[2]["startSimTime"]
    simTime = networkDict[2]["simTime"]
    return startTime, simTime

def main(vefFile, packets, network):
    baseDelay = 1.5
    startTime, simTime = processNetwork(network)

    """ CHANGE TO USER SPECIFIED"""
    bandwidth = 200

    listDicts = []
    msgTimeMapping = {}
    with open(vefFile, mode="r") as f:
        for lineNum, line in enumerate(f, start=1):
            line = line.split()
            if lineNum == 1:
                clock = int(line[-1])

            elif lineNum != 2:
            #check if its not a wait
                if line[3] != 0 and line[1] != line[2]:

                    msgID = int(line[0])
                    source = int(line[1])+1
                    dest = int(line[2])+1
                    numBytes = int(line[3])
                    dep = int(line[4])
                    timeMicro = int(line[5])*1e-6*1000 # multiply by a 1000 because we get how many picoseconds a cycle takes: 1000ps
                    dTime = int(line[6])

                    #reset dictionary
                    dct = {"A" : 0, "B": 0, "t": "", "d": 0}

                    #add source, dest and length
                    dct["A"] = source
                    dct["B"] = dest
                    dct["d"] = numBytes

                    #check if its a message that depends on another message
                    match dep:
                        case 0 | 4:
                            formattedTime = datetime.timedelta(microseconds=timeMicro)

                            #adding time to dict for independent messages
                            dct["t"] = startTime + formattedTime

                            #adding time(in microseconds) and message ID to mapping
                            msgTimeMapping[msgID] = timeMicro

                        #for messages dependent on others
                        #if its a receive dependency:
                        case 2 | 6:

                            #get transmission time of the message
                            transTime = transmissionTime(baseDelay, numBytes, bandwidth)

                            #get the timestamp it was received considering send and transmission time
                            recvTime = msgTimeMapping[dTime] + transTime

                            sendTime = timeMicro + recvTime

                            formattedTime = datetime.timedelta(microseconds=sendTime)

                            #add send timestamp of message in microseconds to the dictionary
                            dct["t"] = startTime + formattedTime

                            #adding timestamp (in microseconds) and message ID to mapping
                            msgTimeMapping[msgID] = sendTime

                        case _:
                            #get the timestamp the message depends on
                            depTime = msgTimeMapping[dTime]

                            sendTime = timeMicro + depTime

                            formattedTime = datetime.timedelta(microseconds=sendTime)

                            #add send timestamp of message in microseconds to the dictionary
                            dct["t"] = startTime + formattedTime
                            #adding timestamp (in microseconds) and message ID to mapping
                            msgTimeMapping[msgID] = sendTime
                    
                        #adds dictionary to list, only if its not a wait

                    listDicts.append(dct)


    sortedList = sorted(listDicts, key= lambda x: x["t"])

    with open(packets, mode ="w") as f:
        yaml.dump(sortedList, f, indent=2)


    #print(listDicts)
    print(msgTimeMapping)

main("data/outputLongerDummy.vef", "packets1.yaml", "network_traffic_visualizer/data/network.yaml")