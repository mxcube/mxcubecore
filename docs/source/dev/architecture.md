# MXCuBE Architecture

**MXCuBE** (Macromolecular Xtallography Customized Beamline Environment) is a modular framework for controlling synchrotron beamlines for macromolecular crystallography experiments.

This documentation was partly generated automatically and is meant to provide an architectural overview of the concepts involved. It may miss implementation details.

## Table of Contents

- [System Overview](#system-overview)
- [High-Level Architecture](#high-level-architecture)
- [MXCubeCore Architecture](#mxcubecore-architecture)
- [MXCubeWeb Architecture](#mxcubeweb-architecture)
- [Communication Flow](#communication-flow)
- [Data Collection Workflow](#data-collection-workflow)
- [Key Components](#key-components)

______________________________________________________________________

## System Overview

MXCuBE is split into two main repositories:

- **mxcubecore**: Hardware abstraction layer and core business logic
- **mxcubeweb**: Web-based user interface and REST/WebSocket API server

```mermaid
graph TB
    subgraph "User Layer"
        Browser[Web Browser]
    end

    subgraph "Application Layer - mxcubeweb"
        UI[React Frontend]
        API[Flask Backend<br/>WebSocket Server]
    end

    subgraph "Hardware Abstraction Layer - mxcubecore"
        HWR[Hardware Repository]
        HWO[Hardware Objects]
        QM[Queue Manager]
    end

    subgraph "Control Systems"
        TANGO[TANGO]
        EPICS[EPICS]
        SPEC[SPEC]
    end

    subgraph "Physical Hardware"
        Motors[Motors/Stages]
        Detectors[Detectors]
        Cameras[Cameras]
        SC[Sample Changer]
    end

    Browser <-->|HTTP/WS| UI
    UI <-->|REST/Socket.IO| API
    API <-->|Python API| HWR
    HWR --> HWO
    HWO -->|Commands/Channels| TANGO
    HWO -->|Commands/Channels| EPICS
    HWO -->|Commands/Channels| SPEC
    TANGO --> Motors
    TANGO --> Detectors
    EPICS --> Cameras
    SPEC --> SC

    style Browser fill:#e1f5ff
    style UI fill:#b3e5fc
    style API fill:#81d4fa
    style HWR fill:#ffcc80
    style HWO fill:#ffb74d
    style TANGO fill:#c5e1a5
    style Motors fill:#f48fb1
```

______________________________________________________________________

## High-Level Architecture

### Three-Tier Architecture

```mermaid
graph LR
    subgraph "Presentation Tier"
        A[React UI<br/>Redux Store<br/>Socket.IO Client]
    end

    subgraph "Application Tier"
        B[Flask Server<br/>WebSocket Server<br/>Business Logic<br/>Queue Manager]
    end

    subgraph "Hardware Tier"
        C[Hardware Repository<br/>Hardware Objects<br/>Control Protocols<br/>Device Drivers]
    end

    A <-->|REST API<br/>WebSocket| B
    B <-->|Python API<br/>Events| C

    style A fill:#bbdefb
    style B fill:#ffccbc
    style C fill:#c5e1a5
```

______________________________________________________________________

## MXCubeCore Architecture

### Core Component Hierarchy

```mermaid
graph TD
    subgraph "mxcubecore/"
        HWR[HardwareRepository<br/>Singleton Registry]

        subgraph "Hardware Objects"
            BL[Beamline<br/>Container Object]
            HWO[Hardware Objects]
            Abstract[Abstract Base Classes]
            Concrete[Concrete Implementations]
        end

        subgraph "Queue System"
            QM[QueueManager]
            QModel[QueueModel<br/>Tree Structure]
            QEntry[QueueEntry<br/>Executors]
        end

        subgraph "Data Models"
            DMO[Queue Model Objects]
            Config[Configuration Models]
            Lims[LIMS Session Models]
        end

        subgraph "Communication"
            Dispatcher[Event Dispatcher]
            Commands[Command Objects]
            Channels[Channel Objects]
        end
    end

    HWR -->|manages| HWO
    HWR -->|provides| BL
    BL -->|contains| HWO
    Abstract -.->|inheritance| Concrete
    HWO -->|uses| Commands
    HWO -->|uses| Channels
    HWO -->|emits| Dispatcher
    QM -->|manages| QModel
    QModel -->|contains| QEntry
    QEntry -->|executes| HWO
    QEntry -->|uses| DMO

    style HWR fill:#ff9800
    style BL fill:#ffc107
    style QM fill:#8bc34a
    style DMO fill:#64b5f6
    style Dispatcher fill:#ba68c8
```

### Hardware Object Base Classes

```mermaid
classDiagram
    class HardwareObject {
        +String name
        +State state
        +init()
        +abort()
        +stop()
        +get_state()
        +emit(signal, args)
        +connect(sender, signal, slot)
    }

    class AbstractActuator {
        +get_value()
        +set_value(value)
        +get_limits()
        +validate_value(value)
        +update_value()
    }

    class AbstractMotor {
        +get_position()
        +set_position(position)
        +get_velocity()
        +home()
    }

    class AbstractSampleChanger {
        +load_sample(sample)
        +unload_sample()
        +get_loaded_sample()
        +get_sample_list()
    }

    class AbstractCollect {
        +collect(params)
        +prepare_collection()
        +data_collection_hook()
    }

    class Beamline {
        +diffractometer
        +sample_changer
        +detector
        +energy
        +collect
    }

    HardwareObject <|-- AbstractActuator
    AbstractActuator <|-- AbstractMotor
    HardwareObject <|-- AbstractSampleChanger
    HardwareObject <|-- AbstractCollect
    HardwareObject <|-- Beamline
```

### Hardware Repository Pattern

```mermaid
sequenceDiagram
    participant App as Application
    participant HWR as HardwareRepository
    participant Parser as XMLParser
    participant HWO as HardwareObject
    participant Device as Control System

    App->>HWR: init_hardware_repository(path)
    HWR->>HWR: scan XML/YAML files

    App->>HWR: get_hardware_object("motor")
    HWR->>Parser: parse config file
    Parser->>HWR: return class & properties
    HWR->>HWO: instantiate & configure
    HWO->>Device: connect to control system
    HWO-->>HWR: return initialized object
    HWR-->>App: return HardwareObject

    App->>HWO: set_value(10.5)
    HWO->>Device: write command
    Device-->>HWO: value changed
    HWO->>HWO: emit('valueChanged')
```

### Queue Execution Model

```mermaid
graph TD
    subgraph "Queue Structure"
        Root[Queue Root]
        S1[Sample 1]
        S2[Sample 2]
        G1[TaskGroup]
        G2[TaskGroup]
        DC1[DataCollection]
        DC2[DataCollection]
        Char[Characterisation]
    end

    subgraph "Queue Entries"
        SEntry[SampleQueueEntry]
        GEntry[TaskGroupQueueEntry]
        DCEntry[DataCollectionQueueEntry]
        CharEntry[CharacterisationQueueEntry]
    end

    subgraph "Execution"
        QM[QueueManager]
        Executor[Entry Executor]
        Collect[Beamline.collect]
    end

    Root --> S1
    Root --> S2
    S1 --> G1
    S2 --> G2
    G1 --> DC1
    G1 --> Char
    G2 --> DC2

    S1 -.->|model| SEntry
    G1 -.->|model| GEntry
    DC1 -.->|model| DCEntry

    QM -->|traverse tree| SEntry
    SEntry -->|execute children| GEntry
    GEntry -->|execute children| DCEntry
    DCEntry -->|collect data| Collect

    style Root fill:#ffeb3b
    style S1 fill:#4caf50
    style G1 fill:#03a9f4
    style DC1 fill:#f44336
    style QM fill:#9c27b0
```

______________________________________________________________________

## MXCubeWeb Architecture

### Backend Architecture

```mermaid
graph TB
    Entry[mxcubeweb-server<br/>Entry Point]

    Flask[Flask Application]
    SocketIO[Flask-SocketIO]
    Auth[Flask-Security]
    Limiter[Rate Limiter]

    MainRoute[Main API Route<br/>/mxcube/api/v0.1]
    QueueRoute[Queue Routes]
    LoginRoute[Login Routes]
    RARoute[Remote Access]
    WorkflowRoute[Workflow Routes]
    HarvesterRoute[Harvester Routes]

    MXApp[MXCUBEApplication]
    Queue[Queue Component]
    Lims[LIMS Component]
    UserMgr[User Manager]
    Chat[Chat Component]
    Workflow[Workflow Component]
    Harvester[Harvester Component]

    AdapterMgr[HardwareObjectAdapterManager]
    HWR[mxcubecore.HWR]

    StateStorage[UI State Storage]
    UserDB[User Database]

    Entry --> Flask
    Flask --> SocketIO
    Flask --> Auth
    Flask --> Limiter
    Flask --> MainRoute

    MainRoute --> QueueRoute
    MainRoute --> LoginRoute
    MainRoute --> RARoute
    MainRoute --> WorkflowRoute
    MainRoute --> HarvesterRoute

    QueueRoute --> Queue
    LoginRoute --> UserMgr
    RARoute --> UserMgr
    RARoute --> Chat
    WorkflowRoute --> Workflow
    HarvesterRoute --> Harvester

    MXApp --> Queue
    MXApp --> Lims
    MXApp --> UserMgr
    MXApp --> Chat
    MXApp --> Workflow
    MXApp --> Harvester
    MXApp --> AdapterMgr

    AdapterMgr --> HWR
    Auth --> UserDB
    SocketIO --> StateStorage

    style Entry fill:#ff9800
    style Flask fill:#2196f3
    style MXApp fill:#4caf50
    style AdapterMgr fill:#9c27b0
    style HWR fill:#ff5722
```

### Frontend Architecture

```mermaid
flowchart TB
    Index[index.jsx Entry Point]

    subgraph State["State Management"]
        Store[Redux Store]
        Reducers[Reducers]
        Actions[Action Creators]
    end

    subgraph Components["Components"]
        Login[Login]
        SampleGrid[Sample Grid]
        SampleQueue[Sample Queue]
        SampleView[Sample View Video Stream]
        TaskForms[Task Forms]
        Equipment[Equipment Panel]
        Logger[Logger]
        RemoteAccess[Remote Access]
    end

    subgraph Containers["Containers"]
        SGContainer[SampleListViewContainer]
        SQContainer[SampleQueueContainer]
        SVContainer[SampleViewContainer]
    end

    subgraph Communication["Communication"]
        API[REST API Client wretch]
        ServerIO[Socket.IO Client]
    end

    Backend[Flask/SocketIO Server]

    Index --> Store
    Store --> Reducers
    Actions --> Reducers

    Index --> SGContainer
    Index --> SQContainer
    Index --> SVContainer

    SGContainer --> SampleGrid
    SQContainer --> SampleQueue
    SVContainer --> SampleView

    SampleGrid --> Actions
    SampleQueue --> Actions
    TaskForms --> Actions

    Actions --> API
    Actions --> ServerIO

    API -->|REST| Backend
    ServerIO -->|WebSocket| Backend
    Backend -->|Events| ServerIO

    ServerIO --> Actions
    Actions --> Store

    style Index fill:#ff9800
    style Store fill:#4caf50
    style API fill:#2196f3
    style ServerIO fill:#9c27b0
    style Backend fill:#f44336
```

### Component Communication

```mermaid
sequenceDiagram
    participant UI as React Component
    participant Action as Action Creator
    participant API as API Client
    participant Server as Flask Server
    participant Queue as Queue Component
    participant HWR as Hardware Repository
    participant HWO as Hardware Object

    UI->>Action: User clicks "Start Queue"
    Action->>API: sendStartQueue()
    API->>Server: PUT /queue/start
    Server->>Queue: queue_start()
    Queue->>HWR: beamline.queue_manager
    HWR->>HWO: execute queue entries
    HWO->>HWO: collect data
    HWO->>HWR: emit signals
    HWR->>Queue: queue progress
    Queue->>Server: emit('queue', state)
    Server->>UI: WebSocket event
    UI->>Action: dispatch(setStatus)
    Action->>UI: update Redux store
```

______________________________________________________________________

## Communication Flow

### REST API Flow

```mermaid
sequenceDiagram
    participant Browser
    participant Redux
    participant APIClient
    participant Flask
    participant Component
    participant MXCubeCore

    Browser->>Redux: User Action
    Redux->>APIClient: api.get('/queue')
    APIClient->>Flask: HTTP GET /mxcube/api/v0.1/queue
    Flask->>Flask: @restrict (auth check)
    Flask->>Component: app.queue.queue_to_dict()
    Component->>MXCubeCore: HWR.beamline.queue_manager
    MXCubeCore-->>Component: queue data
    Component-->>Flask: JSON response
    Flask-->>APIClient: 200 OK + JSON
    APIClient-->>Redux: dispatch(setQueue)
    Redux-->>Browser: UI Update
```

### WebSocket Event Flow

```mermaid
sequenceDiagram
    participant HWO as Hardware Object
    participant Signal as Signal Handler
    participant SocketIO as Flask-SocketIO
    participant Client as Browser Client
    participant Redux as Redux Store

    HWO->>HWO: state changes
    HWO->>Signal: emit('stateChanged', state)
    Signal->>SocketIO: server.emit('hwobj_state', data)
    SocketIO->>Client: WebSocket message
    Client->>Redux: dispatch(updateHWObjState)
    Redux->>Client: re-render UI

    Note over HWO,Redux: Real-time updates without polling
```

### Data Collection Signal Flow

```mermaid
graph LR
    subgraph "Hardware Layer"
        Det[Detector]
        Motor[Goniometer]
    end

    subgraph "Control Layer"
        Collect[CollectHWObj]
        DC[DataCollectionEntry]
    end

    subgraph "Queue Layer"
        QM[QueueManager]
        QE[QueueEntry]
    end

    subgraph "Application Layer"
        QComp[Queue Component]
        Signal[Signal Handler]
    end

    subgraph "Frontend"
        Socket[Socket.IO]
        UI[React UI]
    end

    Det -->|frames collected| Collect
    Motor -->|position reached| Collect
    Collect -->|progress| DC
    DC -->|status| QE
    QE -->|emit| QM
    QM -->|queue_entry_execute_started| QComp
    QComp -->|format message| Signal
    Signal -->|emit event| Socket
    Socket -->|WebSocket| UI

    style Det fill:#c5e1a5
    style Collect fill:#ffcc80
    style QM fill:#81d4fa
    style Signal fill:#ce93d8
    style UI fill:#90caf9
```

______________________________________________________________________

## Data Collection Workflow

### End-to-End Data Collection

```mermaid
sequenceDiagram
    participant User
    participant UI as React UI
    participant Queue as Queue Component
    participant QM as QueueManager
    participant SC as Sample Changer
    participant Diff as Diffractometer
    participant Collect as Collect HWObj
    participant Det as Detector
    participant LIMS

    User->>UI: Add sample + tasks
    UI->>Queue: addTask()
    Queue->>QM: add to queue model

    User->>UI: Click "Start Queue"
    UI->>Queue: startQueue()
    Queue->>QM: execute()

    QM->>SC: load_sample(location)
    SC-->>QM: sample mounted

    QM->>Diff: center_sample()
    Diff-->>QM: centred position

    QM->>Collect: collect(parameters)
    Collect->>Diff: move to start position
    Collect->>Det: prepare acquisition
    Collect->>Det: start_acquisition()

    loop For each image
        Det->>Det: collect frame
        Det->>Collect: emit('imageCollected')
        Collect->>QM: progress update
        QM->>UI: WebSocket update
    end

    Det-->>Collect: acquisition complete
    Collect->>LIMS: store metadata
    Collect-->>QM: collection finished
    QM->>UI: emit('queue_entry_finished')

    QM->>SC: unload_sample()
    SC-->>QM: sample unmounted
```

### Queue Tree Execution

```mermaid
stateDiagram-v2
    [*] --> QueueIdle
    QueueIdle --> Executing: start_queue()

    state Executing {
        [*] --> MountSample
        MountSample --> CenterSample
        CenterSample --> TaskGroup

        state TaskGroup {
            [*] --> DataCollection
            DataCollection --> Characterisation
            Characterisation --> [*]
        }

        TaskGroup --> UnmountSample
        UnmountSample --> NextSample
        NextSample --> MountSample: more samples
        NextSample --> [*]: done
    }

    Executing --> QueueIdle: finished
    Executing --> Paused: pause()
    Paused --> Executing: resume()
    Executing --> Stopped: stop()
    Stopped --> QueueIdle
```

______________________________________________________________________

## Key Components

### 1. Hardware Repository (mxcubecore)

**Purpose**: Central registry and factory for hardware objects

**Key Features**:

- Singleton pattern for global access (`HWR.beamline.*`)
- Dynamic loading from XML/YAML configurations
- Lazy initialization of hardware objects
- Event-driven communication via dispatcher

**Example**:

```python
from mxcubecore import HardwareRepository as HWR

# Access hardware objects
HWR.beamline.diffractometer.move_motors({"omega": 90})
HWR.beamline.detector.prepare_acquisition()
```

### 2. Hardware Objects

**Purpose**: Abstract hardware control behind unified interfaces

**Key Base Classes**:

- `HardwareObject`: Base class with state management
- `AbstractActuator`: Values and limits (motors, energy, etc.)
- `AbstractSampleChanger`: Sample loading/unloading
- `AbstractCollect`: Data collection orchestration

**Control System Adapters**:

- TANGO (Tango Controls)
- EPICS (Experimental Physics and Industrial Control System)
- SPEC (Python wrapper for Spec diffractometer control)

### 3. Queue System

**Purpose**: Manage and execute data collection workflows

**Components**:

- `QueueModel`: Tree structure of samples and tasks
- `QueueEntry`: Executable nodes with `execute()` method
- `QueueManager`: Traversal and execution engine

**Queue Entry Types**:

- `SampleQueueEntry`: Mount/unmount operations
- `DataCollectionQueueEntry`: Standard data collection
- `CharacterisationQueueEntry`: Crystal characterisation
- `WorkflowQueueEntry`: Multi-step workflows
- `TaskGroupQueueEntry`: Group related tasks

### 4. MXCUBEApplication (mxcubeweb)

**Purpose**: Application-level business logic and state

**Components**:

- `Queue`: Queue management API
- `Lims`: LIMS integration (ISPyB, etc.)
- `UserManager`: Authentication and authorization
- `Chat`: Remote access collaboration
- `Workflow`: Advanced workflows (GPhL, etc.)
- `Harvester`: Crystal harvester integration

### 5. Signal System

**Purpose**: Decouple components via event-driven architecture

**Pattern**:

```python
# Hardware object emits signal
self.emit("valueChanged", new_value)

# Application listens
HWR.beamline.motor.connect("valueChanged", callback)
```

**Signal Flow**:
Hardware Object → Dispatcher → Signal Handler → Flask-SocketIO → Browser

### 6. React Frontend

**Purpose**: Modern web UI with real-time updates

**Stack**:

- React 18 + Redux for state management
- Socket.IO for real-time communication
- Vite for fast builds
- Bootstrap for styling

**Key Containers**:

- `SampleListViewContainer`: Sample management and LIMS
- `SampleQueueContainer`: Queue visualization and control
- `SampleViewContainer`: Video stream and sample centering
- `TaskParametersContainer`: Data collection forms

______________________________________________________________________
