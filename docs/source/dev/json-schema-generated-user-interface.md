# JSON-schema generated user interface

:Created: Rasmus Fogh, 20230514
:Updated:
  - 20230730
  - 20230927

After the PRs for [mxcubecore #755](https://github.com/mxcube/mxcubecore/pull/755) and [mxcubeqt #442](https://github.com/mxcube/mxcubeqt/pull/442) we have a system for code-generated interfaces that can be plugged in to both a Qt and a Web user interface. It is implemented for Qt5, and with some help it should be possible to implement a (prototype?) web interface on the same basis. After discussion with [@marcusoscarsson](https://github.com/marcus-oscarsson) the PR is now refactored to do parameter updating on the server side only, sending values back and forth as necessary through signals. The newest version is through PRs [#794 (mxcubecore)](https://github.com/mxcube/mxcubecore/pull/794) and [#453 (mxcubeqt)](https://github.com/mxcube/mxcubeqt/pull/453).

The system is used to generate parameter queries from mxcubecore (for now from the GΦL workflow). It includes a wide range of widgets; multiple nested layout fields; support for custom update functions triggered when values are edited, that can reset values of other fields or change widget colouring; field value validation; and colouring and disabling of action for invalid widgets. There are several examples of pulldown menu contents being modified depending on the values of other fields. The system is started with a `PARAMETERS_NEEDED` on signals being sent from the mxcubecore side with the JSON schemas as parameters. The UI side responds by sending a `PARAMETER_RETURN_SIGNAL` with the complete dictionary of parameter values. There is also a control parameter, that determines whether the response matches a Continue or Cancel click (closing the UI popup), or whether it is a request for a UI update. In the latter case the update is sent from the mxcubecore side with a `PARAMETER_UPDATE_SIGNAL`.

I have done my best to follow the correct practice of using JSON schemas to specify user interfaces – but possibly with mixed success. The documentation I could find was neither as clear nor as comprehensive as is the case for Qt (where it is already hard to find what you need), and the capabilities of the proposed system go rather beyond what you see in web examples. The main documentation used has been <https://rjsf-team.github.io/react-jsonschema-form/>, <https://github.com/jsonform/jsonform/wiki>, <https://www.npmjs.com/package/react-jsonschema-form-layout>, <https://ui-schema.bemit.codes/>, <https://react-jsonschema-form.readthedocs.io/en/v1.8.1/form-customization/>. Ultimately I had to invent a certain amount, which may then be inconsistent with web libraries and best practices. Hopefully someone more familiar with JSON-schema and web practice would be able to find a more correct way of handling some of the problems. One advantage is that since this system is purely internal to MXCuBE-Qt so far it can (and will) be changed to conform to the needs of the web implementation.

The only really detailed documentation available is the Qt implementation, which serves as a worked example. The attached files show screenshots of the generated interfaces (with some examples of e.g. widget colouring); the JSON schemas that generate them can be found in the mxcubecore repository, in `mxcubecore/doc/json_schema_gui` as can the parameters returned, and some examples of the response to gui update requests.


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
