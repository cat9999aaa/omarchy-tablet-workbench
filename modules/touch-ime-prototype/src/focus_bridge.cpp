#include "target_gate.h"
#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/instance.h>
#include <fcitx/inputcontext.h>
#include <fcitx/event.h>
#include <dbus_public.h>
#include <fcitx-utils/dbus/objectvtable.h>
#include <QJsonDocument>
#include <QJsonObject>
#include <set>
#include <vector>

class FocusBridge final : public fcitx::AddonInstance, public fcitx::dbus::ObjectVTable<FocusBridge> {
    fcitx::Instance *instance_;
    fcitx::InputContext *active_ = nullptr;
    uint32_t generation_ = 1;
    uint32_t context_ = 1;
    fcitx::CapabilityFlags capabilities_;
    std::vector<std::unique_ptr<fcitx::HandlerTableEntry<fcitx::EventHandler>>> watchers_;
    bool usable(uint32_t expected) const {
        return omt::validTarget(expected, generation_, active_ && active_->hasFocus());
    }
public:
    explicit FocusBridge(fcitx::AddonManager *manager, fcitx::dbus::Bus *bus = nullptr) : instance_(manager->instance()) {
        if (!bus) {
            auto *dbus = manager->addon("dbus", true);
            if (!dbus) throw std::runtime_error("DBus unavailable");
            bus = dbus->call<fcitx::IDBusModule::bus>();
        }
        if (!bus->addObjectVTable("/omt", "org.pcadmin.TouchIme1", *this))
            throw std::runtime_error("Cannot register input bridge");
        for (auto type : {fcitx::EventType::InputContextFocusIn, fcitx::EventType::InputContextFocusOut,
                          fcitx::EventType::InputContextDestroyed, fcitx::EventType::InputContextCapabilityChanged}) {
            watchers_.push_back(instance_->watchEvent(type, fcitx::EventWatcherPhase::PostInputMethod,
                [this, type](fcitx::Event &event) {
                    auto *ic = static_cast<fcitx::InputContextEvent &>(event).inputContext();
                    if (type == fcitx::EventType::InputContextFocusIn) { active_ = ic; capabilities_=ic->capabilityFlags(); ++generation_; ++context_; }
                    else if (ic == active_) {
                        if(type==fcitx::EventType::InputContextCapabilityChanged) {
                            auto relevant=fcitx::CapabilityFlags(fcitx::CapabilityFlag::PasswordOrSensitive) | fcitx::CapabilityFlag::NoOnScreenKeyboard;
                            auto next=ic->capabilityFlags();
                            bool changed=(capabilities_ & relevant)!=(next & relevant);
                            capabilities_=next;
                            if(!changed) return;
                        } else ++context_;
                        ++generation_;
                        if (type != fcitx::EventType::InputContextCapabilityChanged) active_ = nullptr;
                    }
                }));
        }
    }
    std::string state() {
        bool focused = active_ && active_->hasFocus();
        bool sensitive = focused && bool(active_->capabilityFlags() & fcitx::CapabilityFlag::PasswordOrSensitive);
        bool noKeyboard = focused && active_->capabilityFlags().test(fcitx::CapabilityFlag::NoOnScreenKeyboard);
        QJsonObject o{{"generation", int(generation_)}, {"context",int(context_)}, {"focused", focused},
                      {"program", focused ? QString::fromStdString(active_->program()) : QString()},
                      {"frontend",focused ? QString(active_->frontend()) : QString()},
                      {"sensitive", sensitive}, {"noKeyboard", noKeyboard}};
        return QJsonDocument(o).toJson(QJsonDocument::Compact).toStdString();
    }
    bool commit(uint32_t expected, const std::string &text) {
        if (!usable(expected) || text.empty() || text.size() > 65536) return false;
        active_->commitString(text); return true;
    }
    bool key(uint32_t expected, const std::string &name) {
        static const std::set<std::string> allowed{"BackSpace", "Return", "Left", "Right", "Delete", "Home", "End", "Tab", "Escape", "Control+a", "Control+c", "Control+x", "Control+v"};
        if (!usable(expected) || !allowed.count(name)) return false;
        if (active_->capabilityFlags() & fcitx::CapabilityFlag::PasswordOrSensitive) {
            if (name=="Control+c" || name=="Control+x" || name=="Control+a") return false;
        }
        auto k = fcitx::Key(name);
        active_->forwardKey(k, false);
        active_->forwardKey(k, true);
        return true;
    }
    FCITX_OBJECT_VTABLE_METHOD(state, "State", "", "s");
    FCITX_OBJECT_VTABLE_METHOD(commit, "Commit", "us", "b");
    FCITX_OBJECT_VTABLE_METHOD(key, "Key", "us", "b");
};
class Factory final : public fcitx::AddonFactory {
    fcitx::AddonInstance *create(fcitx::AddonManager *manager) override { return new FocusBridge(manager); }
};
FCITX_ADDON_FACTORY(Factory)
