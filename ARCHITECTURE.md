# HdmiCecSource Plugin Architecture

## Overview

The HdmiCecSource plugin is a WPEFramework (Thunder) plugin that provides HDMI-CEC (Consumer Electronics Control) functionality for source devices in RDK environments. It enables STB (Set-Top Box) devices to communicate with other HDMI-CEC enabled devices over the HDMI connection, allowing for device control, status monitoring, and inter-device communication.

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    WPEFramework Core                         │
│                  (Thunder Framework)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
┌─────────▼──────────┐  ┌──────▼──────────────┐
│  JSONRPC Interface │  │  COM-RPC Interface   │
│  (REST/WebSocket)  │  │  (Process Boundary)  │
└─────────┬──────────┘  └──────┬───────────────┘
          │                     │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────────────────┐
          │    HdmiCecSource Plugin         │
          │  (PluginHost::IPlugin)          │
          │  (PluginHost::JSONRPC)          │
          └──────────┬──────────────────────┘
                     │
          ┌──────────▼──────────────────────┐
          │ HdmiCecSourceImplementation     │
          │ (Exchange::IHdmiCecSource)      │
          └──────┬──────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼────┐  ┌───▼───┐  ┌────▼─────┐
│  CEC   │  │ IARM  │  │    DS    │
│Library │  │  Bus  │  │ (Device  │
│        │  │       │  │ Settings)│
└────────┘  └───────┘  └──────────┘
```

### Component Breakdown

#### 1. Plugin Layer (HdmiCecSource)
- **Responsibility**: Thunder framework integration and JSONRPC API exposure
- **Key Features**:
  - Implements `PluginHost::IPlugin` for lifecycle management
  - Inherits from `PluginHost::JSONRPC` for JSON-RPC communication
  - Handles client notifications and event broadcasting
  - Manages plugin activation/deactivation
- **Files**: `HdmiCecSource.h`, `HdmiCecSource.cpp`, `Module.h`, `Module.cpp`

#### 2. Implementation Layer (HdmiCecSourceImplementation)
- **Responsibility**: Core CEC protocol implementation and device management
- **Key Features**:
  - Implements `Exchange::IHdmiCecSource` interface
  - CEC message processing and routing
  - Device discovery and tracking
  - Physical and logical address management
  - Power state management integration
- **Files**: `HdmiCecSourceImplementation.h`, `HdmiCecSourceImplementation.cpp`

#### 3. CEC Message Processing
- **HdmiCecSourceFrameListener**: Listens for incoming CEC frames
- **HdmiCecSourceProcessor**: Processes CEC messages including:
  - Active Source detection
  - Device power status
  - OSD name queries
  - Physical address reports
  - Routing information
  - User control commands
  - Vendor ID queries

#### 4. HAL Integration Layer
- **CEC Library**: HDMI-CEC protocol stack (`ccec/`)
  - Frame encoding/decoding
  - Connection management
  - Message types and structures
- **IARM Bus**: Inter-process communication
  - Event propagation
  - System-wide notifications
- **Device Settings (DS)**: Hardware abstraction
  - Display port management
  - Video output configuration
  - HDMI connection status

## Data Flow

### Outbound CEC Command Flow
```
Client (JSONRPC) → Plugin → Implementation → CEC Library → HDMI Hardware
```

1. Client sends JSONRPC request (e.g., `getActiveSource`)
2. Plugin validates and routes to implementation
3. Implementation prepares CEC message
4. CEC Library encodes and transmits via hardware

### Inbound CEC Event Flow
```
HDMI Hardware → CEC Library → FrameListener → MessageProcessor → Implementation → Plugin → Client Notification
```

1. Hardware receives CEC frame
2. CEC Library decodes frame
3. FrameListener notifies MessageProcessor
4. Processor handles message based on type
5. Implementation updates device state
6. Plugin broadcasts event to subscribed clients

## Plugin Framework Integration

### Thunder Plugin Lifecycle
1. **Construction**: Plugin object created by framework
2. **Initialize**: Configuration loaded, resources allocated
3. **Activate**: Implementation instantiated, CEC connection established
4. **Deactivate**: CEC connection closed, resources released
5. **Deinitialize**: Final cleanup

### Configuration
Plugin configuration is managed through:
- `HdmiCecSource.config`: Plugin metadata and startup parameters
- `HdmiCecSource.conf.in`: Runtime configuration template
- CMake options: `PLUGIN_HDMICECSOURCE`, startup order settings

### Interface Definition
The plugin exposes the `IHdmiCecSource` interface defined in Thunder interfaces:
- JSON-RPC bindings auto-generated from interface definition
- Both in-process (COM-RPC) and out-of-process (JSON-RPC) access supported

## Dependencies and Interfaces

### External Dependencies
- **WPEFramework**: Core plugin infrastructure (R4.4.1+)
- **CEC Library**: HDMI-CEC protocol implementation
- **IARMBus**: RDK Inter-Application Resource Management
- **Device Settings**: Hardware abstraction layer
- **IPowerManager**: System power state management

### Helper Utilities
The plugin uses common RDK utilities from the `helpers/` directory:
- `UtilsIarm.h`: IARM bus communication helpers
- `UtilsJsonRpc.h`: JSON-RPC utility functions
- `UtilssyncPersistFile.h`: Persistent storage synchronization
- `UtilsSearchRDKProfile.h`: RDK profile configuration lookup
- `UtilsBIT.h`: Bit manipulation utilities
- `UtilsThreadRAII.h`: Thread management with RAII pattern
- `UtilsLogging.h`: Logging infrastructure

## Technical Implementation Details

### Thread Management
- Main processing occurs on Thunder framework threads
- CEC events handled asynchronously via FrameListener callback
- Thread-safe device state management using mutexes and condition variables

### Device State Management
- Maintains registry of connected CEC devices
- Tracks logical addresses, physical addresses, and vendor IDs
- Monitors power states and active source status
- Supports device hot-plug/removal detection

### Error Handling
- Feature abort responses for unsupported commands
- Timeout handling for CEC transactions
- IARM communication error recovery
- Graceful degradation when hardware unavailable

## Security Considerations
- Plugin operates with Thunder framework security context
- JSONRPC access controlled by Thunder security tokens (can be disabled in test builds)
- No direct hardware access - all operations through HAL layers
- Input validation on all external API calls

## Performance Characteristics
- Low latency CEC message processing (<100ms typical)
- Minimal CPU overhead when idle
- Event-driven architecture reduces polling overhead
- Efficient device state caching to minimize hardware queries
