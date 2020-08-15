# configuration for SO MF and UHF array moat filling
so_mf_uhf_cfg = {"filename": "so_mf_uhf_moatfill",
                 "debug_plot": True,
                 "rhombus_letter": "all",  # A, B, C, or all
                 "p": 5.3,  # pitch (mm)
                 "a": 0.410,  # spacer hex side length (mm)
                 "N": 12,  # number pixels per row/columns
                 "alignment_pts": [[130.183, 130.674, 20.725], [103.595, 84.731, 20.725]],  # locations of marks
                 "mark_num": [1, 2],  # mark numbers (indicies of alignment photos)
                 "R": 2.7,  # distance pixel center to middle of glue arc
                 'theta_o': [[30, 210], [90, 270], [-30, -210]],  # angular orientation of moat arcs
                 "arc_length": 15,  # length (angle in deg) for glue dispenser to travel in an arc
                 "Z": 33.5  # dispenser height
                 }





