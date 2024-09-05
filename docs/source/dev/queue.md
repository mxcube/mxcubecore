# Queue system
Today's MXCuBE queue system was first implemented in version 2.x of MXCuBE. The aim was to create a queuing system that provided means for automation and that integrated well with the sample changer robots, the ISPyB LIMS system, and workflow engines. The system was also designed to be flexible to handle the rapid technical and scientific evolution of the beamlines.

To enable automatic data collection over several samples, there is a need to associate a set of tasks to be performed on the given samples. The decision was to represent the queue as a tree of nodes, where each node defines the logic for a certain task or collection protocol. Each node can have a set of child nodes that are executed after the main logic of its parent. There are no constraints on the structure of the tree, to not limit the possibilities for more complex collection protocols. The nesting and reuse of the various types of nodes can be done freely. For conventional collections with a sample changer containing pins with samples. A sample node, for example, defines how a sample is mounted, and its child nodes define what is done on that sample once it is mounted.

```{figure} /assets/queue_overview_node_concept.svg
:width: 400
:alt: Queue overview node concept

*Typical structure of a queue for conventional colletions with sample changer containing pins with samples.*
```

```{attention}
There are no constraints on the structure of the tree. However, today: the top level always contains sample nodes,
and the nesting occurs at the group level. The depth of nesting is commonly 3 - Sample -
Data collection group - Datacollection.Workflows and more complex data collection strategies might however use more levels. Group is the name given to a node that groups together several other nodes, for instance, data collections. A group is just like any other node and can have its behavior defined in an `execute` method. A group can, for instance, commonly be a workflow that consists of several different steps.
```

```{figure} /assets/queue_complex_node_concept.svg
:width: 400
:alt: More complex queue

*A nested strucutre, A group (Group1) with several sub groups each with several data collections. Group 1 could for instance be a workflow carrying out multiple sets of data collections (each set in its own group)*
```

The execution order is depth first, so that all the children of a node are executed before the node's siblings. Each node has a `execute` method that defines its main logic and `pre_execute`and `post_execute` methods that are executed before and after the main `execute` method. There are also means to stop, pause and skip entries (by raising `QueueSkipEntryException`).

This design was thought to map well to the semantics of how data is collected with a sample changer and the upload of metadata to LIMS. The sample changer has a number of samples, each having a set of data collections (child nodes). The results are uploaded to the lims system after each data collection, (`post_execute`). Workflow engines can further group native collection protocols into grouping nodes, which in turn can be used as building blocks for even more complex collection strategies.

```{figure} /assets/queue_execute_methods.svg
:alt: Queue overview node concept

*`pre_execute` and `post_execute` methods that are executed before and after the main `execute` method.*
```

The queue system and node, mentioned above, can be seen as having two conceptual parts: a behavioral part and a model part. The behavioral part consists of an object called `QueueManager` and objects are often referred to as *queue entries*. Queue entry objects are simply objects inheriting `BaseQueueEntry`, for instance `DataCollectionQueueEntry`. The queue entry objects define the behavior (logic) of a specific collection protocol. The queue consists of several queue entry objects that are executed via the `QueueManager`.

The model consists of an object called `QueueModel` that has a tree structure of `TaskNode` objects. The `TaskNode` object is often referred to as a *queue model object* and defines the data associated with a collection protocol. There is a one-to-one mapping between a specific queue model object and a specific queue entry, for example, `DataCollectionTaskNode` and `DataCollectionQueueEntry`. The mapping is defined in a structure called [MODEL_QUEUE_ENTRY_MAPPINGS](https://github.com/mxcube/mxcubecore/blob/develop/mxcubecore/queue_entry/__init__.py#L83)

The combination of a `QueueEntry` and its model (`QueueModel`) is often referred to as a *task*, and makes up the entity that will be executed when the queue is executed.

The one-to-one mapping makes it possible to represent a queue and construct the queue entries from the queue model objects. In this way, the tree of queue model objects defines the queue. A task or collection protocol can be added to the queue by adding the *queue model object* to the `QueueModel`. For instance, a rotational data collection is added to the queue by adding a `DataCollectionTaskNode` to the `QueueModel`. This method of adding tasks to the queue is used by the Workflow engines, while the interfaces directly attach a `TaskNode` object to the corresponding `QueueEntry` which is then
*enqueued*.

## Task creation - creation of QueueEntry and QueueModel
A task is created by creating a `Tasknode` and  attaching it to a corresponding `QueueEntry`. The `QueueEntry` is added or *enqueued* to the queue via the method `QueueManager.enqueue`.

### Creation of QueueEntry and QueueModel
A simple example of the creation of a task: data collection is added to a group, which in turn is added to a sample.
```
# View is either a Qt view or a Mock object
view = Mock()

# The sample_model and sample_entry belong to the sample to which
# we would like to add the task.
# sample_model, sample_entry

# In the Qt verison this item is displayed in the queue while its
# not displayed at all in the Web version
group_model = qmo.TaskGroup()
group_entry = qe.TaskGroupQueueEntry(view, group_model)

dc_model = qmo.DataCollection()
dc_entry = qe.DataCollectionQueueEntry(view, dc_model)

HWR.beamline.queue_model.add_child(sample_model, group_model)
HWR.beamline.queue_model.add_child(group_model, dc_model)

sample_entry.enqueue(group_entry)
group_entry.enqueue(dc_entry)
```

A task can either be enqueued explicitly through the `BaseQueueEntry.enqueue` or via the `child_added` signal emitted by the `QueueModel.add_child` function. In the Web version, the `enqueue` method is used for everything that is added directly from the interface, and the `child_added` signal is used for everything else, such as workflows and characterisation results. The code for this is located in `mxcubeweb.components.queue` in the methods called add_**task_type**, for instance `add_data_collection`. In the Qt version, the creation is done via the `child_added` signal. The queue model object is created in the user interface, and then through `QueueModel.add_child` signal that calls`QueueModel.view_created` that performs `BaseQueueEntry.enqueue`.

### Differences between the Web and the Qt user interfaces
When the Web interface was designed, the scientists wanted to change some aspects of how the queue operates and how it is presented to the user. The decision was to work on one sample at a time, instead of the entire queue at once, as is done in the Qt version. This also means that the Web interface is centered around displaying the contents of the queue for one sample at the time. It was also decided to not display `DataCollectionGroupQueueEntry` in the queue. The `DataCollectionGroupQueueEntry` still exists in the Web interface, but there is no view created for it.

On a technical level, there is a tight coupling between the `QueueEntry` base class and a Qt view object that makes the creation of the `QueueEntry` object slightly different between the two user interfaces (Qt and Web). To handle the tight coupling to Qt, a `Mock` object is used in the web version instead of a Qt View. The Qt interface can access the view directly via a reference, something that is impossible in the Web interface. Because the view and the `QueueEntry` do not execute in the same process, updates to the view in the web version are instead done through signals passed over websockets to the client.

## Execution
As mentioned above, the execution order is depth first, so that all the children of a node are executed before the node's siblings. Each node has a `execute` method that defines its main logic and `pre_execute` and `post_execute` methods that are run before and after the main `execute` method. The `execute` and `pre_execute` methods of an entry runs before the `execute` method of its children. The `post_execute` method of an entry will run after its children have executed.

A queue entry has a state internally called `status` that indicates the state of execution; the state can be one of:

 - `SUCCESS`: The item was executed successfully, indicated with a green color in the UI
 - `WARNING`: The item was executed successfully, but there was a problem with, for instance, processing. For example, a characterization that finishes without a collection plan or a collection without diffraction. Warning is indicated in yellow in the UI
 - `FAILED`: The execution failed, indicated with red in the UI
 - `SKIPPED`: Item was skipped, indicated with red in the UI
 - `RUNNING`: Item is currently being executed, indicated with blue in the UI
 - `NOT_EXECUTED`: Item has not yet been executed; the default item color is gray.

While running the queue, it emits a set of signals/events via `self.emit`. The signals are:

- `queue_entry_execute_finished`: When a queue entry finishes execution for any given reason, the queue entry in question and one of the strings (Failed, Successful, Skipped or Aborted) are passed with the signal.
- `queue_stopped`: When the queue was stopped
- `queue_paused`: When the queue was/is paused

The exception `QueueSkipEntryException` can be raised at any time to skip to the next entry in the queue. Raising `QueueSkipEntryException` will skip to the next entry at the same level as the current node, meaning that all child nodes will be skipped as well. The
status of the skipped queue entry will be set to `SKIPPED` and `queue_entry_execute_finished` will be emitted with `Skipped`

Aborting the execution of the queue is done by raising `QueueAbortedException`. The status of the queue entry will be "FAILED" and `queue_entry_execute_finished` will be emitted with `Aborted`. The exception is re-raised after being handled.

The exception `QueueExecutionException` can be raised to handle an error and skip to the
next entry. The status of the skipped queue entry will be set to `FAILED` and `queue_entry_execute_finished` will be emitted with `Failed`. The difference between `QueueSkipEntryException` is that the status is set to `Failed` instead of skipped.

Any other exception that occurs during queue entry execution will be handled in the `handle_exception` method of the executing entry, and the queue will be stopped.

### Nesting of nodes and execution
There are, as mentioned in the introduction, no constraints on the depth of the queue. An item will execute its main body of logic defined in the `exeute` method and then run its child items. The process will continue until there are no more child items to execute, and then continue with the siblings of the parent of the last executed item.

#### Web interface and nesting of items
The web interface has a flat, non-hierarchical, representation of the queue where the child items of a node are displayed under its parent item. The parent item will remain running, highlighted in blue, while the child items are being processed. An item will be highlighted in green when successfully executed and in red if something went wrong.

## Dynamically loaded queue entries
After some years of use, the developer community has found that some aspects of the queue can be improved. The queue was originally designed with a certain degree of flexibility in mind; it was initially thought that the queue was to be extended with new collection protocols occasionally, but that that the number of protocols would remain quite limited. Furthermore, the model layer `QueueModel` objects were designed as pure data-carrying objects with the intent that these objects could be instantiated from serialized data passed over an RPC protocol. The `QueueModel` objects were also originally designed to run on Python 2.4 (that was used at the time) with limimited support for typing. The `QueueModel` objects are often converted to Python dictionary data structures and passed to various parts of the application. An approach that was adapted partly because the dictionary structure is simple to serialize to a string, but also because the already existing collection routines were already using dictionaries to pass data internally.

With time, the `QueueModel` objects were extended with methods, deviating from the initial idea of them as purely data-carrying. This, to some extent, breaks compatibility with RPC protocols. Furthermore, the dictionaries not being well-defined or immutable quickly become a source of uncertainty.

A new kind of "dynamic" queue entry that can be loaded on demand has been introduced to solve some of these limitations. The new queue entry has the following properties:

- Can be self-contained within a single Python file defining the collection protocol
- Can be loaded on demand by the application
- The data model is defined by a schema (JSON Schema), via Python type hints
- The data model only contains data
- The data model and its schema are JSON-serializable and hence easy to use in message passing protocols

The new system makes it very easy to add a new collection protocol by simply adding a Python file in a certain directory (the `site_entry_path`) that is scanned when the application starts. The data model is also better defined and, to a certain extent, self-documenting. The data and the schema can easily be passed over a message queue protocol, or RPC solution. The user interface for the collection protocols can, in many cases, be automatically generated via the schema. Making it possible to add a new collection protocol without updating the user interface.

#### Creating a "dynamic" queue entry
```{attention}
The dynamic queue entry is still beeing developed and some parts especially the `DATA_MODEL` mentioned below are subject to
change.
```

The `QueueManager` looks for queue entries in the directory `mxcubecore/queue_entry`. A site-specific folder can be configured via the option `site_entry_path`. Setting `site_entry_path` will add the path `mxcubecore/HardwareObjects/[site_entry_path]/queue_entry` to the lookup path.

```
<object class="QueueManager" role="Queue">
  <!-- where SITE is for instance ALBA|DESSY|ESRF ... -->
  <site_entry_path>"SITE"</site_entry_path>
</object>
```

A queue entry needs to follow a certain convention for it to be picked by the loader. The loader will search through the modules in the lookup path and look for a class with the same name as the module and the suffix `QueueEntry` appended to it. For example, the class name for an entry in a module with the name `test_collection.py` would be `TestCollectionQueueEntry`. See the example `test_collection.py` in `mxcubecore/queue_entry`.

As with any queue entry in MXCuBE the "dynamic" queue entry also has to inherit `BaseQueueEntry` and be associated with a `QueueModel` object, for instance `DataCollection`. Using BaseQueueEntry and DataCollection making the "dynamic" queue entries behave as native queue entries. The big difference between the `dynamic` and the native queue entry lies in how the data model is defined and passed. The native queue entry uses a set of the classes defined in queue_model_objects, whereas the "dynamic" entries use a single `Pydantic` model. The excerpt from the example collection `test_collection.py` illustrates the similarities between the native and "dynamic" queue entries.

```
# Using BaseQueueEntry and DataCollection making the "Dynmaic" queue entries behave as
# native queue entries

from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry
from mxcubecore.model.queue_model_objects import (
    DataCollection,
)

class TestCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class TestCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    # The four class variables below are specific to "dynamic" queue entries
    QMO = TestCollectionQueueModel
    DATA_MODEL = TestCollectionTaskParameters
    NAME = "Test collection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: TestCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()
```

The part that differ from the native queue entry is the four class variables `QMO`, `DATA_MODEL`, `NAME` and `REQUIRES`.

- `QMO`: (Queue model object) is used internally to tell which QueueModel object this entry is assocaited with so that the entry can be added to [MODEL_QUEUE_ENTRY_MAPPINGS](https://github.com/mxcube/mxcubecore/blob/develop/mxcubecore/queue_entry/__init__.py#L83)
- `DATA_MODEL`: Specifies the Pydantic model
- `NAME`: The name of the queue entry (also the name displayed to the user)
- `REQUIRES`: A set of prerequsits that needs to be fullfilled for this entry

*Dynamic queue entry data model*
The data model `DATA_MODEL` needs to be a pydantic model; inherit `pydantic.BaseModel` and have the following four attributes:
`path_parameters`, `common_parameters`, `collection_parameters`, `user_collection_parameters` and `legacy_parameters`.

```
class TestCollectionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: TestUserCollectionParameters
    legacy_parameters: LegacyParameters
```

The task parameters have currently been split into four different parts:

- `path_parameters`: Parameters realted to the data path, complements the `PathTemplate` object
- `common_parameters`: Parameters that are common between differnt kinds of collection protocols
- `collection_parameters`: Collection parameters for the specific protocol
- `user_collection_parameters`: Collection parameters relevant to the user complements `collection_parameters`
- `legacy_parameters`: Parameters that are still beeing passed arround in the application but not used (for backward compatability)

For a complete example see: [test_collection.py](https://github.com/mxcube/mxcubecore/blob/develop/mxcubecore/queue_entry/test_collection.py)
