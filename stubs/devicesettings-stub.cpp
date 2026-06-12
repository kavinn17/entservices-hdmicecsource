// DeviceSettings stub implementation for vdevice
// Provides minimal mock functions to prevent runtime crashes

#include <string>
#include <vector>
#include <stdexcept>

namespace device {

// Forward declarations
class Display;
class VideoOutputPort;
class Host;

// Display stub
class Display {
public:
    void getEDIDBytes(std::vector<uint8_t>& edidVec) {
        // Return mock EDID with generic vendor ID (not LG)
        edidVec.resize(256, 0);
        edidVec[8] = 0x00;  // Not LG (LG would be 0x1E)
        edidVec[9] = 0x00;  // Not LG (LG would be 0x6D)
    }
};

// VideoOutputPort stub
class VideoOutputPort {
private:
    Display display;
    
public:
    VideoOutputPort() {}
    
    bool isDisplayConnected() {
        // Mock: always return true (display connected)
        return true;
    }
    
    Display& getDisplay() {
        return display;
    }
};

// Host stub
class Host {
private:
    static Host* instance;
    
public:
    static Host& getInstance() {
        if (!instance) {
            instance = new Host();
        }
        return *instance;
    }
    
    std::string getDefaultVideoPortName() {
        return "HDMI0";
    }
    
    VideoOutputPort getVideoOutputPort(const char* name) {
        return VideoOutputPort();
    }
    
    // Event registration stubs
    template<typename T>
    void Register(T* obj, const char* name) {
        // Do nothing - mock registration
    }
    
    template<typename T>
    void UnRegister(T* obj) {
        // Do nothing - mock unregistration  
    }
    
    class IDisplayDeviceEvents {
    public:
        virtual ~IDisplayDeviceEvents() {}
    };
};

Host* Host::instance = nullptr;

// Manager stub
class Manager {
public:
    static void Initialize() {
        // Do nothing - mock initialization
    }
    
    static void DeInitialize() {
        // Do nothing - mock cleanup
    }
};

} // namespace device
