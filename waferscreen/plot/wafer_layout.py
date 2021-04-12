#example of chip_pos_label
chip_pos_label = [[-1,0],[1,3],[0,5],....]

#this part calculates the position of each resonator
for i in range(0,len(chips)):
    for j in range(0,len(resonators_on_chip)):
            res_chip_index = j
            if res_chip_index < 16.5:
                x_pos_index = 4*res_chip_index
                res_ypos_shift = -0.2
            elif res_chip_index < 32.5:
                x_pos_index = 2 + 4*(res_chip_index - 17)
                res_ypos_shift = -0.2
            elif res_chip_index < 49.5:
                x_pos_index = 1 + 4*(res_chip_index - 33)
                res_ypos_shift = 0.2
            elif res_chip_index < 65.5:
                x_pos_index = 3 + 4*(res_chip_index - 50)
                res_ypos_shift = 0.2
            res_xpos_shift = -8.125 + 16.25*x_pos_index/65.0
            chip_x_shift = chip_pos_label[i,0]*20.0 #shift of chip in x from wafer center
            chip_y_shift = chip_pos_label[i,1]*4 #shift of chip in y from wafer center
#add shift relative to chip center to shift of chip relative to center of wafer
res_wafer_x_pos = chip_x_shift + res_xpos_shift
res_wafer_y_pos = chip_y_shift + res_ypos_shift

#plot distribution of frequency errors on wafer
fig5 = plt.figure(5)
ax51 = fig5.add_subplot(111)
res_scatter = ax51.scatter(res_wafer_x_pos,res_wafer_y_pos, c=1e3*(fit_center_freqs-target_center_freqs), cmap = plt.cm.jet, vmin = -10, vmax = 10)
ax51.set_xlabel("Wafer X Position (mm)")
ax51.set_ylabel("Wafer Y Position (mm)")
# Draw chip outlines on plot
res_chips = []
# Loop over mux chip; create box at each point
kerf = 0.1
for i in range(-4,5): #-1 and +1 chips
    rect = Rectangle((-30.0+kerf/2, i*4.0-2.0 + kerf/2.0), 20.0 - kerf, 4.0-kerf)
    res_chips.append(rect)
    rect = Rectangle((10.0+kerf/2, i*4.0-2.0 + kerf/2.0), 20.0 - kerf, 4.0-kerf)
    res_chips.append(rect)
for i in range(-7,8): #center chips
    rect = Rectangle((-10.0+kerf/2, i*4.0-2.0 + kerf/2.0), 20.0 - kerf, 4.0-kerf)
    res_chips.append(rect)
# Create patch collection with specified colour/alpha
pc = PatchCollection(res_chips, facecolor='None', alpha= 1.0,
                     edgecolor= 'k')
# Add collection to axes
ax51.add_collection(pc)
#draw wafer outline on plot
wafer = Circle([0,0],25.4*3.0/2.0, edgecolor = 'k', facecolor = 'gray', alpha = 0.2)
ax51.add_artist(wafer)
#add colorbar
cbar = fig5.colorbar(res_scatter, extend = 'both')
cbar.set_label("Measured - Designed Resonator Freq. (MHz)")
#add umux chip labels
for i in range(0,len(unique_chips)):
    label_pos_x = unique_chip_pos[i,0]*20.0 - 9.5
    label_pos_y = unique_chip_pos[i,1]*4.0 + 0.75
    ax51.text(label_pos_x, label_pos_y, "B" + str(unique_chips[i]), fontsize = 8)
ax51.text(-35,35,"Wafer " + str(wafer_number), fontsize = 14)
ax51.set_xlim([-25.4*3.0/2*1.1, 25.4*3.0/2*1.1])
ax51.set_ylim([-25.4*3.0/2*1.1, 25.4*3.0/2*1.1])
ax51.set_aspect('equal')