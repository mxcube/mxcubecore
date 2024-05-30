# Queue system
Today's MXCuBE queue system was first implemented in version 2.x of MXCuBE. The aim was to create a queuing system that provided means for automation and that integrated well with the sample changer robots, the ISPyB LIMS system, and workflow engines. The system was also designed to be flexible to handle the rapid technical and scientific evolution of the beamlines.

To enable automatic data collection over several samples, there is a need to associate a set of tasks to be performed on the given samples. The decision was to represent the queue as a tree of nodes, where each node defines the logic for a certain task or collection protocol. Each node can have a set of child nodes that are executed after the main logic of its parent. There are no constraints on the structure of the tree, to not limit the possibilities for more complex collection protocols. The nesting and reuse of the various types of nodes can be done freely. For conventional collections with a sample changer containing pins with samples. A sample node, for example, defines how a sample is mounted, and its child nodes define what is done on that sample once it is mounted.

```{figure} /assets/queue_overview_node_concept.svg
:width: 400
:alt: Queue overview node concept

*Typical structure of a queue for conventional colletions with sample changer containing pins with samples.*
```

**_NOTE:_** There are no constraints on the structure of the tree. However, today: the top level always contains sample nodes,
and the nesting occurs at the group level. The depth of nesting is commonly 3 - Sample -
Data collection group - Datacollection.Workflows and more complex data collection strategies might however use more levels. Group is the name given to a node that groups together several other nodes, for instance, data collections. A group is just like any other node and can have its behavior defined in an `execute` method. A group can, for instance, commonly be a workflow that consists of several different steps.


```{figure} /assets/queue_complex_node_concept.svg
:width: 400
:alt: More complex queue

*A nested strucutre, A group (Group1) with several sub groups each with several data collections. Group 1 could for instance be a workflow carrying out multiple sets of data collections (each set in its own group)*
```

The execution order is depth first, so that all the children of a node are executed before the node's siblings. Each node has a `execute` method that defines its main logic and `pre_execute`and `post_execute` methods that are executed before and after the main `execute` method. There are also means to stop, pause and skip entries (by raising `QueueSkippEntryException`).

This design was thought to map well to the semantics of how data is collected with a sample changer and the upload of metadata to LIMS. The sample changer has a number of samples, each having a set of data collections (child nodes). The results are uploaded to the lims system after each data collection, (`post_execute`). Workflow engines can further group native collection protocols into grouping nodes, which in turn can be used as building blocks for even more complex collection strategies.

```{figure} /assets/queue_execute_methods.svg
:alt: Queue overview node concept

*`pre_execute` and `post_execute` methods that are executed before and after the main `execute` method.*
```

The queue system and node, mentioned above, can be seen as having two conceptual parts: a behavioral part and a model part. The behavioral part consists of an object called `QueueManager` and objects are often referred to as *queue entries*. Queue entry objects are simply objects inheriting `BaseQueueEntry`, for instance `DataCollectionQueueEntry`. The queue entry objects define the behavior (logic) of a specific collection protocol. The queue consists of several queue entry objects that are executed via the `QueueManager`.

The model consists of an object called `QueueModel` that has a tree structure of `TaskNode` objects. The `TaskNode` object is often referred to as a *queue model object* and defines the data associated with a collection protocol. There is a one-to-one mapping between a specific queue model object and a specific queue entry, for example, `DataCollectionTaskNode` and `DataCollectionQueueEntry`. The mapping is defined in a structure called [MODEL_QUEUE_ENTRY_MAPPINGS](https://github.com/mxcube/mxcubecore/blob/develop/mxcubecore/queue_entry/__init__.py#L83)

The combination of a `QueueEntry` and its model (`QueueModel`) is often referred to as a *task*, and makes up the entity that will be executed when the queue is executed.

The one-to-one mapping makes it possible to represent a queue and construct the queue entries from the queue model objects. In this way, the tree of queue model objects defines the queue. A task or collection protocol can be added to the queue by adding the *queue model object* to the `QueueModel`. For instance, a rotational data collection is added to the queue by adding a `DataCollectionTaskNode` to the `QueueModel`. This method of adding tasks to the queue is used by the Workflow engines, while the interfaces directly attach a `TaskNode` object to the corresponding `QueueEntry` which is then
*enqueued*

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
