# Sequence Flow: GetDeviceList Device Discovery via AIDL Binder

This diagram shows the detailed sequence of operations when `GetDeviceList()` is called and how device information is retrieved through the CEC bus via AIDL binder.

```mermaid
sequenceDiagram
    participant Client
    participant API as GetDeviceList()
    participant Cache as deviceList[] Cache
    participant Poll as threadRun()
    participant Update as threadUpdateCheck()
    participant Conn as Connection (smConnection)
    participant Bus as Bus → DriverImpl
    participant Binder as AIDL Binder IPC
    participant VComp as vcomponent Service
    participant Listener as DriverImplEventListener
    participant Decoder as MessageDecoder
    participant Proc as HdmiCecSourceProcessor

    Client->>API: GetDeviceList()
    API->>Cache: read deviceList[0..14]
    API-->>Client: return cached devices
    API->>Poll: signal m_condSig

    Note over Poll: Loop i = 0 to 14

    Poll->>Conn: ping(logicalAddress, i)
    Conn->>Bus: send(CECFrame[src|dest])
    Bus->>Binder: mAidlController→sendMessage()
    Binder->>VComp: HdmiCecController::sendMessage()

    alt Device ACKs (present)
        VComp-->>Binder: SendMessageStatus::ACK_STATE_0
        Binder-->>Bus: status OK
        Bus-->>Poll: no exception
        Poll->>Cache: addDevice(i) → BIT_SET(PRESENT)
    else No ACK (absent)
        VComp-->>Binder: SendMessageStatus::ACK_STATE_1
        Binder-->>Bus: CECNoAckException
        Bus-->>Poll: exception thrown
        Poll->>Cache: removeDevice(i)
    end

    Poll->>Update: signal m_condSigUpdate

    Note over Update: For each PRESENT device

    rect rgb(255, 243, 224)
        Update->>Conn: requestOsdName(i) [opcode 0x46]
        Conn->>Bus: sendAsync(frame)
        Bus->>Binder: mAidlController→sendMessage()
        Binder->>VComp: sendMessage([src|dst, 0x46])
        VComp->>VComp: lookup OSD name from device config
        VComp->>Binder: receiveMessageCallback([dst|src, 0x47, name...])
        Binder->>Listener: onMessageReceived()
        Listener->>Bus: DriverReceiveCallback() → rQueue.offer()
        Bus->>Decoder: Bus::Reader → notify() → decode()
        Decoder->>Proc: process(SetOSDName)
        Proc->>Cache: deviceList[i].m_osdName = name
    end

    rect rgb(232, 245, 233)
        Update->>Conn: requestVendorID(i) [opcode 0x8C]
        Conn->>Bus: sendAsync(frame)
        Bus->>Binder: mAidlController→sendMessage()
        Binder->>VComp: sendMessage([src|dst, 0x8C])
        VComp->>VComp: lookup vendor ID from device config
        VComp->>Binder: receiveMessageCallback([dst|src, 0x87, id...])
        Binder->>Listener: onMessageReceived()
        Listener->>Bus: DriverReceiveCallback() → rQueue.offer()
        Bus->>Decoder: Bus::Reader → notify() → decode()
        Decoder->>Proc: process(DeviceVendorID)
        Proc->>Cache: deviceList[i].m_vendorID = id
    end

    Note over Client: Next GetDeviceList() call returns updated data
```

## Flow Explanation

### Phase 1: API Call (Synchronous)
1. Client calls `GetDeviceList()`
2. API immediately reads and returns cached `deviceList[0..14]`
3. API signals poll thread to start discovery

### Phase 2: Device Discovery (Asynchronous)
1. Poll thread pings each logical address (0-14)
2. Each ping goes through: Connection → Bus → DriverImpl → AIDL binder → vcomponent
3. vcomponent responds with ACK or NACK based on device presence
4. ACK → `addDevice()` marks device as present
5. NACK → `removeDevice()` clears device

### Phase 3: Detail Fetching (Asynchronous)
**Orange box - OSD Name Request:**
- Sends CEC opcode `0x46` (Give OSD Name)
- Response opcode `0x47` (Set OSD Name) comes back through binder callback
- Updates `deviceList[i].m_osdName`

**Green box - Vendor ID Request:**
- Sends CEC opcode `0x8C` (Give Device Vendor ID)
- Response opcode `0x87` (Device Vendor ID) comes back through binder callback
- Updates `deviceList[i].m_vendorID`

### Phase 4: Subsequent Calls
Next `GetDeviceList()` call returns the populated cache with all device details.
