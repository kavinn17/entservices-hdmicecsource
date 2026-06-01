/**
 * Mock header for device::Host and related interfaces
 * Created to resolve compilation errors when devicesettings is not available
 */

#pragma once

#include <cstdint>
#include <string>
#include "videoOutputPort.hpp"

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
    
    /**
     * @brief Mock Host singleton class for device management
     */
    class Host {
    public:
        /**
         * @brief Mock interface for display device events
         * This is nested inside Host to match the expected device::Host::IDisplayDeviceEvents
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
        
        /**
         * @brief Get the singleton instance
         * @return Reference to the Host instance
         */
        static Host& getInstance() {
            static Host instance;
            return instance;
        }
        
        /**
         * @brief Register for display device events
         * @param listener Pointer to the event listener interface
         * @param name Name identifier for the registration
         */
        template<typename T>
        void Register(T* listener, const std::string& name) {
            // Mock implementation - no-op
        }
        
        /**
         * @brief Unregister from display device events
         * @param listener Pointer to the event listener interface
         */
        template<typename T>
        void UnRegister(T* listener) {
            // Mock implementation - no-op
        }
        
        /**
         * @brief Get the default video port name
         * @return Default video port name (e.g., "HDMI0")
         */
        std::string getDefaultVideoPortName() const {
            return "HDMI0";
        }
        
        /**
         * @brief Get a video output port by name
         * @param portName Name of the video port
         * @return VideoOutputPort object
         */
        VideoOutputPort getVideoOutputPort(const char* portName) {
            return VideoOutputPort();
        }
        
    private:
        Host() = default;
        ~Host() = default;
        Host(const Host&) = delete;
        Host& operator=(const Host&) = delete;
    };
    
} // namespace device
