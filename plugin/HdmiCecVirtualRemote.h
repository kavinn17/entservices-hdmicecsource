#include <map>
#include <string>
#include <libevdev/libevdev.h>
#include <libevdev/libevdev-uinput.h>

class HdmiCecVirtualRemote
{
        public:

                HdmiCecVirtualRemote();

                virtual ~HdmiCecVirtualRemote();

                            bool keyPress(std::string keyAction);
                            bool keyRelease(std::string keyAction);
                            bool keyPressRelease(std::string keyAction);

        private:

                bool sendEvent(int type, int code, int value);

        private:

                std::map<std::string, int> keys;

                std::string virtualInputDeviceName;

                struct libevdev* device;

                struct libevdev_uinput* ui_device;

};
