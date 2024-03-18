# Queue system
Today's MXCuBE queue system was first implemented in version 2.x of MXCuBE. The aim was to create a queuing system that provided means for automation and that integrated well with the sample changer robots, the ISPyB LIMS system, and workflow engines. The queue was designed to have manual and automatic modes of operation.

To enable automatic data collection over several samples, one needs to associate tasks to be performed on a set of samples. The decision was to represent the queue as a tree of nodes, where each node defines the logic for a certain task or collection protocol. Each node can have a set of child nodes that are executed after the main logic of its parent. There are no constraints on the structure of the tree to not limit the possibilities for more complex collection protocols, the nesting of the various types of nodes can be done freely. For conventional colletions with sample changer containing pins with samples. A sample node, for example, defines how a sample is mounted, and its child nodes define what is done on that sample once it is mounted.

```{figure} /assets/queue_overview_node_concept.svg
:width: 400
:alt: Queue overview node concept

*Typical structure of a queue for conventional colletions with sample changer containing pins with samples.*
```

**_NOTE:_** There are no constraints on the structure of the tree. However, today: the top level always contain sample nodes,
and the nesting occours at the group level. The depth of nesting is currently maximum (3? to be confirmed)


```{figure} /assets/queue_overview_node_complex.svg
:width: 400
:alt: Queue as bad as it gets

*A nested strcture with several wedges, one in each group*
```

The execution order is depth first, so that all the children of a node are executed before the node's siblings. Each node has a `execute` method that defines its main logic and `pre_execute`and `post_execute` methods that are executed before and after the main `execute` method.

This design was thought to map well to the semantics of how data is collected with a sample changer and the upload of metadata to LIMS. The sample changer has a number of samples, each having a set of data collections (child nodes). The results are uploaded to the lims system after each data collection, (`post_execute`). Workflow engines can further group native collection protocols into grouping nodes, which in turn can be used as building blocks for even more complex collection strategies.

```{figure} /assets/queue_execute_methods.svg
:alt: Queue overview node concept

*`pre_execute` and `post_execute` methods that are executed before and after the main `execute` method.*
```

The queue system and node, mentioned above, can be seen as having two conceptual parts: a logic part and a model part. The logic part consists of an object called `QueueManager` and objects are often referred to as *queue entries*. Queue entry objects are simply objects inheriting `BaseQueueEntry`, for instance `DataCollectionQueueEntry`. The queue entry objects define the behavior (logic) of a specific collection protocol. The queue consists of several queue entry objects that are executed via the `QueueManager`.

The model consists of an object called `QueueModel` that has a tree structure of `TaskNode` objects. The `TaskNode` object is often referred to as a *queue model object* and defines the data associated with a collection protocol. There is a one-to-one mapping between a specific queue model object and a specific queue entry, for example, `DataCollectionTaskNode` and `DataCollectionQueueEntry`. The mapping is defined in a structure called MODEL_QUEUE_ENTRY_MAPPINGS in mxcubecore/queue_entry/base_queue_entry.py.

The combination of a `QueueEntry` and its model (`QueueModel`) is often referred to as a *task*, and makes up the entity that will be executed when the queue is executed.

The one-to-one mapping makes it possible to represent a queue and construct the queue entries from the queue model objects. In this way, the tree of queue model objects defines the queue. A task or collection protocol can be added to the queue by adding the *queue model object* to the `QueueModel`. For instance, a rotational data collection is added to the queue by adding a `DataCollectionTaskNode` to the `QueueModel`. This method of adding tasks to the queue is used by the Workflow engines, while the interfaces directly attach a `TaskNode` object to the corresponding `QueueEntry` which is then
*enqueued*


## Task creation - creation of QueueEntry and QueueModel
A task is created by creating a `Tasknode` and  attaching it to a corresponding `QueueEntry`. The `QueueEntry` is added or *enqueued* to the queue via the method `QueueManager.enqueue`.

### Differences between the Web and the Qt user interfaces
When the Web interface was designed, the scientists wanted to change some aspects of how the queue operates and how it is presented to the user. The decision was to work on one sample at a time, rather than for the entire queue, as is done in the Qt version. This also means  that the Web interface is centered around displaying the contents of the queue for one sample. It was also decided to not display `DataCollectionGroupQueueEntry` in the queue. The `DataCollectionGroupQueueEntry` still exists in the Web interface, but there is no view created for it.

On a technical level, there is a tight coupling between the `QueueEntry` base class to a Qt view object that makes the creation of the object slightly different between the two user interfaces (Qt and Web). To handle the tight coupling to Qt a `Mock` object used in the Web version instead of a Qt view and the handling of the updating of the view in the web version handled through signals passed over websockets to the client.

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

Each type of data collection protocol has a piece of code similar to the code above associated with it. There is a mapping, MODEL_QUEUE_ENTRY_MAPPINGS, in mxcubecore/queue_entry/base_queue_entry.py, that is used to associate the types of models and entries. In the Web version, this is done in mxcubeweb.components.queue.py in the methods called add_**task_type**, for instance `add_data_collection`. In the Qt version, the creation is done in two different places: first in the widget where the queue model object is created, and then through `QueueModel.view_created`.
