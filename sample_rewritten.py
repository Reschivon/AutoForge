
def registerInitialState(self, gameState):
    BustersAgent.registerInitialState(self, gameState)
    self.distancer = Distancer(gameState.data.layout, False)

def chooseAction(self, gameState):
    dist = self.distancer.getDistance
    legalActions = [a for a in gameState.getLegalPacmanActions()]
    livingGhosts = gameState.getLivingGhosts()
    livingGhostPositionDistributions = [beliefs for i, beliefs in enumerate(self.ghostBeliefs)
            if livingGhosts[i + 1]]
    pacmanPosition = gameState.getPacmanPosition()

    def dist_from_pacman(ghostPosition):
        return dist(pacmanPosition, ghostPosition)
    ghostPositions = [distribution.argMax()
                        for distribution in livingGhostPositionDistributions]
    closestGhostPosition = min(ghostPositions, key=dist_from_pacman)

    def distance_from_closest_ghost_after_action(action):
        newPacmanPosition = Actions.getSuccessor(pacmanPosition, action)
        return dist(newPacmanPosition, closestGhostPosition)
    greedyAction = min(legalActions, key=distance_from_closest_ghost_after_action)
    return greedyAction