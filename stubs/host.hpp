#pragma once

#include <cstdint>
#include <string>

#include "hdmiIn.hpp"
#include "videoOutputPort.hpp"

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

class Host {
public:
    class IDisplayDeviceEvents {
    public:
        virtual ~IDisplayDeviceEvents() = default;
        virtual void OnDisplayHDMIHotPlug(dsDisplayEvent_t displayEvent) = 0;
    };

    class IHdmiInEvents {
    public:
        virtual ~IHdmiInEvents() = default;
        virtual void OnHdmiInEventHotPlug(dsHdmiInPort_t port, bool isConnected) = 0;
    };

    static Host& getInstance()
    {
        static Host instance;
        return instance;
    }

    template<typename T>
    void Register(T*, const std::string&)
    {
    }

    template<typename T>
    void UnRegister(T*)
    {
    }

    std::string getDefaultVideoPortName() const
    {
        return "HDMI0";
    }

    VideoOutputPort getVideoOutputPort(const char*)
    {
        return VideoOutputPort();
    }

private:
    Host() = default;
    ~Host() = default;
    Host(const Host&) = delete;
    Host& operator=(const Host&) = delete;
};

} // namespace device
