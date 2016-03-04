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
       text = "<h%d>%s</h%d>\n" % (heading, text, heading)
    return text

def create_image(image_path):
    return '<img src="%s" title="%s" />\n' % (image_path, image_path)

def create_html_start(title=""):
    return HTML_START % title

def create_html_end():
    return HTML_END

def create_table(table_header=None, table_cells=None):
    string_list = []
    string_list.append("<table border='1'>")
    if table_header:
        string_list.append("<tr>") 
        header_str = ""
        for table_header in table_header:
            header_str += "<th>%s</th>" % table_header
        string_list.append(header_str)

    if table_cells:
        for table_row in table_cells:
            if table_row[0].startswith("bgcolor"):
                row_str = "<tr %s>" % table_row[0]
                table_row.pop(0)
            else:
                row_str = "<tr>" 
            for cell_str in table_row:
                if cell_str.startswith("<td bgcolor"):
                    row_str += cell_str
                else:
                    row_str += "<td>%s</td>" % cell_str
            row_str += "</tr>" 
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
    try:
       html_file = open(html_filename, "w")
       html_file.write(HTML_START % "Mesh scan results")  
       html_file.write('<div align="CENTER">\n')
       html_file.write(create_text("Mesh scan results", heading = 1))
       html_file.write(create_image("parallel_processing_result.png"))
       html_file.write("<table border='1'>\n")
       html_file.write("<tr><th>Index</th><th>Score</th><th>Number of spots</th>" + \
                       "<th>Int aver.</th><th>Resolution</th><th>Prefix</th>" +\
                       "<th>Column</th><th>Row</th>\n")
       for best_position in mesh_scan_results.get("best_positions", []):
           best_position_str = "<tr><td>%d</td>" % best_position["index"]           
           best_position_str += "<td>%.3f</td>" % best_position["score"]
           best_position_str += "<td>%.3f</td>" % best_position["spots_num"]
           best_position_str += "<td>%.3f</td>" % best_position["spots_int_aver"]
           best_position_str += "<td>%.3f</td>" % best_position["spots_resolution"]
           best_position_str += "<td>%s</td>" % best_position["filename"]
           best_position_str += "<td>%d</td>" % best_position["col"]
           best_position_str += "<td>%d</td></tr>\n" % best_position["row"]
           html_file.write(best_position_str)
       html_file.write("</table>\n") 
    except:
       pass      

    finally:
       html_file.write("</div>\n")
       html_file.write(HTML_END)
       html_file.close()
