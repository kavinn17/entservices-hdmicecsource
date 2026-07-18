/**
* If not stated otherwise in this file or this component's LICENSE
* file the following copyright and licenses apply:
*
* Copyright 2025 RDK Management
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
* http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
**/

/**
 * @file HdmiCecSourceImplementation.h  (DS_COMRPC)
 *
 * @brief HdmiCecSource implementation using COM-RPC DeviceSettings plugin.
 *
 * Compiled when USE_DEVICESETTING_PLUGIN is defined.  Replaces the legacy
 * DS_IARM version which drives libds/IARM directly.  The CEC stack (libcec,
 * ccec/Connection, etc.) is unchanged; only the display-related queries
 * (connectivity check, EDID read) and the HDMI hot-plug notification are
 * re-routed through the DeviceSettings COM-RPC plugin.
 *
 * Changes vs DS_IARM:
 *   - Inherits DSHelper for a single COM-RPC link.
 *   - Inherits Exchange::IConfiguration so the HdmiCecSource proxy can pass
 *     IShell* via Configure(service).
 *   - device::Host::IDisplayDeviceEvents replaced by inner
 *     DSVideoPortNotification (IDeviceSettingsVideoPort::INotification).
 *   - Cached _videoPortHandle / _displayHandle populated in
 *     OnDeviceSettingsActivated().
 *   - device::Manager::Initialize() is NOT called.
 */

#pragma once

#include <stdint.h>
#include <mutex>
#include <condition_variable>

#include "ccec/FrameListener.hpp"
#include "ccec/Connection.hpp"
#include "libIARM.h"
#include "ccec/Assert.hpp"
#include "ccec/Messages.hpp"
#include "ccec/MessageDecoder.hpp"
#include "ccec/MessageProcessor.hpp"
#include <thread>

#undef Assert // conflicts with WPEFramework

#include "../Module.h"

#include "UtilsBIT.h"
#include "UtilsThreadRAII.h"

#include <interfaces/IPowerManager.h>
#include "PowerManagerInterface.h"
#include <interfaces/IHdmiCecSource.h>
#include <interfaces/IConfiguration.h>
#include "DeviceSettingsInterface.h"
#include <interfaces/IDeviceSettingsDisplay.h>

using namespace WPEFramework;
using PowerState = WPEFramework::Exchange::IPowerManager::PowerState;
using ThermalTemperature = WPEFramework::Exchange::IPowerManager::ThermalTemperature;

namespace WPEFramework {

    namespace Plugin {
        class HdmiCecSourceFrameListener : public FrameListener
        {
        public:
            HdmiCecSourceFrameListener(MessageProcessor &processor) : processor(processor) {}
            void notify(const CECFrame &in) const;
            ~HdmiCecSourceFrameListener() {}
        private:
            MessageProcessor &processor;
        };

        class HdmiCecSourceProcessor : public MessageProcessor
        {
        public:
            HdmiCecSourceProcessor(Connection &conn) : conn(conn) {}
            void process (const ActiveSource &msg, const Header &header);
            void process (const RequestActiveSource &msg, const Header &header);
            void process (const Standby &msg, const Header &header);
            void process (const GetCECVersion &msg, const Header &header);
            void process (const CECVersion &msg, const Header &header);
            void process (const GiveOSDName &msg, const Header &header);
            void process (const GivePhysicalAddress &msg, const Header &header);
            void process (const GiveDeviceVendorID &msg, const Header &header);
            void process (const SetOSDName &msg, const Header &header);
            void process (const RoutingChange &msg, const Header &header);
            void process (const RoutingInformation &msg, const Header &header);
            void process (const SetStreamPath &msg, const Header &header);
            void process (const ReportPhysicalAddress &msg, const Header &header);
            void process (const DeviceVendorID &msg, const Header &header);
            void process (const GiveDevicePowerStatus &msg, const Header &header);
            void process (const ReportPowerStatus &msg, const Header &header);
            void process (const UserControlPressed &msg, const Header &header);
            void process (const UserControlReleased &msg, const Header &header);
            void process (const FeatureAbort &msg, const Header &header);
            void process (const Abort &msg, const Header &header);
            void process (const Polling &msg, const Header &header);
        private:
            Connection conn;
        };

#define BIT_DEVICE_PRESENT    (0)

        class CECDeviceInfo_2 {
        public:
            LogicalAddress m_logicalAddress;
            VendorID m_vendorID;
            OSDName m_osdName;
            short m_deviceInfoStatus;
            bool m_isOSDNameUpdated;
            bool m_isVendorIDUpdated;
            std::mutex m_;
            std::condition_variable cv_;
            std::unique_lock<std::mutex> lk;

            CECDeviceInfo_2()
            : m_logicalAddress(0),m_vendorID(0,0,0),m_osdName("NA"), m_deviceInfoStatus(0), m_isOSDNameUpdated(false), m_isVendorIDUpdated(false)
            {
                BITMASK_CLEAR(m_deviceInfoStatus, 0xFFFF);
            }

            void clear()
            {
                m_logicalAddress = 0;
                m_vendorID = VendorID(0,0,0);
                m_osdName = "NA";
                BITMASK_CLEAR(m_deviceInfoStatus, 0xFFFF);
                m_isOSDNameUpdated = false;
                m_isVendorIDUpdated = false;
            }

            bool update(const VendorID &vendorId) {
                bool isVendorIdUpdated = false;
                if (!m_isVendorIDUpdated)
                    isVendorIdUpdated = true;
                else
                    isVendorIdUpdated = (m_vendorID.toString().compare(vendorId.toString())==0)?false:true;
                m_isVendorIDUpdated = true;
                m_vendorID = vendorId;
                return isVendorIdUpdated;
            }

            bool update(const OSDName &osdName) {
                bool isOSDNameUpdated = false;
                if (!m_isOSDNameUpdated)
                    isOSDNameUpdated = true;
                else
                    isOSDNameUpdated = (m_osdName.toString().compare(osdName.toString())==0)?false:true;
                m_isOSDNameUpdated = true;
                m_osdName = osdName;
                return isOSDNameUpdated;
            }
        };

        class HdmiCecSourceImplementation
            : public Exchange::IHdmiCecSource
            , public Exchange::IConfiguration
            , public DSHelper
        {
            enum {
                VOLUME_UP     = 0x41,
                VOLUME_DOWN   = 0x42,
                MUTE          = 0x43,
                UP            = 0x01,
                DOWN          = 0x02,
                LEFT          = 0x03,
                RIGHT         = 0x04,
                SELECT        = 0x00,
                HOME          = 0x09,
                BACK          = 0x0D,
                NUMBER_0      = 0x20,
                NUMBER_1      = 0x21,
                NUMBER_2      = 0x22,
                NUMBER_3      = 0x23,
                NUMBER_4      = 0x24,
                NUMBER_5      = 0x25,
                NUMBER_6      = 0x26,
                NUMBER_7      = 0x27,
                NUMBER_8      = 0x28,
                NUMBER_9      = 0x29
            };

        public:
            HdmiCecSourceImplementation();
            virtual ~HdmiCecSourceImplementation();
            void onPowerModeChanged(const PowerState currentState, const PowerState newState);
            void registerEventHandlers();
            static HdmiCecSourceImplementation* _instance;
            CECDeviceInfo_2 deviceList[16];
            pthread_cond_t m_condSig;
            pthread_mutex_t m_lock;
            pthread_cond_t m_condSigUpdate;
            pthread_mutex_t m_lockUpdate;
            bool cecEnableStatus;

            void SendStandbyMsgEvent(const int logicalAddress);
            void SendKeyPressMsgEvent(const int logicalAddress,const int keyCode);
            void SendKeyReleaseMsgEvent(const int logicalAddress);
            void sendActiveSourceEvent();
            void addDevice(const int logicalAddress);
            void removeDevice(const int logicalAddress);
            void sendUnencryptMsg(unsigned char* msg, int size);
            void sendDeviceUpdateInfo(const int logicalAddress);
            void sendKeyReleaseEvent(const int logicalAddress);
            Core::hresult setEnabledInternal(const bool enabled, const bool isPersist);
            typedef struct sendKeyInfo
            {
                int logicalAddr;
                int keyCode;
            } SendKeyInfo;

            BEGIN_INTERFACE_MAP(HdmiCecSourceImplementation)
                INTERFACE_ENTRY(Exchange::IHdmiCecSource)
                INTERFACE_ENTRY(Exchange::IConfiguration)
            END_INTERFACE_MAP

        private:
            template <typename T>
            T* baseInterface()
            {
                static_assert(std::is_base_of<T, HdmiCecSourceImplementation>(), "base type mismatch");
                return static_cast<T*>(this);
            }

            // -----------------------------------------------------------------------
            // Inner notification delegate: IDeviceSettingsVideoPort::INotification
            //
            // Receives OnResolutionPreChange / OnResolutionPostChange from
            // DeviceSettings.  A resolution change fires when the TV display
            // connects / disconnects (hotplug), which is the COM-RPC equivalent
            // of device::Host::IDisplayDeviceEvents::OnDisplayHDMIHotPlug.
            // -----------------------------------------------------------------------
            class DSVideoPortNotification
                : public Exchange::IDeviceSettingsVideoPort::INotification
            {
            public:
                explicit DSVideoPortNotification(HdmiCecSourceImplementation& parent)
                    : _parent(parent) {}

                DSVideoPortNotification(const DSVideoPortNotification&)            = delete;
                DSVideoPortNotification& operator=(const DSVideoPortNotification&) = delete;

                void OnResolutionPreChange(
                    const Exchange::IDeviceSettingsVideoPort::ResolutionChange& /*res*/) override
                {
                    // Nothing to do on pre-change
                }

                void OnResolutionPostChange(
                    const Exchange::IDeviceSettingsVideoPort::ResolutionChange& /*res*/) override
                {
                    _parent.onHdmiHotPlug(0 /* HDMI_HOT_PLUG_EVENT_CONNECTED */);
                }

                BEGIN_INTERFACE_MAP(DSVideoPortNotification)
                    INTERFACE_ENTRY(Exchange::IDeviceSettingsVideoPort::INotification)
                END_INTERFACE_MAP

            private:
                HdmiCecSourceImplementation& _parent;
            };

            // -----------------------------------------------------------------------
            // Inner notification delegate: IDeviceSettingsDisplay::IDisplayHDMIHotPlugNotification
            //
            // Receives OnDisplayHDMIHotPlug(DS_DISPLAY_EVENT_CONNECTED) on HDMI plug-in
            // and OnDisplayHDMIHotPlug(DS_DISPLAY_EVENT_DISCONNECTED) on unplug.
            // Registered in OnDeviceSettingsActivated() via disp->Register().
            // -----------------------------------------------------------------------
            class DSDisplayHotPlugNotification
                : public Exchange::IDeviceSettingsDisplay::IDisplayHDMIHotPlugNotification
            {
            public:
                explicit DSDisplayHotPlugNotification(HdmiCecSourceImplementation& parent)
                    : _parent(parent) {}

                DSDisplayHotPlugNotification(const DSDisplayHotPlugNotification&)            = delete;
                DSDisplayHotPlugNotification& operator=(const DSDisplayHotPlugNotification&) = delete;

                void OnDisplayHDMIHotPlug(
                    const Exchange::IDeviceSettingsDisplay::DisplayEvent displayEvent) override
                {
                    _parent.onHdmiHotPlug(
                        (displayEvent == Exchange::IDeviceSettingsDisplay::DS_DISPLAY_EVENT_CONNECTED)
                            ? 0  /* HDMI_HOT_PLUG_EVENT_CONNECTED */
                            : 1  /* disconnected */);
                }

                BEGIN_INTERFACE_MAP(DSDisplayHotPlugNotification)
                    INTERFACE_ENTRY(Exchange::IDeviceSettingsDisplay::IDisplayHDMIHotPlugNotification)
                END_INTERFACE_MAP

            private:
                HdmiCecSourceImplementation& _parent;
            };

            class PowerManagerNotification : public Exchange::IPowerManager::IModeChangedNotification {
            private:
                PowerManagerNotification(const PowerManagerNotification&) = delete;
                PowerManagerNotification& operator=(const PowerManagerNotification&) = delete;

            public:
                explicit PowerManagerNotification(HdmiCecSourceImplementation& parent)
                    : _parent(parent) {}
                ~PowerManagerNotification() override = default;

                void OnPowerModeChanged(const PowerState currentState, const PowerState newState) override
                {
                    _parent.onPowerModeChanged(currentState, newState);
                }

                template <typename T>
                T* baseInterface()
                {
                    static_assert(std::is_base_of<T, PowerManagerNotification>(), "base type mismatch");
                    return static_cast<T*>(this);
                }

                BEGIN_INTERFACE_MAP(PowerManagerNotification)
                    INTERFACE_ENTRY(Exchange::IPowerManager::IModeChangedNotification)
                END_INTERFACE_MAP

            private:
                HdmiCecSourceImplementation& _parent;
            };

            HdmiCecSourceImplementation(const HdmiCecSourceImplementation&) = delete;
            HdmiCecSourceImplementation& operator=(const HdmiCecSourceImplementation&) = delete;

            std::string logicalAddressDeviceType;
            bool cecSettingEnabled;
            bool cecOTPSettingEnabled;
            Connection *smConnection;
            int m_numberOfDevices;
            bool m_pollThreadExit;
            Utils::ThreadRAII m_pollThread;
            bool m_updateThreadExit;
            Utils::ThreadRAII m_UpdateThread;
            bool m_sendKeyEventThreadExit;
            bool m_sendKeyEventThreadRun;
            Utils::ThreadRAII m_sendKeyEventThread;
            std::mutex m_sendKeyEventMutex;
            std::queue<SendKeyInfo> m_SendKeyQueue;
            std::condition_variable m_sendKeyCV;

            HdmiCecSourceProcessor *msgProcessor;
            HdmiCecSourceFrameListener *msgFrameListener;

            void InitializePowerManager(PluginHost::IShell *service);
            void InitializeIARM();
            void DeinitializeIARM();
            void onHdmiHotPlug(int connectStatus);
            bool loadSettings();
            void persistSettings(bool enableStatus);
            void persistOTPSettings(bool enableStatus);
            void persistOSDName(const char *name);
            void persistVendorId(unsigned int vendorID);
            void CECEnable(void);
            void CECDisable(void);
            void getPhysicalAddress();
            void getLogicalAddress();
            void cecAddressesChanged(int changeStatus);
            bool pingDeviceUpdateList(int idev);
            void removeAllCecDevices();
            void requestVendorID(const int newDevlogicalAddress);
            void requestOsdName(const int newDevlogicalAddress);
            void requestCecDevDetails(const int logicalAddress);
            static void threadRun();
            static void threadUpdateCheck();
            static void threadSendKeyEvent();
            static void threadCecDaemonInitHandler();
            static void threadCecStatusUpdateHandler(int data);
            uint32_t sendKeyPressEvent(const int logicalAddress, int keyCode);
            int getUIKeyCode(int keyCode);

            // DSHelper provides cached video-port and audio-port handles (private).
            // Access via DSHelper::getCachedVideoPortHandle() etc.
            // _displayHandle is managed locally (DSHelper::LoadAllConfigs does not populate display handles).
            int32_t                                         _displayHandle { INVALID_DS_HANDLE };
            Core::Sink<DSVideoPortNotification>             _dsVideoPortNotification;
            Core::Sink<DSDisplayHotPlugNotification>        _dsDisplayHotPlugNotification;

            PowerManagerInterfaceRef _powerManagerPlugin;
            Core::Sink<PowerManagerNotification> _pwrMgrNotification;
            bool _registeredEventHandlers;

            mutable Core::CriticalSection _adminLock;
            std::list<Exchange::IHdmiCecSource::INotification*> _hdmiCecSourceNotifications;

            // DSHelper lifecycle
            void OnDeviceSettingsActivated() override;
            void OnDeviceSettingsDeactivated() override;

        public:
            Core::hresult SetEnabled(const bool &enabled, HdmiCecSourceSuccess &success) override;
            Core::hresult GetEnabled(bool &enabled, bool &success) override;
            Core::hresult SetOTPEnabled(const bool &enabled, HdmiCecSourceSuccess &success) override;
            Core::hresult GetOTPEnabled(bool &enabled, bool &success) override;
            Core::hresult SetOSDName(const string &name, HdmiCecSourceSuccess &success) override;
            Core::hresult GetOSDName(string &name, bool &success) override;
            Core::hresult SetVendorId(const string &vendorid, HdmiCecSourceSuccess &success) override;
            Core::hresult GetVendorId(string &vendorid, bool &success) override;
            Core::hresult PerformOTPAction(HdmiCecSourceSuccess &success) override;
            Core::hresult SendStandbyMessage(HdmiCecSourceSuccess &success) override;
            Core::hresult SendKeyPressEvent(const uint32_t &logicalAddress,const uint32_t &keyCode, HdmiCecSourceSuccess &success) override;
            Core::hresult GetActiveSourceStatus(bool &isActiveSource, bool &success) override;
            Core::hresult GetDeviceList(uint32_t &numberofdevices, IHdmiCecSourceDeviceListIterator*& deviceList, bool &success) override;
            Core::hresult Configure(PluginHost::IShell* service) override;
            Core::hresult Register(Exchange::IHdmiCecSource::INotification *notification) override;
            Core::hresult Unregister(Exchange::IHdmiCecSource::INotification *notification) override;
        };
    } // namespace Plugin
} // namespace WPEFramework
