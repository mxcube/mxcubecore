# LIMS integration

Integrating a Laboratory Information Management System (LIMS) is an essential
part of data acquisition software. It enables the retrieval and upload of sample
and experimental data both before and during the acquisition process. It further
facilitates real-time monitoring of experimental results. MXCuBE can be
integrated with any LIMS, currently supporting ISPyB, ICAT, or both via the
AbstractLims interface.

## Background

The ISPyB LIMS system has, for a very long time, been the LIMS standard in the
MXCuBE community. There was for that reason, little need for an abstraction that
enabled the use of other systems. Several sites within the community have
started to use other LIMS systems, creating a need for a more general
abstraction within MXCuBE.

The current AbstractLims abstraction is based on the interface of the previous
ISPyBClient, which was used for communication with ISPyB. Much of the API
defined in `ISPyBClient` was kept the same so that the new
[`AbstractLims`](https://github.com/mxcube/mxcubecore/blob/3a87598e81c17edd6785c71a4800b89d87e52f98/mxcubecore/HardwareObjects/abstract/AbstractLims.py),
in an initial phase, can be used with minimal changes.

The aim of the current implementation of `AbstractLims` is to facilitate the
usage of other LIMS systems. It also allows the use of other LIMS systems in
parallel with ISPyB. It's understood that the `AbstractLims` will need to evolve
with the introduction of new LIMS systems and further development of existing
solutions.

## Authentication and authorization

The authentication and authorization of a user have traditionally been performed
in one step via the `ISPYBClient` hardware object. The authentication step has
either been done through LDAP or delegated to ISPyB. `ISPYBClient` has been
replaced by `ISPyBAbstractLIMS` and exists in two variants, one for user-based
login (`UserTypeISPyBLims`) and another one for proposal
(`ProposalTypeISPyBLims`) both of which support authentication via LDAP or
ISPyB. The possibility to authenticate via LIMS will be removed in the future,
and authentication has to be delegated to a process dedicated to authentication.

The authorization for a user to use a beamline is performed via the user portal
or LIMS system, and the policy is site-specific. A very common policy is that
user cannot log in unless there is an experiment scheduled for that user on the
given beamline.

```{attention}
The proposal based login is still maintained but it's *strongly recommended* to
migrate to user based login. The proposal based login will be deprecated in the
future.
```

### Experiment session

A user belongs to a **proposal** that has an experiment **session** scheduled
on a beamline at a given time. Only one **session** and **proposal** can be
active on a beamline at the same time. Other users beloning to the same
**proposal** can access the instrument but only as **observers**, meaning
that they can see what's being done but not control it. Users not belonging to
the currently active proposal can consequently not login (are not **authorized**
to use the instrument).

### User-based login

When user-based login is used, the user authenticates with their personal
credentials and the authorization is generally handled as described above.
There may be local deviations from this defined by the LIMS system and
HardwareObject used. Any number of users can be logged in at the same time
(only one active) as long as they belong to the **same** proposal.

### Proposal-based login

When proposal-based login is used, the user authenticates with the proposal
credentials. Only one proposal can be active at the time; however, a proposal
can be logged-in any number of times (with only one instance active at the time).


## Internal data model

The data structures passed to the LIMS system via `AbstractLims` are still, as
with `ISPyBClient`, the dictionary data structure used by the collect routines
based on `AbstractCollect` and `AbstractMultiCollect`. A deliberate choice to
leave room for discussion on the data model and make the transition into
`AbstractLims` easier. There is a longer-running discussion in the community on
the topic of defining these data structures as data classes and, more recently,
as `PyDantic` models. The dictionary structures have for that purpose been
documented in the new `AbstractLims` class.

There is an attempt to define the data structures retrieved from the LIMS system
in
[`model/lims_session.py`](https://github.com/mxcube/mxcubecore/blob/3a87598e81c17edd6785c71a4800b89d87e52f98/mxcubecore/model/lims_session.py#L1).
This data model currently defines information related to the experiment or
session. Work is needed to further develop the model so that it includes the
different data entities, such as samples.

## Abstract LIMS

The `AbstractLIMS` class contains the methods that must be implemented for any
LIMS to function properly. The following list is the result of merging, cleaning
and refactoring the methods found in `HardwareObjects/ISPyBClient.py` and
`HardwareObjects/ISPyBRestClient.py`:

```
    def get_user_name(self)
    def get_full_user_name(self)
    def login(self, login_id: str, password: str, create_session: bool)
    def get_proposals_by_user(self, login_id  str)
    def get_samples(self)
    def store_robot_action(self, proposal_id  str)
    def store_beamline_setup(self, session_id  str, bl_config_dict  dict)
    def store_image(self, image_dict  dict)
    def store_energy_scan(self, energyscan_dict  dict)
    def store_xfe_spectrum(self, xfespectrum_dict  dict)
    def store_workflow(self, workflow_dict  dict)
    def store_data_collection(self, datacollection_dict: dict, beamline_config_dict: dict)
    def update_data_collection(self, datacollection_dict: dict)
    def finalize_data_collection(self, datacollection_dict: dict)
    def update_bl_sample(self, bl_sample  str)
```

## ISPyB

### ISPyBAbstractLIMS

The former `ISPyBClient` has been refactored and renamed to `ISPyBAbstractLIMS`.
It uses the `ISPyBDataAdapter` class, a data adapter that handles all calls to
ISPyB via SOAP web services. It improves the readability and maintainability of
the code by reducing its complexity. The adapter class also provides a way to
create a ISPyB client using a different technology to communicate with ISPyB
i.e. REST instead of SAOP.

Depending on the facility, a user can be logged in as either a user or a
proposal. In the previous implementation, this logic was combined, increasing
complexity. It has now been separated into two distinct classes that inherit
from `ISPyBAbstractLIMS`: `UserTypeISPyBLims` and `ProposalTypeISPyBLims`.

A facility using the ISPyB LIMS would need to configure the lims.xml hardware
object either with `ProposalTypeISPyBLims` or `UserTypeISPyBLims`.

```{attention}
This is more or less the same configuration file as previously with
`ISPyBClient`. The difference is the class name, and that there is no login_type
configuration
```

Example:
```
<object class="ProposalTypeISPyBLims"> <!-- or <object class="UserTypeISPyBLims"> -->
  <object role="ldapServer" href="/ldapconnection" />
  <ws_root>
    https://ispyb.server.fr/ispyb/ispyb-ws/ispybWS/
  </ws_root>
  <ws_username>********</ws_username>
  <ws_password>********</ws_password>
  <object role="session" href="/session" />
  <authServerType>ldap</authServerType>
</object>
```

### Migrating to AbstractLims
To use `AbstractLims` instead of ISPyBClient, change object in the configuration
file to `ProposalTypeISPyBLims` or `UserTypeISPyBLims`, as in the example below.

```
<!--<object class="ISPyBClient"> Change to ProposalTypeISPyBLims -->
<object class="ProposalTypeISPyBLims">
  <object hwrid="/lims-rest" role="lims_rest"/>
  <object role="ldapServer" href="/ldapconnection"/>
  <object role="icat_client" href="/icat-client"/>
  <ws_root>
    https://ispyb.esrf.fr/ispyb/ispyb-ws/ispybWS/
  </ws_root>
  <ws_username>****</ws_username>
  <ws_password>****</ws_password>
  <object role="session" href="/session"/>
  <authServerType>ldap</authServerType>
</object>
```

The method `AbstractLims.login` now returns a `LimsSessionManager` [model](https://github.com/mxcube/mxcubecore/blob/3a87598e81c17edd6785c71a4800b89d87e52f98/mxcubecore/model/lims_session.py#L72) instead of a list with dictionaries.



### ICAT

Similar to ISPyB, MXCuBE can now use ICAT with the `ICATLIMS` class. Note that
`ICATLIMS` only works with user authentication.

The way a user selects their session is more flexible compared to with ISPyB,
and it also manages beamline changes (in case of breakdown), making the
configuration slightly more complex.

```
<object class="ICATLIMS">
  <ws_root>https://icatplus.server.com</ws_root>
  <loginType>user</loginType>
  <object role="session" href="/session" />
  <queue_urls>ingester:61613</queue_urls>
  <before_offset_days>20</before_offset_days>
  <after_offset_days>20</after_offset_days>
    <!--
       The list of sessions will be filtered by the override_beamline_name,
       this is needed when HWR.beamline.session.beamline_name does not match
       with the name of the instrument in the catalog
    -->
  <override_beamline_name>ID30A-1</override_beamline_name>

  <data_portal_url>https://[dataportal]/investigation/{id}/datasets</data_portal_url>
  <logbook_url>https://[dataportal]/investigation/{id}/logbook</logbook_url>
  <user_portal_url>https://[userportal]</user_portal_url>

</object>

```

### ESRFLIMS

On top of the mentioned configuration, there is a LIMS client that combines both
ISPyB and ICAT. This LIMS client has, for the time beeing been named `ESRFLIMS`
but is open for renaming. By using `ESRFLIMS` sample information can be
retrieved from either ISPyB or ICAT and the results are sent to both ISPyB and
ICAT simultaneously. The authorization is based in ICAT. The configuration
`lims.xml` relies on the previous hardware objects for ICAT (drac.xml) and ISPyB
(ispyb.xml):

```
<object class="ESRFLIMS">
  <object role="drac" href="/drac" />
  <object role="ispyb" href="/ispyb" />
</object>
```
