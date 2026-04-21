# Process Architecture: Binder IPC Between Plugin and vcomponent

This diagram shows how the Thunder plugin process and vcomponent service process communicate across the Linux kernel's binder driver.

```mermaid
graph LR
    subgraph Process1["Thunder Plugin Process"]
        direction TB
        A1["HdmiCecSourceImplementation<br/>(GetDeviceList, deviceList cache)"]
        A2["HdmiCecSourceProcessor<br/>(message handlers)"]
        A3["Connection / Bus / DriverImpl<br/>(hdmicec library)"]
        A4["DriverImplEventListener<br/>(receives binder callbacks)"]

        A1 --- A2
        A2 --- A3
        A3 --- A4
    end

    subgraph BinderKernel["Linux Kernel"]
        B1["/dev/binder<br/>(Binder Driver)"]
    end

    subgraph Process2["vcomponent Service Process"]
        direction TB
        C1["HdmiCec (BnHdmiCec)<br/>IHdmiCec service"]
        C2["HdmiCecController (BnHdmiCecController)<br/>sendMessage / addLogicalAddresses"]
        C3["VComponentHdmiCecDriver<br/>worker thread, message queue"]
        C4["DeviceListManager<br/>emulated device configs (YAML)"]

        C1 --- C2
        C2 --- C3
        C3 --- C4
    end

    A3 -->|"sendMessage()<br/>(BpHdmiCecController)"| B1
    B1 -->|"onTransaction()<br/>(BnHdmiCecController)"| C2

    C2 -->|"onMessageReceived()<br/>(BpHdmiCecEventListener)"| B1
    B1 -->|"onTransaction()<br/>(BnHdmiCecEventListener)"| A4

    style Process1 fill:#e1f5fe,stroke:#0288d1
    style BinderKernel fill:#fce4ec,stroke:#c62828
    style Process2 fill:#e8f5e9,stroke:#2e7d32
```

## Process Separation

### Thunder Plugin Process (Blue)
- Runs as part of the WPEFramework/Thunder
- Contains the HdmiCecSource plugin implementation
- Links against hdmicec library (libccec.so)
- Uses **Bp** (Binder Proxy) stubs to make calls to vcomponent

### Linux Kernel Binder Driver (Red)
- `/dev/binder` character device
- Provides IPC mechanism between processes
- Handles data marshaling/unmarshaling
- Manages reference counting and death notifications

### vcomponent Service Process (Green)
- Separate daemon process (typically runs as system service)
- Implements **Bn** (Binder Native) stubs to receive calls
- Emulates CEC hardware behavior
- Loads device configurations from YAML files in `vcomponent_configurations/`

## Binder Communication Paths

### Outbound (Plugin → vcomponent)
```
DriverImpl::write()
  → mAidlController->sendMessage()  [BpHdmiCecController proxy]
  → /dev/binder kernel driver
  → HdmiCecController::sendMessage()  [BnHdmiCecController native]
  → VComponentHdmiCecDriver
```

### Inbound (vcomponent → Plugin)
```
VComponentHdmiCecDriver::receiveMessage()
  → mReceiveMessageCallback()
  → mControllerListener->onMessageReceived()  [BpHdmiCecEventListener proxy]
  → /dev/binder kernel driver
  → DriverImplEventListener::onMessageReceived()  [BnHdmiCecEventListener native]
  → DriverReceiveCallback() → rQueue
```

## AIDL Generated Code

The binder proxies and stubs are generated from AIDL definitions:
- `IHdmiCec.aidl` - Service interface
- `IHdmiCecController.aidl` - Controller interface for sending messages
- `IHdmiCecEventListener.aidl` - Callback interface for receiving messages

Generated classes:
- **Bp** = Binder Proxy (client side)
- **Bn** = Binder Native (server side)
- **I** = Interface definition
