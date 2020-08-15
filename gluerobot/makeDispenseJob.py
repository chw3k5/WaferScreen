"""
makeDispenseJob.py

executable to make an SRC file, required to program the glue dispense robot
JH 8/2020
"""
import numpy as np
import os
import matplotlib.pyplot as plt
from gluerobot.gluerobotlib import single_commands, geometry

parent_folder = os.path.dirname(os.path.realpath(__file__))
deg_to_rad = np.pi / 180.0


class JobCreator:
    def __init__(self, config=None, verbose=True):
        # enables print statements
        self.verbose = verbose
        # default values in the case that no config dictionary if provided
        self.filename = 'testRhomb'
        self.debug_plot = False
        self.rhombus_letter = None
        self.p = None
        self.a = None
        self.N = None
        self.alignment_pts = None
        self.mark_num = None
        self.R = None
        self.theta_o = None
        self.arc_length = None
        self.Z = None
        # unpack the configuration value if supplied 
        if config is not None:
            for key in config.keys():
                if key == "arc_length":
                    config[key] = config[key] * deg_to_rad
                elif key == "theta_o":
                    config[key] = np.array(config[key]) * deg_to_rad
                self.__setattr__(key, config[key])
        if isinstance(self.theta_o, list):
            if self.rhombus_letter == 'A':
                self.theta_o = self.theta_o[0]
            elif self.rhombus_letter == 'B':
                self.theta_o = self.theta_o[1]
            elif self.rhombus_letter == 'C':
                self.theta_o = self.theta_o[2]
        self.filename = os.path.join(parent_folder, "output", self.filename)

    def make_rhombus_src(self):
        """ Generate an SRC file for single rhombus in 3 rhombus hex layout.
            Dispenses in arc shape.

            INPUT
            filename: <str> output filename.  Will append a .src extension
            p: <float> pixel pitch mm
            a: <float> `spacer' hex side length (mm).  Spacer hex used to move three rhombii away from one another
            N: number of pixels in a row and column w/in a rhombus.  NxN assumed
            alignment_pts: x,y,z coordinates of 1st and 2nd alignment features
            mark_num: <list-like with 2 elements> image numbers corresponding to photograph of alignment feature
            rhombus_letter: <str> A,B, or C, defining which rhombus.  A,B,C center at (-x,+y), (+x,0), (-x,-y).
            R: <float> radius of arc (mm)
            theta_o: angle to arc midpoint (rad)
            arc_length: half angle of arc (rad) [+30,+210],[+90,+270],[-30,-210] for A,B,C of SO backshort
            Z: <float> height of glue dispense (mm)
            debug_plot: <bool> if true, plot the pixel center locations in glue dispenser coordiante frame

        """
        # general algorithm
        # 1) Z height commands
        # 2) line dispense setup commands
        # 3) check alignment marks
        # 4) dispense glue in a pattern
        
        # over rides if a configuration was not provided or was incomplete
        if self.p is None:
            self.p = 5.3
        if self.a is None:
            self.a = 0.410
        if self.N is None:
            self.N = 12
        if self.alignment_pts is None:
            self.alignment_pts = [(130.183, 130.674, 20.725), (103.595, 84.731, 20.725)]
        if self.mark_num is None:
            self.mark_num = (1, 2)
        if self.R is None:
            self.R = 2.7
        if self.rhombus_letter is None:
            self.rhombus_letter = 'A',
        if self.theta_o is None:
            self.theta_o = [np.pi / 6.0, 7.0 * np.pi / 6.0]
        if self.arc_length is None:
            self.arc_length = np.pi / 12.0
        if self.Z is None:
            self.Z = 33.5

        # setup + alignment commands
        a1 = single_commands["zClearanceSetup"](z_clear=3.0, absOrRel=1)
        b1 = single_commands["lineSpeed"](v=0.1)
        c1 = single_commands["lineDispenseSetup"](preMoveDelay=0, SettlingDistance=0, DwellTime=0, 
                                                  NodeTime=0, ShutoffDistance=0, ShutoffDelay=1.0)
        d1 = single_commands["alignment"](pt1=self.alignment_pts[0], pt2=self.alignment_pts[1], mark_num=self.mark_num)
        cmds = a1 + '\n' + b1 + '\n' + c1 + '\n\n' + d1 + '\n\n'

        # pixel centers of rhombus in XIC ref frame
        M = geometry["rhombusABClist"](p=self.p, a=self.a, N=self.N, rhombus_letter=self.rhombus_letter)
        if self.rhombus_letter == 'A':
            M = np.delete(M, 11, 0)  # remove glue at alignment pin
            M = np.delete(M, 10 * self.N, 0)  # remove glue at slot

        # convert from XIC coordinates to glue dispenser coordinates
        DX = self.a / 2.0 + self.p / 4;
        DY = np.sqrt(3) / 2 * self.a + np.sqrt(3) / 4 * self.p  # shift from XIC (0,0) to alignment pin position
        pt = self.alignment_pts[0][0:2] + np.array([DX, DY])
        M = geometry["convertToRobotCoordiantes"](M=M, pt=pt)

        # loop over pixel centers, add upper and lower moat glue dispense arcs
        n, m = np.shape(M)
        for ii in range(n):
            temp1 = single_commands["dispenseSymmetricArc"](pt=[M[ii][0], M[ii][1], self.Z],
                                                            R=self.R,
                                                            theta_o=self.theta_o[0],
                                                            arc_length=self.arc_length)  # upper moat
            temp2 = single_commands["dispenseSymmetricArc"](pt=[M[ii][0], M[ii][1], self.Z], R=self.R,
                                                            theta_o=self.theta_o[1],
                                         arc_length=self.arc_length)  # lower moat
            cmds = cmds + '\n' + temp1 + '\n' + temp2

        cmds = cmds + '\nEnd Program\n'
        fname = self.filename + '.src'
        f = open(fname, 'w')
        f.write(cmds)
        f.close()
        if self.verbose:
            print('Wrote glue dispensing program: %s' % fname)

        if self.debug_plot:
            # currently only shows pixel centers, not dispense points
            plt.plot(M[:, 0], M[:, 1], 'k.')
            plt.plot(self.alignment_pts[0][0], self.alignment_pts[0][1], 'ro')
            plt.plot(self.alignment_pts[1][0], self.alignment_pts[1][1], 'ro')
            plt.gca().invert_yaxis()
            plt.show()
        return cmds

    def make_3rhombus_hex_src(self):
        """ Generate an SRC file for full wafer composed of three large rhombii.
            Dispenses in arc shape.

            INPUT
            filename: <str> output filename.  Will append a .src extension
            p: <float> pixel pitch mm
            a: <float> `spacer' hex side length (mm).  Spacer hex used to move three rhombii away from one another
            N: number of pixels in a row and column w/in a rhombus.  NxN assumed
            alignment_pts: x,y,z coordinates of 1st and 2nd alignment features
            mark_num: <list-like with 2 elements> image numbers corresponding to photograph of alignment feature
            R: <float> radius of arc (mm)
            theta_o: 3 element list, each element the angles to arc midpoint (rad)
            arc_length: half angle of arc (rad)
            Z: <float> height of glue dispense (mm)
            debug_plot: <bool> if true, plot the pixel center locations in glue dispenser coordiante frame

        """

        # general algorithm
        # 1) Z height commands
        # 2) line dispense setup commands
        # 3) check alignment marks
        # 4) dispense glue in a pattern

        # over rides if a configuration was not provided or was incomplete
        if self.p is None:
            self.p = 5.3
        if self.a is None:
            self.a = 0.410
        if self.N is None:
            self.N = 12
        if self.alignment_pts is None:
            self.alignment_pts = [(130.183, 130.674, 20.725), (103.595, 84.731, 20.725)]
        if self.mark_num is None:
            self.mark_num = (1, 2)
        if self.R is None:
            self.R = 2.7
        if self.rhombus_letter is None:
            self.rhombus_letter = 'A',
        if self.theta_o is None:
            self.theta_o = [[np.pi / 6, 7 * np.pi / 6], [np.pi / 2, 3 * np.pi / 2], [-np.pi / 6, -7 * np.pi / 6]]
        if self.arc_length is None:
            self.arc_length = np.pi / 12.0
        if self.Z is None:
            self.Z = 33.5
        # setup + alignment commands
        a1 = single_commands["zClearanceSetup"](z_clear=3.0, absOrRel=1)
        b1 = single_commands["lineSpeed"](v=0.1)
        c1 = single_commands["lineDispenseSetup"](preMoveDelay=0, SettlingDistance=0, DwellTime=0, NodeTime=0, ShutoffDistance=0,
                               ShutoffDelay=1.0)
        d1 = single_commands["alignment"](pt1=self.alignment_pts[0], pt2=self.alignment_pts[1], mark_num=self.mark_num)
        cmds = a1 + '\n' + b1 + '\n' + c1 + '\n\n' + d1 + '\n\n'

        # pixel centers of rhombus in XIC ref frame
        DX = self.a / 2.0 + self.p / 4
        DY = np.sqrt(3) / 2 * self.a + np.sqrt(3) / 4 * self.p  # shift from XIC (0,0) to alignment pin position
        pt = self.alignment_pts[0][0:2] + np.array([DX, DY])  # used to center on mark_num[0]

        rhombus_letters = ['A', 'B', 'C']
        for ii in range(3):
            rL = rhombus_letters[ii]
            M = geometry["rhombusABClist"](p=self.p, a=self.a, N=self.N, rhombus_letter=rL)
            if rL == 'A':  # remove cells where no glue should be placed
                M = np.delete(M, 11, 0)  # remove glue at alignment pin
                M = np.delete(M, 10 * self.N, 0)  # remove glue at slot

            M = geometry["convertToRobotCoordiantes"](M=M, pt=pt)  # convert from XIC coordinates to glue dispenser coordinates
            # loop over pixel centers, add upper and lower moat glue dispense arcs
            n, m = np.shape(M)
            for jj in range(n):
                temp1 = single_commands["dispenseSymmetricArc"](pt=[M[jj][0], M[jj][1], self.Z], R=self.R,
                                                                theta_o=self.theta_o[ii][0],
                                                                arc_length=self.arc_length)  # upper moat
                temp2 = single_commands["dispenseSymmetricArc"](pt=[M[jj][0], M[jj][1], self.Z], R=self.R,
                                                                theta_o=self.theta_o[ii][1],
                                                                arc_length=self.arc_length)  # lower moat
                cmds = cmds + '\n' + temp1 + '\n' + temp2
            if self.debug_plot:
                # currently only shows pixel centers, not dispense points
                plt.plot(M[:, 0], M[:, 1], 'k.')

        cmds = cmds + '\nEnd Program\n'
        fname = self.filename + '.src'
        f = open(fname, 'w')
        f.write(cmds)
        f.close()
        print('Wrote glue dispensing program: %s' % fname)

        if self.debug_plot:
            plt.plot(self.alignment_pts[0][0], self.alignment_pts[0][1], 'ro')
            plt.plot(self.alignment_pts[1][0], self.alignment_pts[1][1], 'ro')
            plt.gca().invert_yaxis()
            plt.show()

        return cmds

    def write(self):
        if self.rhombus_letter == 'all':
            self.make_3rhombus_hex_src()
        else:
            self.make_rhombus_src()


if __name__ == "__main__":
    from gluerobot.configs import so_mf_uhf_cfg
    jc = JobCreator(config=so_mf_uhf_cfg, verbose=True)
    jc.write()
