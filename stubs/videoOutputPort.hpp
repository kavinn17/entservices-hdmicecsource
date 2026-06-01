/**
 * Mock header for videoOutputPort.hpp
 * Created to resolve compilation errors when devicesettings is not available
 */

#pragma once

#include <string>
#include <vector>
#include <cstdint>

namespace device {
    
    /**
     * @brief Mock Display class representing a display device
     */
    class Display {
    public:
        Display() = default;
        ~Display() = default;
        
        /**
         * @brief Get EDID bytes from the display
         * @param edidBytes Vector to store EDID bytes
         */
        void getEDIDBytes(std::vector<uint8_t>& edidBytes) {
            // Mock implementation - provide minimal EDID data
            // Bytes at positions 8-9 are manufacturer ID in real EDID
            edidBytes.resize(256, 0x00);
            // Set some default manufacturer bytes (not LG)
            edidBytes[8] = 0x00;
            edidBytes[9] = 0x00;
        }
    };
    
    /**
     * @brief Mock VideoOutputPort class representing a video output port
     */
    class VideoOutputPort {
    public:
        VideoOutputPort() = default;
        ~VideoOutputPort() = default;
        
        /**
         * @brief Check if a display is connected to this port
         * @return true if display is connected, false otherwise
         */
        bool isDisplayConnected() const {
            // Mock implementation - assume display is connected
            return true;
        }
        
        /**
         * @brief Get the Display object associated with this port
         * @return Display object
         */
        Display& getDisplay() {
            return display_;
        }
        
    private:
        Display display_;
    };
    
} // namespace device

