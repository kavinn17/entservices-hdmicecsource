# Architecture: GetDeviceList and CEC Communication Stack

This diagram shows the overall architecture of how the `GetDeviceList()` API communicates through the hdmicec library, AIDL binder IPC, and vcomponent service.

```mermaid
graph TB
    subgraph Thunder["Thunder Plugin (entservices-hdmicecsource)"]
        API["GetDeviceList() API"]
        Cache["deviceList[0..14] Cache<br/>logicalAddress, osdName, vendorID"]
        Processor["HdmiCecSourceProcessor<br/>(MessageProcessor)"]
        FrameListener["HdmiCecSourceFrameListener"]
        PollThread["threadRun()<br/>(Poll Thread)"]
        UpdateThread["threadUpdateCheck()<br/>(Update Thread)"]
        SendKey["sendUnencryptMsg()"]
    end

    subgraph CCEC["hdmicec Library (ccec)"]
        Connection["Connection<br/>(smConnection)"]
        Bus["Bus<br/>(Reader + Writer threads)"]
        DriverImpl["DriverImpl<br/>(Driver singleton)"]
        EventListener["DriverImplEventListener<br/>(BnHdmiCecEventListener)"]
        MsgDecoder["MessageDecoder"]
        RQueue["rQueue<br/>(IncomingQueue)"]
    end

    subgraph Binder["AIDL Binder IPC"]
        IHdmiCec["IHdmiCec<br/>(Service Interface)"]
        IController["IHdmiCecController<br/>(sendMessage, addLogicalAddresses)"]
        IEventListener["IHdmiCecEventListener<br/>(onMessageReceived callback)"]
    end

    subgraph VComp["vcomponent (rdk-aidl-vcomponent-cec)"]
        HdmiCec["HdmiCec Service<br/>(BnHdmiCec)"]
        Controller["HdmiCecController<br/>(BnHdmiCecController)"]
        Driver["VComponentHdmiCecDriver"]
        Worker["worker() thread"]
        DevMgr["DeviceListManager<br/>(emulated devices)"]
        CecConfig["CEC Response Config<br/>(YAML files)"]
    end

    API -->|"1. reads"| Cache
    API -->|"2. signals poll"| PollThread

    PollThread -->|"ping(addr)"| Connection
    UpdateThread -->|"requestOsdName/VendorID"| SendKey
    SendKey -->|"sendAsync(frame)"| Connection

    Connection -->|"send()"| Bus
    Bus -->|"write()"| DriverImpl
    DriverImpl -->|"mAidlController->sendMessage()"| IController
    IController -->|"Binder IPC"| Controller
    Controller -->|"gHdmiCecDriver.sendMessage()"| Driver
    Driver --> Worker
    Worker -->|"lookup response"| CecConfig
    Worker -->|"device info"| DevMgr

    Worker -->|"receiveMessageCallback()"| Controller
    Controller -->|"mControllerListener->onMessageReceived()"| IEventListener
    IEventListener -->|"Binder Callback"| EventListener
    EventListener -->|"DriverReceiveCallback()"| RQueue
    RQueue -->|"Bus::Reader dequeues"| Bus
    Bus -->|"notify()"| FrameListener
    FrameListener -->|"decode()"| MsgDecoder
    MsgDecoder -->|"process()"| Processor
    Processor -->|"update osdName/vendorID"| Cache

    style Thunder fill:#e1f5fe,stroke:#0288d1
    style CCEC fill:#fff3e0,stroke:#ef6c00
    style Binder fill:#fce4ec,stroke:#c62828
    style VComp fill:#e8f5e9,stroke:#2e7d32
```

## Key Components

### Thunder Plugin Layer (Blue)
- **GetDeviceList()**: Returns cached device data and triggers async polling
- **deviceList[] Cache**: Stores device info (logical address, OSD name, vendor ID)
- **Background Threads**: Poll thread discovers devices, update thread fetches details

### hdmicec Library Layer (Orange)
- **Connection**: Manages CEC frame sending/receiving
- **Bus**: Reader/Writer threads for async I/O
- **DriverImpl**: Interfaces with AIDL binder for actual hardware communication

### AIDL Binder IPC Layer (Red)
- Cross-process communication boundary
- Synchronous calls (sendMessage) and asynchronous callbacks (onMessageReceived)

### vcomponent Service Layer (Green)
- Emulates CEC hardware/devices
- Loads device configurations from YAML files
- Generates CEC responses based on opcode and device state
