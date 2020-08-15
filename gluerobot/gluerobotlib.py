"""
gluerobotlib.py

library of functions to construct a .src file to control the Nordson glue dispensing robot

The software is structured to work off of pixel centers, in which there may be multiple
glue dispense points per pixel.  Software originally developed for SO/AliCPT backshort
moat filling with CR-110.

Note some manual intervention required.  There does not appear to be a way to ask the software
what the current offsets are (both camera to tip offset and Z tip to workpiece).
The software is written to provide coordinates relative to the 1st fiducial mark (ie alignment mark).
These coordinates are for the location of the *camera* not the tip.  Therefore the camera to tip offset
will need to be subtracted from all these coordinates.  Additionally the Z coordinates should be
replaced as well with something measured.

JH 8/2020
"""

import numpy as np
import matplotlib.pyplot as plt


# single command level functions ------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------------

single_commands = {}


def sc(func):
    # puts all of the single command functions into a dictionary at import import time
    single_commands[func.__name__] = func
    return func


@sc
def alignment(pt1=(130.183, 130.674, 20.725), pt2=(103.595, 84.731, 20.725), mark_num=(1, 2)):
    """ Command to align X,Y and angle of part
        INPUT
        pt1: x,y,z of 1st alignment feature
        pt2: x,y,z location of 2nd alignment feature
        mark_num: <list-like with 2 elements> image numbers corresponding to photograph of alignment feature
    """
    return 'Vision Mark,' + '%.3f,' * 3 % tuple(pt1) + '%d' % mark_num[0] + '\n''Vision Mark,' + '%.3f,' * 3 % tuple(
        pt2) + '%d' % mark_num[1] + '\nRead Vision'


@sc
def lineDispenseSetup(preMoveDelay=0, SettlingDistance=0, DwellTime=1, NodeTime=0, ShutoffDistance=0, ShutoffDelay=1.5):
    """ line dispense setup command

        INPUT
        preMoveDelay:
        SettlingDistance:
        DwellTime:
        NodeTime:
        ShutoffDistance:
        ShutoffDelay:
    """

    return 'Line dispense Setup' + ',%.1f' * 6 % (
    preMoveDelay, SettlingDistance, DwellTime, NodeTime, ShutoffDistance, ShutoffDelay)


@sc
def zClearanceSetup(z_clear=3.0, absOrRel=1):
    """
    z_clear: distance (mm) to raise tip between two glue dispenses when moving between two locations
    absOrRel: <bool> 0=absolute (0mm is heighest point, + is closer to work surface), 1=relative
    """
    return 'Z Clearance Setup,%.3f,%d' % (z_clear, absOrRel)


@sc
def lineSpeed(v=0.1):
    """ speed during a line glue dispense
        INPUT v: velocity in mm/s """
    return 'Line Speed,%.1f' % v


@sc
def lineDispense(pt1, pt2):
    """ glue line which starts at pt1 and goes to pt2 """
    return 'Line Start' + ',%.3f' * 3 % pt1 + '\nLine End' + ',%.3f' * 3 % pt2


@sc
def dispenseArc(pts):
    """ dispense glue in an arc pattern, starting at pts[0], going through pts[1],
        and ending at pts[2]
    """
    return 'Line Start' + ',%.3f' * 3 % tuple(pts[0]) + '\nArc Point' + ',%.3f' * 3 % tuple(
        pts[1]) + '\nLine End' + ',%.3f' * 3 % tuple(pts[2])


@sc
def dispenseSymmetricArc(pt, R=2.7, theta_o=np.pi / 6., arc_length=np.pi / 9):
    """ dispense glue in an arc pattern at radius R from central point pt.
        Midpoint of arc at theta_o with angular extent +/- arc_length

        INPUT
        pt: x,y,z coordiante of center of circle (pixel center in practice)
        R: radius of arc (mm)
        theta_o: angle to arc midpoint (rad)
        arc_length: half angle of arc (rad)
    """

    x = R * np.cos(arc_length);
    y = R * np.sin(arc_length)
    # make 2D points pointing in +x direction
    pt0 = np.array([x, y])
    pt1 = np.array([R, 0])
    pt2 = np.array([x, -y])
    pts = [pt0, pt1, pt2]
    for ii in range(3):
        M = rotateXY(pts[ii].transpose(), theta_o)
        pts[ii] = pt + np.array([M[0], -1 * M[1], 0])  # need to flip y for glue dispense reference frame coordinates
        # pts[ii]=pt + np.array([M[0],M[1],0])
    return dispenseArc(pts)


### geometry functions ------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------

geometry = {}


def g(func):
    # puts all of the geometry functions into a dictionary at import import time
    geometry[func.__name__] = func
    return func


@g
def rhombusLocations(p=5.3, N=12):
    ''' return NxNx2 array of the rhombus pattern used in OMT hex arrays.
        Placed in 1st quadrant (+x,+y), with M[0,0] at the origin

        INPUT
        p: pixel pitch (mm)
        N: number of pixels in a row and column w/in a rhombus.  NxN assumed

        RETURN:
        M: NxNx2 numpy array.  M[ii,jj] returns the x,y location of the pixel indexed by ii,jj
        ii is the row, jj is the column
    '''
    M = np.zeros((N, N, 2))
    for ii in range(N):  # loop over rows
        for jj in range(N):  # loop over columns
            M[ii, jj, :] = np.array([jj + 0.5 * ii, ii * np.sqrt(3) / 2]) * p
    return M


@g
def convertRhombusLocationsToList(M):
    """ Converts format of rhombusLocations() into (N*N)x2 array.
        This is more convenient for data manipulation.

        INPUT: M, output of rhombusLocations()
        RETURN: N*N x 2 array
    """
    A, B, C = np.shape(M)
    # DD = np.zeros((A*B,2))
    DD = []
    for ii in range(A):  # loop over rows
        for jj in range(B):  # loop over columns
            DD.append(np.array(M[ii, jj]))
    return np.array(DD)


@g
def rhombusABClist(p=5.3, a=0.410, N=12, rhombus_letter='A'):
    """ creates an (N*N)x2 array of (x,y) coordiantes for the center of a
        pixel.  Viewpoint from perspective of XIC layout, looking at the device side.
        Origin is (0,0) in XIC layout.

        INPUT
        p: <float> pixel pitch (mm)
        a: <float> `spacer' hex side length (mm).  Spacer hex used to move three rhombii away from one another
        N: <int> number of pixels in a row (or column)
        rhombus_letter: <str> A,B, or C, defining which rhombus.  A,B,C center at (-x,+y), (+x,0), (-x,-y).

        OUTPUT: N*N x 2 array of pixel centers for selected rhombus
    """
    if rhombus_letter == 'A':
        t = 0
    if rhombus_letter == 'B':
        t = 4 * np.pi / 3
    elif rhombus_letter == 'C':
        t = 2 * np.pi / 3
    DX = -p * N - a / 2.0 + 0.75 * p;
    DY = np.sqrt(3) / 2 * a + np.sqrt(3) / 4 * p
    # DX = -p*(N-1) ; DY = 0
    M = rhombusLocations(p, N)
    Mlist = convertRhombusLocationsToList(M) + np.array([DX, DY])
    if rhombus_letter != 'A':
        n, m = np.shape(Mlist)
        for ii in range(n):
            pt = rotateXY(Mlist[ii, :].transpose(), t=t)
            Mlist[ii, :] = pt
            # print(np.shape(pt.transpose()))
    return Mlist


@g
def plot3rhombusHex(p=5.3, a=.410, N=12):
    """ plot pixel centers in the 3-rhombus hex layout scheme """
    labels = ['bo-', 'go-', 'ro-']
    letters = ['A', 'B', 'C']
    for ii in range(3):
        M = rhombusABClist(p=p, a=a, N=N, rhombus_letter=letters[ii])
        plt.plot(M[:, 0], M[:, 1], labels[ii])
    plt.show()


@g
def convertToRobotCoordiantes(M, pt, p=5.3):
    """ convert of XIC layout coordiantes to glue dispensing robot coordinates.
        Note glue dispense coordiante system as y -> -y.
        INPUT
        M: Nx2 array of coordinates
    """

    M[:, 1] = -1 * M[:, 1]
    M = M + np.array(pt)
    return M


@g
def rotateXY(M, t=2 * np.pi / 3):
    """ rotate M=(x,y) pair by t radians.  +t is ccw """
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    return np.matmul(R, M)


# full script writing modules ------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------



