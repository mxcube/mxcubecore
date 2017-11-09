import os


HTML_START = '''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html lang="en">
<head>
  <title>%s</title>
</head>
<body>\n'''

HTML_END ='''</body>
</html>'''

COLOR_DICT = {'LightRed': '#FFCCCC',
              'Red' : '#FE0000',
              'LightGreen' : '#CCFFCC',
              'Green': '#007800'}

def create_text(text, heading=None, color=None, bold=None):
    if heading:
        html_str = "<h%d>%s</h%d>\n" % (heading, text, heading)
    else:
        html_str = text
    return html_str

def create_image(image_path, width=None, height=None):
    html_str = '<img src="%s" title="%s"' % (image_path, image_path)
    if width:
        html_str += ' width=%d' % width
    if height:
        html_str += ' height=%d' % height

    html_str += '/>\n'
    return html_str

def create_html_start(title=""):
    return HTML_START % title

def create_html_end():
    return HTML_END

def create_table(table_header=None, table_cells=None, border_size=1):
    string_list = []
    string_list.append("<table border='%d'>" % border_size)
    if table_header:
        string_list.append("<tr>") 
        header_str = ""
        for table_header in table_header:
            if table_header.startswith("bgcolor"):
                header_str += "<th %s</th>" % table_header
            else:
                header_str += "<th>%s</th>" % table_header
        header_str += "\n"
        string_list.append(header_str)

    if table_cells:
        for table_row in table_cells:
            if str(table_row[0]).startswith("bgcolor"):
                row_str = "<tr %s>" % str(table_row[0])
                table_row.pop(0)
            else:
                row_str = "<tr>" 
            for cell in table_row:
                cell_str = str(cell)
                if cell_str.startswith("<td bgcolor"):
                    row_str += cell_str
                elif cell_str.startswith("bgcolor"):
                    row_str += "<td %s" % cell_str
                else:
                    row_str += "<td>%s</td>" % cell_str
            row_str += "</tr>\n"             
            string_list.append(row_str)            
    if table_header:
        string_list.append("</tr>")
    string_list.append("</table>")
    return string_list

def create_ref(ref_name, ref_text=None, hidden=True):
    if ref_text:
        return "<a href=#%s>%s</a>" % (ref_name, ref_text) 
    else:
        return "<a href=#%s></a>" % ref_name

def create_toc(ref_list, title):
    toc_str = '<nav role="navigation" class="table-of-contents">'
    if title:
        toc_str += '<h2>%s</h2>' % title
    toc_str += '<ul>'
    for ref in ref_list:
        toc_str += '<li><a href="#%s">%s</a></li>' % (ref[0], ref[1])
    toc_str += '</ul></nav>'
    return toc_str
          

def generate_mesh_scan_report(mesh_scan_results, mesh_scan_params, html_filename):
    if True:
       html_file = open(html_filename, "w")
       html_file.write(HTML_START % "Mesh scan results")  
       html_file.write('<div align="CENTER">\n')
       html_file.write(create_text("Mesh scan results", heading = 1))
       html_file.write(create_image("parallel_processing_result.png"))
       html_file.write("</br>")
       html_file.write(create_text("Scan parameters", heading = 1))
       osc_range_per_line = mesh_scan_params["osc_range"] * \
                            (mesh_scan_params['images_per_line'] - 1)

       table_cells = (("Number of lines", str(mesh_scan_params['lines_num'])),
                      ("Frames per line", str(mesh_scan_params['images_per_line'])),
                      ("Grid size", "%d x %d microns" %\
                       ((mesh_scan_params["steps_x"] * \
                         mesh_scan_params["xOffset"] * \
                         1000),
                        (mesh_scan_params["steps_y"] * \
                         mesh_scan_params["yOffset"] * \
                         1000))),
                      ("Scan area", "%d x %d microns" % \
                       ((mesh_scan_params['dx_mm'] * 1000),
                        (mesh_scan_params['dy_mm'] * 1000))),
                      ("Horizontal distance between frames",
                       "%d microns" % (mesh_scan_params['xOffset'] * 1000)),
                      ("Vertical distance between frames",
                       "%d microns" % (mesh_scan_params['xOffset'] * 1000)),
                      ("Osciallation middle",
                       "%.1f" % mesh_scan_params["osc_midle"]),
                      ("Osciallation range per frame",
                       "%.2f" % mesh_scan_params["osc_range"]),
                      ("Osciallation range per line",
                       "%.2f (from %.2f to %2.f)" % \
                       (osc_range_per_line,
                        (mesh_scan_params["osc_midle"] - osc_range_per_line / 2),
                        (mesh_scan_params["osc_midle"] + osc_range_per_line / 2))))
       table_rec = create_table(table_cells=table_cells, border_size=0)
       for row in table_rec:
           html_file.write(row)
       html_file.write("</br>")


       positions = mesh_scan_results.get("best_positions", [])
       if len(positions) > 0:
           html_file.write(create_text("Best position", heading=1))
           html_file.write("</br>") 

           html_file.write('<font size="2">')
           table_cells = [["%d" % positions[0]["index"],
                           "<b>%.2f<b>" % positions[0]["score"],
                           "<b>%d</b>" % positions[0]["spots_num"],
                           "%.1f" % positions[0]["spots_int_aver"],
                           "%.1f" % positions[0]["spots_resolution"],
                           positions[0]["filename"],
                           "%d" % (positions[0]["col"] + 0.5),
                           "%d" % (positions[0]["row"] + 0.5)]]
           table_rec = create_table(\
                ["Index", "<b>Score</b>", "<b>Number of spots</b>", "Int aver.",
                 "Resolution", "File name", "Column", "Row"],
                table_cells)
           for row in table_rec:
               html_file.write(row)
           html_file.write("</br>")

           if len(positions) > 1:
               html_file.write(create_text("All positions", heading=1))
               html_file.write("</br>")
               table_cells = []
               for position in positions[1:]:
                   table_cells.append((position["index"],
                                       "<b>%.2f</b>" % position["score"],
                                       "<b>%d</b>" % position["spots_num"],
                                       "%.1f" % position["spots_int_aver"],
                                       "%.1f" % position["spots_resolution"],
                                       position["filename"],
                                       "%d" % (position["col"] + 0.5),
                                       "%d" % (position["row"] + 0.5)))
               table_rec = create_table(\
                   ["Index", "<b>Score</b>", "<b>Number of spots</b>", "Int aver.",
                    "Resolution", "File name", "Column", "Row"],
                   table_cells)
               for row in table_rec:
                   html_file.write(row)
               html_file.write("</br>")
           html_file.write("</font>")
    #except:
    #   pass      

    #finally:
    html_file.write("</div>\n")
    html_file.write(HTML_END)
    html_file.close()
