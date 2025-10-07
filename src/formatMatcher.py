import json
import os
import yaml
import sys
import datetime
import time
from collections import defaultdict

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
    updatedDelta = networkDict[2]["updateDelta"]

    fileType = networkDict[2]["packetsFile"]
    return startTime, simTime, linkCap, timestampType, fileType, updatedDelta

def main(vefFile, packets, network, network2):
    baseDelay = 1.5
    startTime, simTime, linkCap, timestampType, fileType, updateDelta = processNetwork(network)
    counter = 3

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
                counter += 1
                continue

            """ MIGHT BE SOLVED """
            # if theres a barrier
            if line[0] == 'G0':
                msgID = line[0] + line[3] # so id is G0 and then rank
                timeMili = int(line[7])*1e-9*clock

                match dep:
                    case 0|4:
                        msgTimeMapping[msgID] = timeMili
                    case 2|6:
                        transTime = transmissionTime(baseDelay, numBytes, linkCap)
                        recvTime = msgTimeMapping[dTime] + transTime
                        sendTime = timeMili + recvTime

                        msgTimeMapping[msgID] = sendTime
                    case _:
                        depTime = msgTimeMapping[dTime]
                        sendTime = timeMili + depTime
                        msgTimeMapping[msgID] = sendTime
                continue

            msgID = int(line[0])
            source = int(line[1])+1
            dest = int(line[2])+1
            numBytes = int(line[3])
            dep = int(line[4])
            timeMili = int(line[5])*1e-9*clock # multiply by a 1000 because we get how many picoseconds a cycle takes: 1000p
    
            if line[6][0] == 'G':
                dTime = line[6] + line[1]  # assuming source represents the rank
            
            else:
                dTime = int(line[6])

            #reset dictionary
            dct = {"A" : 0, "B": 0, "t": "", "d": 0}

            #add source, dest and length
            dct["A"] = source
            dct["B"] = dest
            dct["d"] = numBytes

            #if its the first message we put it the startime
            if lineNum == counter:
                if timestampType == "relative":
                    dct["t"] = 0.0
                else:
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

                    if timestampType == "relative":
                        dct["t"] = round(0 + delta, 4)
                    else:
                        formattedTime = datetime.timedelta(milliseconds=delta)
                        #adding time to dict for independent messages
                        dct["t"] = startTime + formattedTime

                    #adding time(in milioseconds) and message ID to mapping
                    msgTimeMapping[msgID] = timeMili

                #if its a receive dependency:
                case 2 | 6:

                    #get transmission time of the message
                    transTime = transmissionTime(baseDelay, numBytes, linkCap)

                    #get the timestamp it was received considering send and transmission time
                    recvTime = msgTimeMapping[dTime] + transTime

                    sendTime = timeMili + recvTime

                    delta = sendTime - msgTimeMapping[firstMsg]

                    if timestampType == "relative":
                        dct["t"] = round(0 + delta, 4)
                    else:
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

                    if timestampType == "relative":
                        dct["t"] = round(0 + delta, 4)
                    else: 
                        formattedTime = datetime.timedelta(milliseconds=delta)

                        #add send timestamp of message in microseconds to the dictionary
                        dct["t"] = startTime + formattedTime
                    #adding timestamp (in microseconds) and message ID to mapping
                    msgTimeMapping[msgID] = sendTime
            
            listDicts.append(dct)

    sortedList = sorted(listDicts, key= lambda x: x["t"])

    linkBandwidthHistory = defaultdict(list)
    maxBandwidthPerLink = defaultdict(int)
    currentWindowBytes = defaultdict(int)
    currentWindowStart = 0

    for msg in sortedList:
        if timestampType == "relative":
            delta = msg["t"]
        else:
            delta = (msg["t"] - startTime).total_seconds() * 1000

        while delta >= (currentWindowStart + updateDelta):
            for linkKey, bytesInWindow in currentWindowBytes.items():
                bandwidthMBPS = (bytesInWindow * 8) / (updateDelta * 1e-3) / 1e6
                linkBandwidthHistory[linkKey].append(bandwidthMBPS)

                if bytesInWindow >= maxBandwidthPerLink[linkKey]:
                    maxBandwidthPerLink[linkKey] = bytesInWindow

            currentWindowStart += updateDelta
            currentWindowBytes.clear()
        
        link = frozenset((msg["A"], msg["B"]))
        if link == frozenset({2, 4}):
            print(f"Processing 2-4 link: delta={delta}, window={currentWindowStart}, bytes={msg['d']}")
    
        currentWindowBytes[link] += msg["d"]
        
    for linkKey, bytesInWindow in currentWindowBytes.items():
        bandwidthMBPS = (bytesInWindow*8) / (updateDelta * 1e-3) / 1e6
        linkBandwidthHistory[linkKey].append(bandwidthMBPS)
        if bytesInWindow > maxBandwidthPerLink[linkKey]:
            maxBandwidthPerLink[linkKey] = bytesInWindow
    
    print("\n=== BANDWIDTH ANALYSIS ===")
    for link_key, max_bytes in maxBandwidthPerLink.items():
        max_bandwidth_mbps = (max_bytes * 8) / (updateDelta * 1e-3) / 1e6
        avg_bandwidth = sum(linkBandwidthHistory[link_key]) / len(linkBandwidthHistory[link_key])
        print(f"Link {link_key}: Max={max_bandwidth_mbps:.2f} Mbps, Avg={avg_bandwidth:.2f} Mbps, Windows={len(linkBandwidthHistory[link_key])}")


    with open(network, mode="r") as file:
        net = yaml.safe_load(file)
    
    print(net)
    for i in net[0]:
        link = frozenset(i['endpoints'])
        maxBandwidthMBPS = ((maxBandwidthPerLink[link] * 8) / (updateDelta * 1e-3)) / 1e6
        i["capacity"] = maxBandwidthMBPS
    
    maxBandwidth = max(maxBandwidthPerLink.values())
    print(maxBandwidth)
    net[2]['linkCap'] = maxBandwidth

    with open(network2, mode="w") as f:
        yaml.dump(net, f, indent=2)

    if fileType == "yaml":
        with open(packets, mode ="w") as f:
            yaml.dump(sortedList, f, indent=2)
    else:
        with open(packets, mode ="w") as f:
            json.dump(sortedList, f, indent=2)

main("data/collectiveTraceTest.vef", "packetsTRY.yaml", "network_traffic_visualizer/data/network.yaml", "network_traffic_visualizer/data/network2.yaml")