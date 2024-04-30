# JSON-schema generated user interface

:Created: Rasmus Fogh, 20230514
:Updated:
  - 20230730
  - 20230927
  - 20240213

We have a system for code-generated interfaces that can be plugged in to both a Qt and a Web user interface. It is implemented for Qt5, and (as of 20240213) just about ready for testing with the web interface.

The system is used to generate parameter queries from mxcubecore (for now from the GΦL workflow). It includes a wide range of widgets; multiple nested layout fields; support for custom update functions triggered when values are edited, that can reset values of other fields, change widget colouring and pulldown enums; field value validation; and colouring and disabling of action for invalid values. There are several examples of pulldown menu contents being modified depending on the values of other fields. The system is started with a `PARAMETERS_NEEDED` on signals being sent from the mxcubecore side with the JSON schemas as parameters. The UI side responds by sending a `PARAMETER_RETURN_SIGNAL` with the complete dictionary of parameter values. There is also a control parameter, that determines whether the response matches a Continue or Cancel click (closing the UI popup), or whether it is a request for a UI update. In the latter case the update is sent from the mxcubecore side with a `PARAMETER_UPDATE_SIGNAL`.

The form of the JSON schemas used has been agreed between Rasmus Fogh, Jean-Baptiste Florial, and Marcus Oscarsson. Hopefully it fits with standard practices.

The only really detailed documentation available is the Qt implementation, which serves as a worked example. The attached files show screenshots of the generated interfaces (with some examples of e.g. widget colouring); the JSON schemas that generate them can be found in the mxcubecore repository, in `mxcubecore/doc/json_schema_gui` as can the parameters returned, and some examples of the response to gui update requests.

It should be noted that the widget update machinery supports (only) the tags 'value', 'highlight' and 'enum'. Other ooptions like 'readonly', 'is_hiddden', or 'limits' could be added later, if desired.


## Implementation

The current implementation is found in the following files. The files in mxcubecore serve for both Qt and web interfaces, whereas the files on the Qt side would need to be reimplemented/replaced for a Web interface.


### `mxcubecore/HardwareObjects/GphlWorkflow.py`

This is the client, essentially. The calls to the user interface happen entirely within then two functions `query_pre_strategy_params` and `query_collection_strategy`. `GphlWorkflow.py` also contains a number of methods `update_xyz` and `adjust_xyz` that take care of UI update requests. Signals from the UI side are received and dispatched by the `receive_pre_strategy_data` and `receive_pre_collection_data` methods, connected to signals.


### `mxcubeqt/widgets/gphl_json_dialog.py`

This contains the function that is triggered by receiving the signal (`gphlJsonParametersNeeded`), sets up the UI window with Continue button etc., and calls the function that creates the contained UI widgets.


### `mxcubeqt/widgets/jsonparamsgui.py`

This contains all the widgets, and the UI creation function (create_widgets) that transforms the input schemas to a UI. The top level widget is the LayoutWidget class. Widgets include Layout widgets (VerticalBox, HorizontalBox, and ColumnGridWqidget for gridded layouts), standard widgets for primitive types, and SelectionTable.


## Attached Examples

The JSON schemas that give rise so the images shown here can be found in the mxcubecore repository, github develop branch, in `mxcubecore/doc/json_schema_gui`.


### PreCharacterisation

Called from `query_pre_strategy_params`

![PreCharacterisation](/assets/pre-characterisation.jpeg)


### Characterisation

Called from `query_collection_strategy`

![Characterisation](/assets/characterisation.jpeg)


### PreAcquisition

Called from `query_pre_strategy_params`

Note that row 4 is selected automatically (row number shown in bold). Manually selected rows are also shown with a blue border. This could be improved.

![PreAcquisition](/assets/pre-acquisition.jpeg)


### Acquisition

Called from `query_collection_strategy`

![Acquisition](/assets/acquisition.jpeg)


### PreAcquisition_2

Called from `query_pre_strategy_params`

Another example of a pre-acquisition popup. Note that in this image row 12 is selected. The update information generated (successively) by selecting this row, by setting Crystal Lattice to 'Cubic', and by setting Space Group to F432 can be found in `update_indexing.json`, `update_lattice.json`, and `update_spacegroup.json`, respectively (in `mxcubecore/doc/json_schema_gui`)

![PreAcquisition_2](/assets/pre-acquisition-2.jpeg)


### Acquisition_3

Called from `query_collection_strategy`

Note that this is another run than `PreAcquisition_2`. This being a MAD experiment, two additional wavelengths are shown in the UI.
The dose and dose budget fields are coloured yellow as a warning because after increasing the transmission value, the dose value is higher than the dose budget. Editing the transmission field has also coloured that filed orange, as 'most recently edited'. Note that the Continue button is still active. This is done through update functions. The update information generated by changing the transmission can be found in `update_transmission.json` (in `mxcubecore/doc/json_schema_gui`)

![Acquisition_3](/assets/acquisition-3.jpeg)


### PreDiffractometerCalibration

Called from `query_pre_strategy_params`

Note that cell parameters are editable in PreDiffractometerCalibration (unlike in the very similar PreCharacterisation popup) (and have been edited in the snapshot, most recent edit showing in orange). The resolution has been set to an illegal value, colouring the field light red, and disabling the Continue button.The resolution was reset to a valid value before producing the `result.json` file.

![PreDiffractometerCalibration](/assets/pre-diffractometer-calibration.jpeg)
