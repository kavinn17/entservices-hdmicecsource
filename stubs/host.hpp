/**
* Mock header for device::Host::IDisplayDeviceEvents
* Created to resolve compilation errors when devicesettings is not available
*/

#pragma once

#include <cstdint>

// Mock for dsDisplayEvent_t enum
typedef enum {
    dsDISPLAY_EVENT_CONNECTED = 0,
    dsDISPLAY_EVENT_DISCONNECTED,
    dsDISPLAY_RXSENSE_ON,
    dsDISPLAY_RXSENSE_OFF,
    dsDISPLAY_HDMIHOTPLUG_CONNECTED,
    dsDISPLAY_HDMIHOTPLUG_DISCONNECTED,
    dsDISPLAY_EVENT_MAX
} dsDisplayEvent_t;

namespace device {
    namespace Host {
        /**
         * @brief Mock interface for display device events
         * 
         * This is a mock implementation to allow compilation when 
         * devicesettings host.hpp is not available.
         */
        class IDisplayDeviceEvents {
        public:
            virtual ~IDisplayDeviceEvents() = default;
            
            /**
             * @brief Callback for HDMI hotplug events
             * @param displayEvent The display event type
             */
            virtual void OnDisplayHDMIHotPlug(dsDisplayEvent_t displayEvent) = 0;
        };
    }
}

