#include "HdmiCecVirtualRemote.h"
#include <linux/input.h>
#include <utility>
#include <cstdio>

HdmiCecVirtualRemote::HdmiCecVirtualRemote()
            : virtualInputDeviceName("HdmiCecVirtualRemote")
                  , device(nullptr)
                  , ui_device(nullptr)
{
            int err;

            keys.insert(std::make_pair("UP", KEY_UP));
            keys.insert(std::make_pair("DOWN", KEY_DOWN));
            keys.insert(std::make_pair("LEFT", KEY_LEFT));
            keys.insert(std::make_pair("RIGHT", KEY_RIGHT));
            keys.insert(std::make_pair("SELECT", KEY_ENTER));

            device = libevdev_new();

            if (device) {

                    libevdev_set_name(
                            device,
                            virtualInputDeviceName.c_str());

                    libevdev_enable_event_type(

                            device,
                            EV_KEY);

                    for (auto itr = keys.begin();
                                    itr != keys.end();
                                    ++itr) {

                            libevdev_enable_event_code(
                                            device,
                                            EV_KEY,
                                            itr->second,
                                            nullptr);
                }

                    libevdev_enable_event_type(
                                    device,
                                    EV_REL);

                    err = libevdev_uinput_create_from_device(
                                    device,
                                    LIBEVDEV_UINPUT_OPEN_MANAGED,
                                    &ui_device);

                    if (err != 0) {

                            libevdev_free(device);
                            device = nullptr;

                    } else {

                            printf("Created node : %s\n",
                                            libevdev_uinput_get_devnode(ui_device));
                    }

            } else {

                    printf("libevdev_new() failed\n");
            }
}

HdmiCecVirtualRemote::~HdmiCecVirtualRemote()
{
        if (ui_device) {

                libevdev_uinput_destroy(ui_device);

        }

        if (device) {

                libevdev_free(device);

                }
}

bool HdmiCecVirtualRemote::keyPress(std::string keyAction)
{

        auto iter = keys.find(keyAction);

                if (iter != keys.end()) {

                return sendEvent(EV_KEY, iter->second, 1);

                }
            return false;
}
bool HdmiCecVirtualRemote::keyRelease(std::string keyAction)
{
            auto iter = keys.find(keyAction);

                if (iter != keys.end()) {
                                return sendEvent(EV_KEY, iter->second, 0);
                                    }

                    return false;
}

bool HdmiCecVirtualRemote::keyPressRelease(std::string keyAction)
{
            auto iter = keys.find(keyAction);

            if (iter != keys.end()) {

                    if (!sendEvent(EV_KEY, iter->second, 1)) {
                            return false;
                    }

                    if (!sendEvent(EV_KEY, iter->second, 0)) {
                            return false;
                    }

                    return true;
            }

                    return false;
}

bool HdmiCecVirtualRemote::sendEvent(int type,
                                     int code,
                                     int value)
{
            int retVal =
                libevdev_uinput_write_event(
                     ui_device,
                     type,
                     code,
                    value);

                if (retVal == 0) {
                    retVal =
                       libevdev_uinput_write_event(
                          ui_device,
                          EV_SYN,
                          SYN_REPORT,
                          0);
   }

                    return (retVal == 0);
}
