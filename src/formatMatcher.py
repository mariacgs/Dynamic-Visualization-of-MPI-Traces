import json
import tempfile, os
import heapq
import yaml
import sys
import datetime
import time
from collections import defaultdict

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

def emitToJSONL(fh, A, B, normTime, numBytes):
    fh.write(json.dumps({"A": A, "B": B, "tNorm": normTime, "d": numBytes}, separators=(",", ":")))
    fh.write("\n")

def chunkSortJSONL(JSONLin, tmpdir, maxLines=2_000_000):
    chunks = []
    buf = []
    count = 0
    with open(JSONLin, "r") as fh:
        for line in fh:
            obj = json.loads(line)
            buf.append((obj["tNorm"], obj))
            count += 1
            if count >= maxLines:
                buf.sort(key=lambda x: x[0])
                path = os.path.join(tmpdir, f"chunk_{len(chunks):04d}.jsonl")
                with open(path, "w") as out:
                    for _, rec in buf:
                        out.write(json.dumps(rec, separators=(",", ":")) + "\n")
                chunks.append(path)
                buf.clear()
                count = 0
    if buf:
        buf.sort(key=lambda x: x[0])
        path = os.path.join(tmpdir, f"chunk_{len(chunks):04d}.jsonl")
        with open(path, "w") as out:
            for _, rec in buf:
                out.write(json.dumps(rec, separators=(",", ":")) + "\n")
        chunks.append(path)
    return chunks

def openChunks(chunks):
    readers, heap = [], []
    for idx, path in enumerate(chunks):
        fh = open(path,"r")
        line = fh.readline()
        if not line:
            fh.close()
            continue
        obj = json.loads(line)
        readers.append(fh)
        heapq.heappush(heap, (obj["tNorm"], idx, obj))
    return readers, heap

def advanceReader(idx, readers):
    fh = readers[idx]
    line = fh.readline()
    if not line:
        fh.close()
        return None
    return json.loads(line)

def closeReaders(readers):
    for fh in readers:
        try:
            fh.close()
        except:
            pass

def mergeToYAMLandBandwidthCalc(chunks, outYAMLpath, timestampType, startTime, updateDelta, networkIn, networkOut):
    readers, heap = openChunks(chunks)
    outYAML = open(outYAMLpath, "w", buffering=1024*1024)

    linkBandwidthHistory = {}
    maxBandwidthPerLink = {}
    currentWindowBytes = {}
    currentWindowStart = 0

    def flushWindow(start):
        if not currentWindowBytes:
            return
        
        for linkKey, bytesInWindow in currentWindowBytes.items():
            bandwidthMBPS = (bytesInWindow * 8) / (updateDelta * 1e-3) / 1e6
            linkBandwidthHistory.setdefault(linkKey, []).append(bandwidthMBPS)
            prev = maxBandwidthPerLink.get(linkKey, 0)
            if bytesInWindow > prev:
                maxBandwidthPerLink[linkKey] = bytesInWindow
        currentWindowBytes.clear()

    try:
        while heap:
            tNorm, idx, obj = heapq.heappop(heap)
            A = obj["A"]
            B = obj["B"]
            d = obj["d"]

            while tNorm >= (currentWindowStart + updateDelta):
                flushWindow(currentWindowStart)
                currentWindowStart += updateDelta
            
            link = frozenset((A, B))
            currentWindowBytes[link] = currentWindowBytes.get(link, 0) + d

            if timestampType == "relative":
                formattedTime = round(0 + tNorm, 4)
                outYAML.write(f"- {{A: {A}, B: {B}, t: {formattedTime}, d: {d}}}\n")
            else:
                formattedTime = startTime + datetime.timedelta(milliseconds=tNorm)
                outYAML.write(f"- {{A: {A}, B: {B}, t: {formattedTime}, d: {d}}}\n")

            nxt = advanceReader(idx, readers)
            if nxt is not None:
                heapq.heappush(heap, (nxt["tNorm"], idx, nxt))

        flushWindow(currentWindowStart)
    finally:
        outYAML.close()
        closeReaders(readers)
    
    with open(networkIn, "r") as f:
        net = yaml.safe_load(f)

    for i in net[0]:
        link = frozenset(i['endpoints'])
        maxBandwidthBytes = maxBandwidthPerLink.get(link, 0)
        maxBandwidthMBPS = ((maxBandwidthBytes * 8) / (updateDelta * 1e-3)) / 1e6
        i["capacity"] = maxBandwidthMBPS
    net[2]["linkCap"] = "mixed"

    with open(networkOut, "w") as f:
        yaml.safe_dump(net, f)

def main(vefFile, packets, network, network2):
    baseDelay = 1.5
    startTime, simTime, linkCap, timestampType, fileType, updateDelta = processNetwork(network)

    print(linkCap)
    # Defining important data structures, functions and variables
    msgTimeMapping = {}
    meta = {}
    pending = defaultdict(list)
    depCounts = defaultdict(int)
    firstMsg = float("inf")

    def transmissionTime(IDdep):
        depNumBytes = meta[IDdep]
        numBits = depNumBytes*8
        bandwidthBitsPerSec = linkCap * 1e9
        delaySec = numBits/bandwidthBitsPerSec
        return baseDelay + (delaySec*1e3)

    def freeUp(msgID):
        msgsDepending = depCounts.get(msgID, 0)
        if msgsDepending <= 0:
            msgTimeMapping.pop(msgID, None)
            meta.pop(msgID, None)

    # FIRST PASS: get clock, first message and the amount of records that depend on another

    with open(vefFile, mode="r") as f:
        for lineNum, raw in enumerate(f, start=1):
            line = raw.split()
            if lineNum == 1:
                clock = int(line[-1])
                continue
            
            if line[0].isdigit() == False:
                continue
            
            depType = int(line[4])
            IDdep = int(line[6])
            timeMili = int(line[5])*1e-9*clock
            if IDdep == -1:
                if firstMsg > timeMili:
                    firstMsg = timeMili
            if IDdep >= 0:
                depCounts[IDdep] += 1

    # SECOND PASS: go through and build packets.yaml
    tmpDir = tempfile.mkdtemp(prefix="vef2yaml")
    JSONLpath = os.path.join(tmpDir, "packetsUnsorted.jsonl")
    JSONLfh = open(JSONLpath, "w", buffering=1024*1024)

    with open(vefFile, mode="r") as f:
        for lineNum, raw in enumerate(f, start=1):
            line = raw.split()
            if (lineNum == 1) or (line[0].isdigit() == False):
                continue

            """ MIGHT BE SOLVED """
            # if theres a barrier
            """            if line[0] == 'G0':
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
                continue"""

            msgID = int(line[0])
            source = int(line[1])+1
            dest = int(line[2])+1
            numBytes = int(line[3])
            depType = int(line[4])
            timeMili = int(line[5])*1e-9*clock # multiply by a 1000 because we get how many picoseconds a cycle takes: 1000p
            IDdep = int(line[6])

            def ready():
                match depType:
                    case 0 | 4:
                        sendTime = timeMili

                        return True, sendTime
                    case 2 | 6:
                        if (IDdep in msgTimeMapping) and (IDdep in meta):

                            #get transmission time of the message
                            transTime = transmissionTime(IDdep)

                            #get the timestamp it was received considering send and transmission time
                            recvTime = msgTimeMapping[IDdep] + transTime

                            sendTime = timeMili + recvTime
                            return True, sendTime
                        else:
                            return False, None
                    case _:
                        if IDdep in msgTimeMapping:

                            #get the timestamp the message depends on
                            depTime = msgTimeMapping[IDdep]

                            sendTime = timeMili + depTime
                            return True, sendTime   
                        else:
                            return False, None
                        
            ok, sendTime = ready()

            if not ok:
                record = (msgID, source, dest, numBytes, depType, timeMili, IDdep)
                pending[IDdep].append(record)
                meta[msgID] = numBytes
                continue

            stack = [(msgID, source, dest, numBytes, IDdep, sendTime)]
            while stack:
                curMsgID, currSource, currDest, currNumBytes, currIDdep, currSendTime =  stack.pop()
                
                #mark current record as known
                msgTimeMapping[curMsgID] = currSendTime
                meta[curMsgID] = currNumBytes

                # skip waits for emit
                if not (currNumBytes == 0 or currSource == currDest):
                    
                    # normalize time
                    delta = currSendTime - firstMsg
                    ## EMIT
                    emitToJSONL(JSONLfh, currSource, currDest, delta, currNumBytes)

                # get children taken care of
                children = pending.pop(curMsgID, [])
                for records in children:
                    pendMsgID, pendSource, pendDest, pendNumBytes, pendDepType, pendTimeMili, pendIDdep = records[:7]
                    
                    if pendDepType in (1, 5):
                        pendSendTime = currSendTime + pendTimeMili
                    
                    elif pendDepType in (2, 6):
                        pendRecvTime = currSendTime + transmissionTime(curMsgID)
                        pendSendTime = pendTimeMili + pendRecvTime
                        
                    stack.append((pendMsgID, pendSource, pendDest, pendNumBytes, pendIDdep, pendSendTime))
                
                if currIDdep >= 0:
                    depCounts[currIDdep] -= 1
                    if depCounts[currIDdep] == 0:
                        del(depCounts[currIDdep])
                        freeUp(currIDdep)
    JSONLfh.close()
    """ 
    #check dependency of the message (not considering first message)
    match depType:
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
            if IDdep in knownTime:

                #get transmission time of the message
                transTime = transmissionTime(baseDelay, numBytes, linkCap)

                #get the timestamp it was received considering send and transmission time
                recvTime = knownTime[IDdep] + transTime
                # recvTime = msgTimeMapping[IDdep] + transTime

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

            else:
                pending[IDdep].append(line)

        case _:
            if IDdep in knownTime:
                #get the timestamp the message depends on
                depTime = msgTimeMapping[IDdep]

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
            else:
                pending[IDdep].append(line)
    """
    
    print("done second pass \n")

    # split and sort chunks
    chunks = chunkSortJSONL(JSONLpath, tmpDir, maxLines=2_000_000)
    print("done split and sort \n")

    # merge the chunks, and while doing it accumulate bandwidth and write yaml file
    mergeToYAMLandBandwidthCalc(chunks, packets, timestampType, startTime, updateDelta, network, network2)
    print("DONEEE")

main("IBMTrace4Nodes.vef", "packetsDebug.yaml", "network_traffic_visualizer/data/network.yaml", "network_traffic_visualizer/data/networkDebug.yaml")