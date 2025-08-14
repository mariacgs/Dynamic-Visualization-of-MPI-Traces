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
    return baseDelay + (delaySec*1e3)

def processNetwork(networkFile):
    with open(networkFile, "r") as f:
        networkDict = yaml.safe_load(f)
    startTime = networkDict[2]["startSimTime"]
    simTime = networkDict[2]["simTime"]
    linkCap = networkDict[2]["linkCap"]
    timestampType = networkDict[2]["timestampType"]

    #fileType = networkDict[2]["packetsFile"] IS IT ACTUALLY NECESSARY - I DONT THINK SO
    return startTime, simTime, linkCap, timestampType

def main(vefFile, packets, network):
    baseDelay = 1.5
    startTime, simTime, linkCap, timestampType = processNetwork(network)
    counter = 3

    """ CHANGE TO USER SPECIFIED"""
   ## bandwidth = 200               BANDWIDTH = LINK CAP IN THIS CASE ?

    listDicts = []
    msgTimeMapping = {}
    with open(vefFile, mode="r") as f:
        for lineNum, line in enumerate(f, start=1):
            line = line.split()
            if lineNum == 1:
                clock = int(line[-1])
                continue
            
            if lineNum == 2:
                continue

            #if its a wait
            if line[3] == '0' and line[1] == line[2]:
                counter += counter
                continue

            msgID = int(line[0])
            source = int(line[1])+1
            dest = int(line[2])+1
            numBytes = int(line[3])
            dep = int(line[4])
            timeMili = int(line[5])*1e-9*clock # multiply by a 1000 because we get how many picoseconds a cycle takes: 1000ps
            dTime = int(line[6])

            #reset dictionary
            dct = {"A" : 0, "B": 0, "t": "", "d": 0}

            #add source, dest and length
            dct["A"] = source
            dct["B"] = dest
            dct["d"] = numBytes

            #if its the first message we put it the startime
            if lineNum == counter:
                dct["t"] = startTime
                firstMsg = msgID
                msgTimeMapping[msgID] = timeMili
                listDicts.append(dct)
                counter = float('inf')
                continue

            #check dependency of the message (not considering first message)
            match dep:
                case 0 | 4:
                    delta = timeMili - msgTimeMapping[firstMsg]

                    formattedTime = datetime.timedelta(milliseconds=delta)
                    #adding time to dict for independent messages
                    dct["t"] = startTime + formattedTime

                    #adding time(in microseconds) and message ID to mapping
                    msgTimeMapping[msgID] = timeMili

                #if its a receive dependency:
                case 2 | 6:

                    #get transmission time of the message
                    transTime = transmissionTime(baseDelay, numBytes, linkCap)

                    #get the timestamp it was received considering send and transmission time
                    recvTime = msgTimeMapping[dTime] + transTime

                    sendTime = timeMili + recvTime

                    delta = sendTime - msgTimeMapping[firstMsg]

                    formattedTime = datetime.timedelta(milliseconds=delta)

                    #add send timestamp of message in microseconds to the dictionary
                    dct["t"] = startTime + formattedTime

                    #adding timestamp (in microseconds) and message ID to mapping
                    msgTimeMapping[msgID] = sendTime

                case _:
                    #get the timestamp the message depends on
                    depTime = msgTimeMapping[dTime]

                    sendTime = timeMili + depTime

                    delta = sendTime - msgTimeMapping[firstMsg]           

                    formattedTime = datetime.timedelta(milliseconds=delta)

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
    #print(msgTimeMapping)

main("output_ClusterTest.vef", "packetsTime.yaml", "network_traffic_visualizer/data/network.yaml")