#ifndef VDEVICE_NOOP_HDMIIN_HPP
#define VDEVICE_NOOP_HDMIIN_HPP

#include "dsError.h"

typedef int dsHdmiInPort_t;

namespace device {

class HdmiInput {
public:
    static HdmiInput& getInstance()
    {
        static HdmiInput instance;
        return instance;
    }

    bool isPortConnected(int) const
    {
        return true;
    }

    int getNumberOfInputs() const
    {
        return 3;
    }

    dsError_t getHDMIARCPortId(int& portId) const
    {
        portId = 1;
        return dsERR_NONE;
    }

private:
    HdmiInput() = default;
};

} // namespace device

#endif
