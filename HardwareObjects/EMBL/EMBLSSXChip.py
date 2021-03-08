#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import logging

from gui.utils import qt_import, Colors

from mxcubecore.HardwareObjects import QtGraphicsLib as GraphicsLib
from mxcubecore.HardwareObjects.QtGraphicsManager import QtGraphicsManager

SEQ_ITEM_COLORS = (
    Colors.LIGHT_GREEN,
    Colors.LIGHT_YELLOW,
    Colors.LIGHT_BLUE,
    Colors.PLUM,
)


__credits__ = ["EMBL Hamburg"]
__category__ = "General"


class EMBLSSXChip(QtGraphicsManager):
    def __init__(self, name):

        QtGraphicsManager.__init__(self, name)

        self.chip_config_list = None
        self.current_chip_index = None

        self.dg_channels_list = []
        self.dg_channel_list_one_zero = []
        self.letters_for_descriptors_list = []
        self.compartment_enable_list = []

        self.channels = []
        self.channels_draw_items = []
        self.pos_coord = [None, None, None]

        self.graphics_coord_axes_item = None

    def init(self):
        """Reads config xml, initiates all necessary hwobj, channels and cmds
        """

        self.chip_config_list = eval(self.get_property("chip_properties", "[]"))
        self.current_chip_index = 0

        self.chip_settings = {
            "scan_rate": 0,
            "quarter_density": 0,
            "meandering": 0,
            "old_num_of_exp": 1,
            "num_channels": self.get_property("num_channels"),
            "channels": eval(self.get_property("channels")),
            "default_seq": eval(self.get_property("default_sequence")),
        }

        self.graphics_view = GraphicsLib.GraphicsView()
        self.graphics_view.scene().setSceneRect(0, 0, 340, 140)
        self.graphics_coord_axes_item = GraphicsItemCoordAxes(
            self, self.chip_settings["num_channels"]
        )
        self.graphics_view.graphics_scene.addItem(self.graphics_coord_axes_item)

    def get_chip_config_list(self):
        return self.chip_config_list

    def get_current_chip_config(self):
        return dict(
            self.chip_config_list[self.current_chip_index].items()
            + self.chip_settings.items()
        )

    def get_current_chip_index(self):
        return self.current_chip_index

    def set_current_chip_index(self, index):
        self.current_chip_index = index

    def get_chip_config_str_list(self):
        config_str_list = []
        for chip_config in self.chip_config_list:
            config_str_list.append(
                "Comp: %dx%d, Crystal: %dx%d"
                % (
                    chip_config["num_comp_h"],
                    chip_config["num_comp_v"],
                    chip_config["num_crystal_h"],
                    chip_config["num_crystal_v"],
                )
            )

        return config_str_list

    def set_config_item(self, item_name, item_value):
        if item_name in self.chip_config_list[self.current_chip_index]:
            self.chip_config_list[self.current_chip_index][item_name] = item_value
        else:
            logging.getLogger("HWR").warning(
                "Item %s not found in the config dict" % item_name
            )

    def get_dg_channels_list(self):
        return self.dg_channels_list

    def set_dg_channels_list(self, dg_channels_list):
        self.dg_channels_list = dg_channels_list

    def get_dg_channel_list_one_zero(self):
        return self.dg_channel_list_one_zero

    def set_dg_channel_list_one_zero(self, dg_channel_list_one_zero):
        self.dg_channel_list_one_zero = dg_channel_list_one_zero

    def set_channels(self, channels):
        self.chip_settings["channels"] = channels
        self.graphics_coord_axes_item.set_channels(channels)
        self.graphics_view.graphics_scene.update()

    def get_interlacings_list(self):
        current_chip_config = self.chip_config_list[self.current_chip_index]

        # 4 lists of divisors
        crystal_h_divisor_list = None
        crystal_v_divisor_list = None
        comp_h_divisor_list = None
        comp_v_divisor_list = None

        # quarter density check box state 1 - not checked; 2 - checked
        multiplier = 1  # for quarter density usage
        if current_chip_config["quarter_density"] == 1:
            multiplier = 2
        else:
            multiplier = 1

        # get values of the number of crystalalals and number of compartments
        num_crystal_h = current_chip_config["num_crystal_h"] / float(multiplier)
        num_crystal_v = current_chip_config["num_crystal_v"] / float(multiplier)
        num_comp_h = current_chip_config["num_crystal_h"]
        num_comp_v = current_chip_config["num_crystal_v"]

        # set list variables with corresponding lists
        crystal_h_divisor_list = self.get_divisors_list(num_crystal_h)
        crystal_v_divisor_list = self.get_divisors_list(num_crystal_v)
        comp_h_divisor_list = self.get_divisors_list(num_comp_h)
        comp_v_divisor_list = self.get_divisors_list(num_comp_v)

        # remove zero elements from V crystalalal and compartment lists
        del crystal_v_divisor_list[0]
        del comp_v_divisor_list[0]

        # multiply V crystalalal list with number of H crystalals
        for element in range(0, len(crystal_v_divisor_list)):
            crystal_v_divisor_list[element] = (
                crys_v_divisor_list[element] * num_crystal_h
            )

        # multiply V compartment list with number of H compartments
        for element in range(0, len(comp_v_divisor_list)):
            comp_v_divisor_list[element] = comp_v_divisor_list[element] * num_comp_h

        # create a list which contains two lists of H and V (already multiplied)
        # crystalalals
        a_list = sorted(crystal_h_divisor_list + crystal_v_divisor_list)

        # create a list which contains two lists of H and V (already multiplied)
        # compartments
        b_list = comp_h_divisor_list + comp_v_divisor_list
        b_list.sort()
        del b_list[0]  # delete first element

        # multiply B_list with number of H and V crystalalals
        for element in range(0, len(b_list)):
            b_list[element] = b_list[element] * num_crystal_h * num_crystal_v

        # concatenate a_list and b_list the sort the result
        output_list = a_list + b_list
        output_list.sort()

        return output_list

    def get_divisors_list(self, number):
        divisor_list = []

        for x in range(1, number + 1):
            if (number % x) == 0:
                divisor_list.append(x)

        if len(divisor_list) == 0:
            divisor_list.append(0)

        return divisor_list

    # creates and shows the shortlist
    def get_short_list(self):
        text_line = ""

        for element in self.dg_channels_list:
            if inte(lement).checkState() == 2:
                self.dg_channel_list_one_zero.append(1)
            else:
                self.dg_channel_list_one_zero.append(0)

        # line counter
        line_number = 1
        # enabled compartment counter
        count = 0
        # boolean to stop iterating
        done = False

        current_chip_config = self.get_current_chip_config()
        num_comp_v = current_chip_config["num_comp_v"]
        num_comp_h = current_chip_config["num_comp_h"]

        if current_chip_config["quarter_density"] == 1:
            # reduce number of features by 2 if quarter density is enabled
            num_crystal_h = current_chip_config["num_crystal_h"] / 2
            num_crystal_v = current_chip_config["num_crystal_v"] / 2
            line_number = 1

            # loops through all compartments and features
            for n_cv in range(0, num_comp_v):
                for n_ch in range(0, num_comp_h):
                    # checks for enabled compartments
                    if (
                        n_cv != self.compartment_enable_list[count][0]
                        or n_ch != self.compartment_enable_list[count][1]
                    ):
                        continue

                    for n_fv in range(0, num_crystal_v):
                        for n_fh in range(0, num_crystal_h):
                            for exposure in range(
                                0, len(self.dg_channel_list_one_zero) / 4
                            ):

                                # meandering
                                if current_chip_config["meandering"]:
                                    # checks wether n_fv is odd or even, then creates
                                    # modified_n_fh
                                    if n_fv % 2 != 0:
                                        modified_n_fh = num_crystal_h - n_fh - 1
                                    else:
                                        modified_n_fh = n_fh
                                else:
                                    modified_n_fh = n_fh

                                line_keeper = (
                                    str(line_number)
                                    + ";"
                                    + self.from_loop_to_string(
                                        n_cv, n_ch, 2 * n_fv, 2 * modified_n_fh
                                    )
                                    + ";"
                                    + str(0)
                                    + ";"
                                    + str(nCv)
                                    + ";"
                                    + str(nCh)
                                    + ";"
                                    + str(2 * nFv)
                                    + ";"
                                )
                                line_keeper = (
                                    line_keeper
                                    + str(2 * n_fh)
                                    + ";"
                                    + str(0)
                                    + ";"
                                    + str(0)
                                    + ";"
                                    + str(dg_channel_list_one_zero[exposure * 4])
                                    + ";"
                                    + str(
                                        self.dg_channes_list_one_zero[exposure * 4 + 1]
                                    )
                                    + ";"
                                )
                                line_keeper = (
                                    line_keeper
                                    + str(dg_channel_list_one_zero[exposure * 4 + 2])
                                    + ";"
                                    + str(
                                        self.dg_channes_list_one_zero[exposure * 4 + 3]
                                    )
                                    + ";"
                                    + str(0)
                                    + ";\n"
                                )
                                text_line = textLine + line_keeper

                                line_number = line_number + 1  # update line number

                    count = count + 1
                    if count > len(self.compartment_enable_list) - 1:
                        done = True
                        break
                # break the whole loop system when count is bigger than the enabled
                # compartments list length
                if done == True:
                    break

        else:
            line_number = 1
            # loops through all compartments and features
            for n_cv in range(0, num_comp_v):
                for n_ch in range(0, num_comp_h):
                    # checks for enabled compartments
                    if (
                        n_cv != self.compartment_enable_list[count][0]
                        or n_ch != self.compartment_enable_list[count][1]
                    ):
                        continue

                    for n_fv in range(0, num_crystal_v):
                        for n_fh in range(0, num_crystal_h):
                            for exposure in range(0, len(dg_channel_list_one_zero) / 4):

                                # meandering
                                if meandering == 1:
                                    # checks wether n_fv is odd or even, then creates
                                    # modified_n_fh
                                    if n_fv % 2 != 0:
                                        modified_n_fh = num_crystal_h - n_fh - 1
                                    else:
                                        modified_n_fh = n_fh
                                else:
                                    modified_n_fh = n_fh

                                line_keeper = (
                                    str(line_number)
                                    + ";"
                                    + self.from_loop_to_string(
                                        n_cv, n_ch, n_fv, modified_n_fh
                                    )
                                    + ";"
                                    + str(0)
                                    + ";"
                                    + str(nCv)
                                    + ";"
                                    + str(nCh)
                                    + ";"
                                    + str(nFv)
                                    + ";"
                                )
                                line_keeper = (
                                    line_keeper
                                    + str(n_fh)
                                    + ";"
                                    + str(0)
                                    + ";"
                                    + str(0)
                                    + ";"
                                    + str(self.dg_channel_list_one_zero[exposure * 4])
                                    + ";"
                                    + str(
                                        self.dg_channes_list_one_zero[exposure * 4 + 1]
                                    )
                                    + ";"
                                )
                                line_keeper = (
                                    line_keeper
                                    + str(
                                        self.dg_channel_list_one_zero[exposure * 4 + 2]
                                    )
                                    + ";"
                                    + str(
                                        self.dg_channes_list_one_zero[exposure * 4 + 3]
                                    )
                                    + ";"
                                    + str(0)
                                    + ";\n"
                                )
                                text_line = text_line + line_keeper

                                line_number = line_number + 1  # update line number
                    count = count + 1
                    if count > len(self.compartment_enable_list) - 1:
                        done = True
                        break
                # break the whole loop system when count is bigger than the enabled
                # compartments list length
                if done == True:
                    break

        # remove disabled compartments from the string
        # enabledCompartments_text_line = self.remove_disabled_compartments(textLine)
        # add text to the screen

        self.dg_channel_list_one_zero = []

        return text_line

    # converts 4 numbers from loops into a string (B3_cd)
    def from_loop_to_string(self, n_cv, n_ch, n_fv, n_fh):
        capital_letter_start_point = ord("A")
        # smallLetterStartPoint = ord('a')

        # set the int value of character A and a in unicode
        output_string = (
            chr(capital_letter_start_point + n_cv)
            + str(n_ch + 1)
            + "_"
            + self.letters_for_descriptors_list[n_fv]
            + self.letters_for_descriptors_list[n_fh]
        )

        return output_string

    # saves chip data in a new file
    def save_chip_data(self, filename):
        f = open(filename, "w+")
        f.write("[main]\n")

        current_chip_config = self.chip_config_list[self.current_chip_index]
        string_line = "%.9E" % Decimal(current_chip_config["crystal_h_pitch"])
        f.write("chip data.crystal H pitch (um)=%s\n" % string_line.replace(".", ","))
        string_line = "%.9E" % Decimal(current_chip_config["crystal_v_pitch"])
        f.write("chip data.crystal V pitch (um)=%s\n" % string_line.replace(".", ","))
        string_line = "%.9E" % Decimal(current_chip_config["comp_h_pitch"])
        f.write(
            "chip data.compartment H pitch (um)=%s\n" % string_line.replace(".", ",")
        )
        string_line = "%.9E" % Decimal(current_chip_config["comp_v_pitch"])
        f.write(
            "chip data.compartment V pitch (um)=%s\n" % string_line.replace(".", ",")
        )
        f.write("chip data.num crystals H=%d\n" % current_chip_config["num_crystal_h"])
        f.write("chip data.num crystals V=%d\n" % current_chip_config["num_crystal_v"])
        f.write("chip data.num compartment H=%d\n" % current_chip_config["num_comp_h"])
        f.write("chip data.num compartment V=%d\n" % current_chip_config["num_comp_v"])
        f.close()

    # returns a list of letters for descriptors
    def create_descriptors_list(self):
        self.letters_for_descriptors_list = []
        capital_letter_start_point = ord("A")
        small_letter_start_point = ord("a")
        number_start_point = ord("0")

        for element in range(0, 26):
            self.letters_for_descriptors_list.append(
                chr(small_letter_start_point + element)
            )

        for element in range(0, 26):
            self.letters_for_descriptors_list.append(
                chr(capital_letter_start_point + element)
            )

        for element in range(0, 10):
            self.letters_for_descriptors_list.append(chr(number_start_point + element))


class GraphicsItemCoordAxes(GraphicsLib.GraphicsItem):
    def __init__(self, parent, num_channels):
        GraphicsLib.GraphicsItem.__init__(self, parent, position_x=0, position_y=0)

        self.num_channels = num_channels
        self.channels = []

        self.custom_pen.setWidth(1)
        self.custom_pen.setColor(qt_import.Qt.black)

    def set_channels(self, channels):
        self.channels = channels

    def paint(self, painter, option, widget):
        scene_width = self.scene().width()
        scene_height = self.scene().height()

        self.custom_brush.setColor(Colors.LIGHT_BLUE)
        painter.setBrush(self.custom_brush)

        offset_x = 5
        offset_y = 0
        height = 30

        self.custom_pen.setColor(Colors.LIGHT_GRAY)
        painter.setPen(self.custom_pen)

        if self.channels:
            self.custom_pen.setColor(Colors.LIGHT_GRAY)
            self.custom_pen.setStyle(qt_import.Qt.DotLine)
            painter.setPen(self.custom_pen)
            # Draw delay reference lines

            max_length = 0
            for channels in self.channels:
                if channels is not None:
                    if channels[1] + channels[2] > max_length:
                        max_length = channels[1] + channels[2]

            self.custom_pen.setColor(Colors.BLACK)
            self.custom_pen.setStyle(qt_import.Qt.SolidLine)
            painter.setPen(self.custom_pen)

            for index, channels in enumerate(self.channels[::-1]):
                if channels is not None:
                    start_x = (
                        offset_x
                        + (scene_width - offset_x * 2) / max_length * channels[1]
                    )
                    size_x = (scene_width - offset_x * 2) / max_length * channels[2]
                    # start_y = scene_height - (scene_height - offset_y - 20) / self.num_channels * index  - offset_y - scene_height / self.num_channels / 2
                    start_y = scene_height - height * (index + 1) - offset_y
                    painter.drawRect(start_x, start_y, size_x, height)

        # Draw x and y axes
        painter.drawLine(offset_x, offset_y, offset_x, scene_height - offset_y)
        for index in range(self.num_channels):
            y_pos = (
                scene_height
                - (scene_height - offset_y - 20) / self.num_channels * index
                - offset_y
            )
            painter.drawLine(offset_x, y_pos, scene_width - 10, y_pos)
