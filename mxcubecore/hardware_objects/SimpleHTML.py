import json
import base64
from PIL import Image

HTML_START = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html lang="en">
<head>
  <title>%s</title>
</head>
<body>\n"""

HTML_END = """</body>
</html>"""

COLOR_DICT = {
    "LightRed": "#FFCCCC",
    "Red": "#FE0000",
    "LightGreen": "#CCFFCC",
    "Green": "#007800",
}


def create_text(text, heading=None, color=None, bold=None):
    if heading:
        html_str = "<h%d>%s</h%d>\n" % (heading, text, heading)
    else:
        html_str = text
    return html_str


def create_image(image_path, width=None, height=None):
    html_str = '<img src="%s" title="%s"' % (image_path, image_path)
    if width:
        html_str += " width=%d" % width
    if height:
        html_str += " height=%d" % height

    html_str += "/>\n"
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
        toc_str += "<h2>%s</h2>" % title
    toc_str += "<ul>"
    for ref in ref_list:
        toc_str += '<li><a href="#%s">%s</a></li>' % (ref[0], ref[1])
    toc_str += "</ul></nav>"
    return toc_str


def create_json_images(image_list):
    json_item = {"type": "images", "items": []}
    for image in image_list:
        item = {}
        item["type"] = "image"
        item["suffix"] = image["filename"].split(".")[-1]
        item["title"] = image["title"]
        im = Image.open(image["filename"])
        item["xsize"] = im.size[0] / 2
        item["ysize"] = im.size[1] / 2
        item["value"] = base64.b64encode(open(image["filename"]).read())
        """
        if item.get("thumbnail_image_filename") is None:
            if thumbnailHeight is not None and thumbnailWidth is not None:
                item["thumbnailSuffix"] = pathToImage.split(".")[-1]
                item["thumbnailXsize"] = thumbnailHeight
                item["thumbnailYsize"] = thumbnailWidth
                item["thumbnailValue"] = base64.b64encode(open(pathToImage).read())
        else:
            item["thumbnailSuffix"] = pathToThumbnailImage.split(".")[-1]
            thumbnailIm = PIL.Image.open(pathToThumbnailImage)
            item["thumbnailXsize"] = thumbnailIm.size[0]
            item["thumbnailYsize"] = thumbnailIm.size[1]
            item["thumbnailValue"] = base64.b64encode(open(pathToThumbnailImage).read())
        """
        json_item["items"].append(item)
    return json_item


def generate_parallel_processing_report(mesh_scan_results, params_dict):
    json_dict = {"items": []}

    html_file = open(params_dict["html_file_path"], "w")
    html_file.write('<div align="CENTER">\n')

    if params_dict["lines_num"] > 1:
        json_dict["items"].append({"type": "title", "value": "Mesh scan results"})
        html_file.write(HTML_START % "Mesh scan results")
    else:
        html_file.write(HTML_START % "Line scan results")
        json_dict["items"].append({"type": "title", "value": "Line scan results"})

    html_file.write(create_image("parallel_processing_plot.png"))
    html_file.write("</br>")
    html_file.write(create_text("Scan parameters", heading=1))
    osc_range_per_line = params_dict["osc_range"] * (params_dict["images_per_line"] - 1)

    table_cells = [
        ("Number of lines", str(params_dict["lines_num"])),
        ("Frames per line", str(params_dict["images_per_line"])),
    ]
    if params_dict["lines_num"] > 1:
        table_cells.extend(
            (
                (
                    "Grid size",
                    "%d x %d microns"
                    % (
                        (params_dict["steps_x"] * params_dict["xOffset"] * 1000),
                        (params_dict["steps_y"] * params_dict["yOffset"] * 1000),
                    ),
                ),
                (
                    "Scan area",
                    "%d x %d microns"
                    % ((params_dict["dx_mm"] * 1000), (params_dict["dy_mm"] * 1000)),
                ),
                (
                    "Horizontal distance between frames",
                    "%d microns" % (params_dict["xOffset"] * 1000),
                ),
                (
                    "Vertical distance between frames",
                    "%d microns" % (params_dict["xOffset"] * 1000),
                ),
                ("Osciallation middle", "%.1f" % params_dict["osc_midle"]),
                ("Osciallation range per frame", "%.2f" % params_dict["osc_range"]),
                (
                    "Osciallation range per line",
                    "%.2f (from %.2f to %2.f)"
                    % (
                        osc_range_per_line,
                        (params_dict["osc_midle"] - osc_range_per_line / 2),
                        (params_dict["osc_midle"] + osc_range_per_line / 2),
                    ),
                ),
            )
        )
    table_rec = create_table(table_cells=table_cells, border_size=0)
    for row in table_rec:
        html_file.write(row)
    html_file.write("</br>")

    positions = mesh_scan_results.get("best_positions", [])
    if len(positions) > 0:
        html_file.write(create_text("Best position", heading=1))
        html_file.write("</br>")

        html_file.write('<font size="2">')
        table_cells = [
            [
                "%d" % positions[0]["index"],
                "<b>%.2f<b>" % positions[0]["score"],
                "<b>%d</b>" % positions[0]["spots_num"],
                "%.1f" % positions[0]["spots_resolution"],
                positions[0]["filename"],
                "%d" % (positions[0]["col"] + 0.5),
                "%d" % (positions[0]["row"] + 0.5),
            ]
        ]
        table_rec = create_table(
            [
                "Index",
                "<b>Score</b>",
                "<b>Number of spots</b>",
                "Resolution",
                "File name",
                "Column",
                "Row",
            ],
            table_cells,
        )
        for row in table_rec:
            html_file.write(row)
        html_file.write("</br>")

        if len(positions) > 1:
            html_file.write(create_text("All positions", heading=1))
            html_file.write("</br>")
            table_cells = []
            for position in positions[1:]:
                table_cells.append(
                    (
                        position["index"],
                        "<b>%.2f</b>" % position["score"],
                        "<b>%d</b>" % position["spots_num"],
                        "%.1f" % position["spots_resolution"],
                        position["filename"],
                        "%d" % (position["col"] + 0.5),
                        "%d" % (position["row"] + 0.5),
                    )
                )
            table_rec = create_table(
                [
                    "Index",
                    "<b>Score</b>",
                    "<b>Number of spots</b>",
                    "Resolution",
                    "File name",
                    "Column",
                    "Row",
                ],
                table_cells,
            )
            for row in table_rec:
                html_file.write(row)
            html_file.write("</br>")
        html_file.write("</font>")
    html_file.write("</div>\n")
    html_file.write(HTML_END)
    html_file.close()

    image = {"title": "plot", "filename": params_dict["cartography_path"]}
    json_dict["items"].append(create_json_images([image]))
    open(params_dict["json_file_path"], "w").write(json.dumps(json_dict, indent=4))
