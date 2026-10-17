#include "../src/focus_bridge.cpp"
#include <cassert>
#include <iostream>
#include <fcitx/inputmethodengine.h>
#include <fcitx/addonloader.h>
#include <QTemporaryDir>
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QElapsedTimer>
#include <QThread>
class SignalProbe : public QObject {
    Q_OBJECT
public:
    int count=0; QJsonObject last;
public slots:
    void received(const QString &value) { ++count;last=QJsonDocument::fromJson(value.toUtf8()).object(); }
};
class TestKeyboard : public fcitx::InputMethodEngine {
public:
    std::vector<fcitx::InputMethodEntry> listInputMethods() override {
        std::vector<fcitx::InputMethodEntry> entries;
        entries.emplace_back("keyboard-us", "Test keyboard", "en", "keyboard");
        return entries;
    }
    void keyEvent(const fcitx::InputMethodEntry &, fcitx::KeyEvent &) override {}
};
class TestKeyboardFactory : public fcitx::AddonFactory {
    fcitx::AddonInstance *create(fcitx::AddonManager *) override { return new TestKeyboard; }
};
class TestContext : public fcitx::InputContext {
public:
    std::string text;
    int keys = 0;
    fcitx::Key lastKey;
    explicit TestContext(fcitx::InputContextManager &m) : InputContext(m, "omt-test") { created(); }
    ~TestContext() override { destroy(); }
    const char *frontend() const override { return "omt-test"; }
    void commitStringImpl(const std::string &s) override { text += s; }
    void deleteSurroundingTextImpl(int, unsigned int) override {}
    void forwardKeyImpl(const fcitx::ForwardKeyEvent &e) override { ++keys; lastKey=e.rawKey(); }
    void updatePreeditImpl() override {}
};
int main(int argc, char **argv) {
    QCoreApplication app(argc,argv);
    QTemporaryDir config;
    setenv("XDG_CONFIG_HOME", config.path().toUtf8().constData(), 1);
    fcitx::Instance instance(argc, argv);
    TestKeyboardFactory keyboard;
    fcitx::StaticAddonRegistry registry{{"keyboard", &keyboard}};
    instance.addonManager().registerDefaultLoader(&registry);
    instance.initialize();
    fcitx::dbus::Bus bus(fcitx::dbus::BusType::Session);
    FocusBridge bridge(&instance.addonManager(), &bus);
    SignalProbe probe;
    auto subscriber=QDBusConnection::sessionBus();
    assert(subscriber.connect(QString::fromStdString(bus.uniqueName()),"/omt","org.pcadmin.TouchIme1","StateChanged",&probe,SLOT(received(QString))));
    subscriber.interface()->registeredServiceNames(); // subscription ordering barrier
    auto receive=[&](int expected) {
        bus.flush();QElapsedTimer timer;timer.start();
        while(probe.count<expected && timer.elapsed()<1000) {QCoreApplication::processEvents();QThread::msleep(1);}
        assert(probe.count==expected);
        assert(probe.last["protocol"].toInt()==2);
    };
    auto state = [&] { return QJsonDocument::fromJson(QByteArray::fromStdString(bridge.state())).object(); };
    assert(!state()["focused"].toBool());
    auto a = std::make_unique<TestContext>(instance.inputContextManager());
    a->focusIn();receive(1);assert(probe.last["focused"].toBool());
    auto generation=uint32_t(state()["generation"].toInt());
    assert(state()["focused"].toBool());
    assert(bridge.commit(generation,"你好") && a->text=="你好");
    assert(!bridge.key(generation,"XF86PowerOff"));
    assert(bridge.key(generation,"BackSpace") && a->keys==2);
    assert(bridge.key(generation,"Control+c") && a->keys==4);
    assert(a->lastKey==fcitx::Key("Control+c"));
    assert(bridge.key(generation,"Control+v") && a->keys==6);
    a->setCapabilityFlags(fcitx::CapabilityFlag::Preedit);
    assert(uint32_t(state()["generation"].toInt())==generation);
    a->setCapabilityFlags(fcitx::CapabilityFlag::Password);
    receive(2);assert(probe.last["sensitive"].toBool());
    assert(state()["sensitive"].toBool());
    assert(!bridge.commit(generation,"stale"));
    assert(!bridge.key(uint32_t(state()["generation"].toInt()),"Control+c"));
    generation=uint32_t(state()["generation"].toInt());
    a->focusOut();receive(3);assert(!probe.last["focused"].toBool());
    assert(!bridge.commit(generation,"unfocused"));
    a->focusIn();receive(4);
    generation=uint32_t(state()["generation"].toInt());
    a.reset();receive(5);assert(!probe.last["focused"].toBool());
    assert(!state()["focused"].toBool());
    assert(!bridge.commit(generation,"destroyed"));
    std::cout << "PASS real Fcitx contexts: commit, allowed keys, capability change, focus loss, destruction\n";
}

#include "test_bridge.moc"
