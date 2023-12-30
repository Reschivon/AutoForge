
def registerInitialState(self, gameState):
    "Pre-computes the distance between every two points."
    BustersAgent.registerInitialState(self, gameState)
    self.distancer = Distancer(gameState.data.layout, False)

def chooseAction(self, gameState):
    """
    First computes the most likely position of each ghost that has
    not yet been captured, then chooses an action that brings
    Pacman closest to the closest ghost (according to mazeDistance!).
    """
    pacmanPosition = gameState.getPacmanPosition()
    legalActions = [a for a in gameState.getLegalPacmanActions()]
    livingGhosts = gameState.getLivingGhosts()
    livingGhostPositionDistributions = [beliefs for i, beliefs in enumerate(self.ghostBeliefs)
            if livingGhosts[i + 1]]
    "*** YOUR CODE HERE ***"
    dist = self.distancer.getDistance
    ghostPositions = [distribution.argMax()
                        for distribution in livingGhostPositionDistributions]

    def dist_from_pacman(ghostPosition):
        return dist(pacmanPosition, ghostPosition)

    closestGhostPosition = min(ghostPositions, key=dist_from_pacman)

    def distance_from_closest_ghost_after_action(action):
        newPacmanPosition = Actions.getSuccessor(pacmanPosition, action)
        return dist(newPacmanPosition, closestGhostPosition)

    greedyAction = min(legalActions, key=distance_from_closest_ghost_after_action)
    return greedyAction