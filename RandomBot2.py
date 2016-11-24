from hlt import *
from networking import *


##############################################################
#####################HELPER FUNCTIONS#########################
##############################################################

# TODO: analyze
def analyzeBoard(gameMap):
    # break the board into 5*5 squares and analyze the production of those squares
    x = 0

    width = gameMap.width
    height = gameMap.height
    summarizedBoard = {}
    while x < width:
        y = 0
        while y < height:
            production = 0
            count = 0
            for i in range(5):
                for j in range(5):
                    if(gameMap.inBounds(Location(x+i, y+j))):
                        production += gameMap.getSite(Location(x+i, y+j)).production
            summarizedBoard[str(x)+str(y)] = production
            y+=5

        x += 5
    return normalizeDict(summarizedBoard)

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

##############################################################
###################END HELPER FUNCTIONS#######################
##############################################################

# keep track of where the center pieces were going so they don't go back and forth
lastCenterMove = {}
#if we got to a enemy tile tunnel into them
tunnelEnemies = {}
# get the board
myID, gameMap = getInit()

# 15 seconds to analyze the board before we begin

productionAnalysis = analyzeBoard(gameMap)

sendInit("10thPythonBot")

while True:
    moves = []
    # make record map so we can tell which pieces have moved
    # this is useful for when a piece wants something to move to it
    edges = []
    centers = []
    moveRecord = {}
    OccupiedPosns = []
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
    # TODO: Better combat AI, maybe...
    # TODO: use the information about where the most valuable tiles are
    for posn in edges:
        if posn[0] in lastCenterMove:
            del lastCenterMove[posn[0]]
        if posn[0] in tunnelEnemies:
            moves.append(Move(posn[0], tunnelEnemies[posn[0]]))
            dir = tunnelEnemies[posn[0]]
            del tunnelEnemies[posn[0]]
            tunnelEnemies[gameMap.getLocation(posn[0], dir)] = dir
        elif (posn[1].strength != 0 and moveRecord[str(posn[0].x) + str(posn[0].y)] == 0):
            values = []
            strengths = []
            neighbours = []
            # fallback if there is only prod 0 squares adjacent
            fallback = 0
            for i in range(1, 5):
                if (gameMap.getSite(posn[0], i).owner == myID):
                    neighbours.append([gameMap.getLocation(posn[0], i),gameMap.getSite(posn[0], i) , i])
                    values.append(1000)
                    strengths.append(1000)
                else:
                    strengths.append(gameMap.getSite(posn[0], i).strength)
                    # dig into enemy territory if possible
                    if (strengths[-1] == 0):
                        emptyToObserve = gameMap.getLocation(posn[0], i)
                        #use neg val to prefer territories with more enemies
                        # since the one with least value is preferred
                        negVal = 0
                        for j in range(1, 5):
                            if(gameMap.getSite(emptyToObserve, j).owner != myID and gameMap.getSite(emptyToObserve, j).owner != 0):
                                negVal -= 1
                        values.append(negVal)
                    elif (gameMap.getSite(posn[0], i).production != 0):
                        values.append(gameMap.getSite(posn[0], i).strength / gameMap.getSite(posn[0], i).production)
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
                    if (minVal <= 0):
                        tunnelEnemies[gameMap.getLocation(posn[0], dir + 1)] = dir + 1
                else:
                    # If we can't take the most valuable square check
                    # if any adjacent edges are strong enough to help
                    for neighbour in neighbours:
                        if(myStrength + neighbour[1].strength > strengths[dir] and len(moveRecord) < 40) and neighbour[1].strength < 120:
                            dirToMove = neighbour[2]
                            if(dirToMove > 2):
                                dirToMove -= 2
                            else:
                                dirToMove += 2
                            moves.append(Move(neighbour[0], dirToMove))
                            moves.append(Move(posn[0], 0))
                            moveRecord[str(neighbour[0].x) + str(neighbour[0].y)] = 1
                        else:
                            moves.append(Move(posn[0], 0))

    # move centers to closest edge
    # use the information of where the enemies are to prefer
    # expansion away
    for posn in centers:
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
                if(curDis < minDis-2):
                    curAng = gameMap.getAngle(posn[0], target[0])
                    dir = getDirection(curAng)
                    if(prefer.index(minDir) < prefer.index(dir)):
                        minDir = dir
                    minDis = curDis

            # TODO: the farther from an edge the sooner it should move
            # Don't move too much wasting production
            if (posn[1].strength > posn[1].production * 6 or posn[1].strength > len(moveRecord)*5):
                moves.append(Move(posn[0], minDir))
                lastCenterMove[gameMap.getLocation(posn[0], minDir)] = minDir

    sendFrame(moves)
