from hlt import *
from networking import *



##############################################################
#####################HELPER FUNCTIONS#########################
##############################################################
# defines what directions are opposites
oppDirs = {0: -1, 1: 3, 3: 1, 2: 4, 4: 2}
# maps coordinates to their surronding production potential
# The production potential is the average of the 12 closest squares , ie
#######
###0###
##000##
#00000#
##000##
###0###
#######
#Keys are in the form "x,y"
cellPotential = {}

moveRecord = {}
# keep track of where the center pieces were going so they don't go back and forth
lastCenterMove = {}

# finds my starting position
def myStart(gameMap, myID):
    for y in range(gameMap.height):
        for x in range(gameMap.width):
            if (gameMap.getSite(Location(x, y)).owner == myID):
                return Location(x, y)
    return Location(0, 0)


# get's the diamond that is x moves away from loc and returns a list of keys, can specify wanting site
def getRing(x, loc, gameMap, site = False):
    #        N, E, S, W
    keys = []
    moves = [x, 0, 0, 0]
    lowerbound = 0
    while True:
        finalLoc = loc
        for i in range(4):
            amount = moves[i]
            while amount > 0:
                finalLoc = gameMap.getLocation(finalLoc, i + 1)
                amount -= 1
        if(site):
            keys.append(gameMap.getSite(finalLoc))
        else:
            keys.append(str(finalLoc.x) + "," + str(finalLoc.y))
        for i in range(lowerbound, 4):
            if (moves[0] == 0): lowerbound = 1
            if (i == 3 and moves[i] > 0):
                moves[i] -= 1
                moves[0] += 1
                break
            elif moves[i] > 0:
                moves[i] -= 1
                moves[i + 1] += 1
                break
        if (moves[0] == x):
            break
    return keys


def analyzeBoard(gameMap, myID):
    # analyzes the board as described in the cell potential dict
    x = 0
    width = gameMap.width
    height = gameMap.height
    while x < width:
        y = 0
        while y < height:
            sumPotential = gameMap.getSite(Location(x, y), 0).production
            closeSquares = []
            closeSquares += getRing(1, Location(x, y), gameMap, True)
            closeSquares += getRing(2, Location(x, y), gameMap, True)
            for site in closeSquares:
                sumPotential += site.production
            cellPotential[str(x) + "," + str(y)] = sumPotential
            y += 1
        x += 1
    # now that the board is broken up use the pre processing time to set a goal
    # tile that has the best production x or less distance away from the start
    # there is some overlap in testing the directions that are straight cardinals
    # TODO: Optimize X
    start = myStart(gameMap, myID)
    keyList = []
    for i in range(1, 15):
        keyList += getRing(i, start, gameMap)

    maxKey = ""
    maxVal = 0
    for key in keyList:
        if (cellPotential[key] > maxVal):
            keyloc = Location(int(key.split(',')[0]), int(key.split(',')[1]))
            if(gameMap.getSite(keyloc).strength < 75):
                maxVal = cellPotential[key]
                maxKey = key

    return maxKey


def normalize(x):
    if (sum(x) != 0):
        return [i / sum(x) for i in x]
    else:
        return x

def normalizeDict(x):
    sumX = sum(x.values())
    if (sumX != 0):
         for key in x:
             x[key] = float(x[key])/float(sumX)
         return x
    else:
        return x


def isEdge(posn, gameMap):
    directions = [1, 2, 3, 4]
    for dir in directions:
        if (gameMap.getSite(posn[0], dir).owner != myID):
            return True
    return False


def getFilledPosns(edges, centers, moveRecord, OccupiedPosns, gameMap):
    for y in range(gameMap.height):
        for x in range(gameMap.width):
            currentSite = gameMap.getSite(Location(x, y))
            if currentSite.owner == myID:
                posn = [Location(x, y), currentSite]
                if (isEdge(posn, gameMap)):
                    edges.append([Location(x, y), currentSite])
                else:
                    centers.append([Location(x, y), currentSite])
                moveRecord[str(x)+str(y)] = 0
            elif currentSite.owner != 0:
                OccupiedPosns.append([Location(x, y), currentSite])


# get's an overall feel of where opponenets are
# returns an array of directions from "safest" to
# most "dangerous"
def preferredDirs(posn, OccupiedPosns, gameMap):
    pi = 3.141592
    # break all angles into 4 quadrants,
    # pick one with low variance and far distance
    avgs = [0, 0, 0, 0]  # mean
    vari = [0, 0, 0, 0]  # variance
    counts = [0, 0, 0, 0]  # absolute count
    strengths = [0, 0, 0, 0]
    for enemy in OccupiedPosns:
        curAng = gameMap.getAngle(posn[0], enemy[0])
        curDis = gameMap.getDistance(posn[0], enemy[0])
        streng = enemy[1].strength
        dirToInc = getDirection(curAng)

        avgs[dirToInc - 1] += curDis
        vari[dirToInc - 1] += (curDis) ** 2
        strengths[dirToInc - 1] += streng
        counts[dirToInc - 1] += 1

    for i in range(4):  # get actual variance
        if (counts[i] != 0): avgs[i] /= counts[i]
        vari[i] = vari[i] - avgs[i] * avgs[i]

    avgs = normalize(avgs)  # High average distance
    vari = normalize(list(map(lambda x: x ** -1 if x != 0 else 0, vari)))  # prefer low variance
    counts = normalize(list(map(lambda x: x ** -1 if x != 0 else 0, counts)))  # prefer low count
    strengths = normalize(list(map(lambda x: x ** -1 if x != 0 else 0, strengths)))  # prefer low strength
    sumUp = [a + b + c + d for a, b, c, d in zip(avgs, vari, counts, strengths)]

    return sumUp

def getDirection(curAng):
    pi = 3.141592
    dirToMove = 2  # default East
    # Angle is in radians
    if (curAng >= 0):
        if (curAng > 3 * pi / 4):
            dirToMove = 4  # West
        elif (curAng > pi / 4):
            dirToMove = 3  # South
    elif (curAng < -3 * pi / 4):
        dirToMove = 4  # West
    elif (curAng < -1 * pi / 4):
        dirToMove = 1  # North
    return dirToMove

def movesToGet(l1, l2, width, height):
    dx = l2.x - l1.x
    dy = l2.y - l1.y

    if dx > width - dx:
        dx -= width
    elif -dx > width + dx:
        dx += width

    if dy > height - dy:
        dy -= height
    elif -dy > height + dy:
        dy += height

    rtn = [0,0,0,0]
    if(dx > 0):
        rtn[1] = dx
    else:
        rtn[3] = dx*-1

    if (dy > 0):
        rtn[2] = dy
    else:
        rtn[0] = dy * -1

    return rtn

def pickCenterDir(gameMap, posn, edges):
    # keep a dict of previous moves so pieces dont ping pong
    if posn[0] in lastCenterMove:
        moves.append(Move(posn[0], lastCenterMove[posn[0]]))
        dir = lastCenterMove[posn[0]]
        del lastCenterMove[posn[0]]
        lastCenterMove[gameMap.getLocation(posn[0], dir)] = dir
    else:
        minDis = 10000
        minDir = 1
        for target in edges:
            curDis = gameMap.getDistance(posn[0], target[0])

            # move to closest edge, prefering ones close opponents
            if (curDis < minDis):
                minDis = curDis
                curAng = gameMap.getAngle(posn[0], target[0])
                minDir = getDirection(curAng)
            if (curDis == minDis):
                curAng = gameMap.getAngle(posn[0], target[0])
                dir = getDirection(curAng)
                if (prefer.index(minDir) > prefer.index(dir)):
                    minDir = dir
                    minDis = curDis

        # TODO: the farther from an edge the sooner it should move
        # Don't move too much wasting production
        # TODO: Optimze production multiplier and other constant
        if (posn[1].strength > posn[1].production * 6 or posn[1].strength * minDis > 600):
            moves.append(Move(posn[0], minDir))
            lastCenterMove[gameMap.getLocation(posn[0], minDir)] = minDir

def pickEdgeDir(gameMap, posn, addedStrength = 0):
    values = []
    strengths = []
    neighbours = []
    for i in range(1, 5):
        # don't every really want to move inwards
        if (gameMap.getSite(posn[0], i).owner == myID):
            neighbours.append([gameMap.getLocation(posn[0], i), gameMap.getSite(posn[0], i), i])
            values.append(10000)
            strengths.append(10000)
        else:
            strengths.append(gameMap.getSite(posn[0], i).strength)
            # dig into enemy territory if possible
            if (strengths[-1] == 0):
                emptyToObserve = gameMap.getLocation(posn[0], i)
                # use neg val to prefer territories with more enemies
                # since the one with least value is preferred
                negVal = 0
                for j in range(1, 5):
                    if (gameMap.getSite(emptyToObserve, j).owner != myID and gameMap.getSite(emptyToObserve,
                                                                                             j).owner != 0):
                        negVal -= 1
                values.append(negVal)
            # if there is no enemies just try to take high prod per strength tiles
            elif (gameMap.getSite(posn[0], i).production != 0):
                values.append(gameMap.getSite(posn[0], i).strength / gameMap.getSite(posn[0], i).production)
                #values.append(1/gameMap.getSite(posn[0], i).production)
            else:
                values.append(1000)

    myStrength = posn[1].strength
    if not values:
        dir = strengths.index(min(strengths))
        if (strengths[dir] < myStrength):
            moves.append(Move(posn[0], dir + 1))
        else:
            moves.append(Move(posn[0], 0))
    else:
        minVal = min(values)
        dir = values.index(minVal)
        if (strengths[dir] < myStrength):
            moves.append(Move(posn[0], dir + 1))
        elif (len(moveRecord) < 30):
            # If we can't take the most valuable square check
            # if any adjacent edges are strong enough to help
            # TODO: The edge combining code could use major improvement
            for neighbour in neighbours:
                # TODO: optimize time to stop combining edges and neighbour strength
                if (myStrength + neighbour[1].strength > strengths[dir] and neighbour[1].strength < 120):
                    dirToMove = neighbour[2]
                    if (dirToMove > 2):
                        dirToMove -= 2
                    else:
                        dirToMove += 2
                    moves.append(Move(neighbour[0], dirToMove))
                    moves.append(Move(posn[0], 0))
                    moveRecord[str(neighbour[0].x) + str(neighbour[0].y)] = 1
                else:
                    moves.append(Move(posn[0], 0))
        else:
            moves.append(Move(posn[0], 0))


##############################################################
###################END HELPER FUNCTIONS#######################
##############################################################


# get the board
myID, gameMap = getInit()

# 15 seconds to analyze the board before we begin

setGoal = analyzeBoard(gameMap, myID)



sendInit("13thPythonBot")

# tunnel to the goal we set from analyzing the board
# getting the goal and processing how to get it
goalLoc = Location(int(setGoal.split(',')[0]), int(setGoal.split(',')[1]))
tunneling = True
myLocations = []
myHead = myStart(gameMap, myID)
myLocations.append(myHead)
movesNeeded = movesToGet(myLocations[0], goalLoc, gameMap.width, gameMap.height)
dirsMoved = []

#with open("test.txt", "a") as myfile:
#    myfile.write("got end")

# array in the form of moves needed [N, E, S, W]
skipFirstGet = False
# don't bother with goal if it's too hard to get
# TODO: Optimize
if(gameMap.getSite(goalLoc).strength < 75):
    while True:
        centers = []
        edges = []
        OccupiedPosns = []
        gameMap = getFrame()
        getFilledPosns(edges, centers, moveRecord, OccupiedPosns, gameMap)
        if(sum(movesNeeded) == 0):
            # we got to our goal!
            break
        moves = []
        values = [1000,1000,1000,1000]
        strengths = [1000,1000,1000,1000]
        for i in range(4):
            if(movesNeeded[i] > 0):
                site = gameMap.getSite(myHead, i+1)
                strengths[i] = site.strength
                if(site.production > 0):
                    values[i] = site.strength/site.production
                else:
                    values[i] = site.strength*2

        dirToMove = values.index(min(values))+1
        strengthNeeded = strengths[dirToMove-1]
        totalStrength = 0
        multi = 0
        for i in range(max(len(myLocations)-4, 0), len(myLocations)):
            totalStrength += gameMap.getSite(myLocations[i]).strength + gameMap.getSite(myLocations[i]).production*multi
            multi += 1
        cascading = True
        i = max(len(myLocations)-4, 0)
        while(cascading):
            if(gameMap.getSite(myHead).strength > strengthNeeded):
                moves.append(Move(myHead, dirToMove))
                dirsMoved.append(dirToMove)
                movesNeeded[dirToMove-1] -= 1
                myHead = gameMap.getLocation(myHead, dirToMove)
                myLocations.append(myHead)
                break
            elif(totalStrength > strengthNeeded):
                # cascade the strength to the head
                for j in range(0, max(len(myLocations)-4, 0)):
                    pickEdgeDir(gameMap, [myLocations[j], gameMap.getSite(myLocations[j])])
                for posn in centers:
                    prefer = [1,2,3,4]
                    pickCenterDir(gameMap, posn, edges)
                if(i < len(myLocations) and i < len(dirsMoved)):
                    moves.append(Move(myLocations[i], dirsMoved[i]))
                    sendFrame(moves)
                    moves = []
                    gameMap = getFrame()
                    getFilledPosns(edges, centers, moveRecord, OccupiedPosns, gameMap)
                    i +=1
            else:
                break




        sendFrame(moves)


    skipFirstGet = True

while True:
    moves = []
    # make record map so we can tell which pieces have moved
    # this is useful for when a piece wants something to move to it
    edges = []
    centers = []

    OccupiedPosns = []
    if(skipFirstGet):
        skipFirstGet = False
    else:
        gameMap = getFrame()

    # get's us an array of all my posns and all opponents
    getFilledPosns(edges, centers, moveRecord,  OccupiedPosns, gameMap)

    if (len(centers) > 0):
        # get an idea of where enemies are
        sums = preferredDirs(centers[len(centers) // 2], OccupiedPosns, gameMap)
    else:
        sums = preferredDirs(edges[len(edges) // 2], OccupiedPosns, gameMap)

    # sums is a list of preferred directions
    # rank the directions
    prefer = []
    sortedSum = sorted(sums, reverse=True)
    for i in range(4):
        prefer.append(sortedSum.index(sums[i]) + 1)
        sortedSum[sortedSum.index(sums[i])] = -1

    # for edges try to expand to the most worthwhile open space
    # TODO: use the information about where the most valuable tiles are
    for posn in edges:
        if posn[0] in lastCenterMove:
            del lastCenterMove[posn[0]]
        if (posn[1].strength != 0 and moveRecord[str(posn[0].x) + str(posn[0].y)] == 0):
            pickEdgeDir(gameMap, posn)

    # move centers to closest edge
    # use the information of where the enemies are to prefer
    # expansion away
    for posn in centers:
        pickCenterDir(gameMap, posn, edges)


    sendFrame(moves)
