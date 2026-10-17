#include "../src/focus_bridge.cpp"
#include "../src/hypr_shortcut.h"
#include "../src/voice_output.h"
#include <cassert>
#include <algorithm>
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
    {
        const QByteArray envelope="Loading audio file: \"/tmp/speech.wav\"\nAudio format: 16000 Hz, 1 channel(s), Int\nProcessing 32000 samples (2.00s)...\n";
        auto result=omt::parseVoiceOutput(envelope+"\n你好测试\n");
        assert(result.valid && result.text=="你好测试");
        const auto spoken=QString("代码 /tmp/demo.py\nLoading audio file: 这是我说的文字");
        result=omt::parseVoiceOutput(envelope+"\n"+spoken.toUtf8()+"\n");
        assert(result.valid && result.text==spoken);
        assert(!omt::parseVoiceOutput("path /tmp/private.wav\n你好").valid);
        assert(!omt::parseVoiceOutput(envelope+"Unknown diagnostic\n\n你好").valid);
        assert(!omt::parseVoiceOutput(QByteArray(70000,'a')).valid);
        result=omt::parseVoiceOutput(envelope+"VAD: 0.00s speech (0.0% of audio)\nNo speech detected, skipping transcription.\n");
        assert(result.valid && result.text.isEmpty());
        result=omt::parseVoiceOutput(envelope+"\n");assert(result.valid && result.text.isEmpty());
        auto crlf=envelope+"\n你好\n";crlf.replace("\n","\r\n");
        assert(omt::parseVoiceOutput(crlf).text=="你好");
    }

    {
        using omt::CommandResult;
        // A restored Fcitx focus cannot authorize text before compositor target validation.
        assert(!omt::validTarget(7,7,true,true));
        assert(omt::validTarget(7,7,true,false));
        assert(!omt::validTarget(6,7,true,false));
        QStringList commands;
        const omt::ShortcutTarget expected{"0x123abc",123};
        assert(omt::holdPasswordPanel(true,true,true,0,expected));
        assert(omt::holdPasswordPanel(true,true,true,99,expected));
        assert(!omt::holdPasswordPanel(false,true,true,0,expected));
        assert(!omt::holdPasswordPanel(true,false,true,0,expected));
        assert(!omt::holdPasswordPanel(true,true,false,0,expected));
        assert(!omt::holdPasswordPanel(true,true,true,-1,expected));
        assert(!omt::holdPasswordPanel(true,true,true,100,expected));
        assert(!omt::holdPasswordPanel(true,true,true,0,{}));
        auto window=QByteArray("{\"address\":\"0x123abc\",\"pid\":123}");
        bool locked=false, allowed=true, evalOk=true;
        auto runner=[&](const QString &program,const QStringList &args) {
            commands.append(program+" "+args.join(" "));
            if(program=="/usr/bin/omarchy-shell")return CommandResult{true,locked?QByteArray("true"):QByteArray("false")};
            if(args.first()=="-j")return CommandResult{true,window};
            return CommandResult{evalOk,evalOk?QByteArray("ok"):QByteArray("error")};
        };
        auto permission=[&]{return allowed;};
        assert(omt::sendHyprShortcut("Control+c",expected,runner,permission));
        assert(commands.last().contains("state=\"down\"") && commands.last().contains("state=\"up\""));
        assert(commands.last().contains("window=w") && commands.last().contains("w.pid==123"));
        assert(commands.last().contains("timeout=50"));
        commands.clear();assert(!omt::sendHyprShortcut("Control+c;exec bad",expected,runner,permission));assert(commands.empty());
        for(const auto &bad : {QByteArray("{}"),QByteArray("{\"address\":\"0x0\",\"pid\":123}"),
             QByteArray("{\"address\":\"0x123;bad\",\"pid\":123}"),QByteArray("{\"address\":\"0x123\",\"pid\":0}")}) {
            window=bad;commands.clear();assert(!omt::sendHyprShortcut("Control+v",expected,runner,permission));
            assert(std::none_of(commands.begin(),commands.end(),[](const auto &s){return s.contains(" eval ");}));
        }
        window="{\"address\":\"0x456def\",\"pid\":456}";
        commands.clear();assert(!omt::sendHyprShortcut("Control+v",expected,runner,permission));
        assert(commands.size()==1); // Fcitx may still say A: never send to new window B.
        window="{\"address\":\"0x123abc\",\"pid\":123}";locked=true;
        commands.clear();assert(!omt::sendHyprShortcut("Control+a",expected,runner,permission));assert(!commands.last().contains(" eval "));
        locked=false;allowed=false;commands.clear();assert(!omt::sendHyprShortcut("Control+x",expected,runner,permission));assert(!commands.last().contains(" eval "));
        allowed=true;evalOk=false;assert(!omt::sendHyprShortcut("Control+v",expected,runner,permission));
        assert(!omt::sendHyprShortcut("Control+v",expected,[](const auto &,const auto &){return CommandResult{false,{}};},permission));
    }
    {
        QJsonObject fresh{{"protocol",2},{"generation",7},{"focused",true},{"sensitive",false}};
        auto allowed=[&](QString key="Control+c",quint32 current=7,quint64 epoch=3,bool focus=true){
            return omt::shortcutStateAllowed(fresh,7,current,3,epoch,focus,key);
        };
        assert(allowed());assert(!allowed("Control+c",8));assert(!allowed("Control+c",7,4));
        assert(!allowed("Control+c",7,3,false));
        fresh["generation"]=6;assert(!allowed());fresh["generation"]=7;
        fresh["sensitive"]=true;
        for(const auto &key:{"Control+a","Control+c","Control+x"})assert(!allowed(key));
        assert(allowed("Control+v"));
        fresh.remove("sensitive");assert(!allowed("Control+v"));
        fresh=QJsonObject{};assert(!allowed());
    }
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
