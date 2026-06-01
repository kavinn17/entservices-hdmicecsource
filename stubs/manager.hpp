/**
 * Mock header for manager.hpp
 * Created to resolve compilation errors when devicesettings is not available
 */

#pragma once

namespace device {
    
    /**
     * @brief Mock Manager class for device management
     */
    class Manager {
    public:
        /**
         * @brief Initialize the device manager
         * Mock implementation - does nothing
         */
        static void Initialize() {
            // Mock implementation - no-op
        }
        
        /**
         * @brief De-initialize the device manager
         * Mock implementation - does nothing
         */
        static void DeInitialize() {
            // Mock implementation - no-op
        }
    };
    
} // namespace device

