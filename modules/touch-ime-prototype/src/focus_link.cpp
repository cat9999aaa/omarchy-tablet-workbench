#include "focus_link.h"
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>
#include <QJsonDocument>
#include <QTimer>

namespace {
const QString service = QStringLiteral("org.fcitx.Fcitx5");
const QString path = QStringLiteral("/omt");
const QString interface = QStringLiteral("org.pcadmin.TouchIme1");
}
FocusLink::FocusLink(QObject *parent)
    : QObject(parent), watcher_(service, QDBusConnection::sessionBus(),
                              QDBusServiceWatcher::WatchForOwnerChange, this) {
    connect(&watcher_, &QDBusServiceWatcher::serviceOwnerChanged, this,
            [this](const QString &, const QString &, const QString &owner) {setOwner(owner);});
}
void FocusLink::start() {
    // Owner lookup is asynchronous too. A change signal supersedes this reply.
    auto epoch = epoch_;
    auto *pending = new QDBusPendingCallWatcher(
        QDBusConnection::sessionBus().interface()->asyncCall("GetNameOwner", service), this);
    connect(pending, &QDBusPendingCallWatcher::finished, this, [this,epoch](auto *p) {
        QDBusPendingReply<QString> reply = *p; p->deleteLater();
        if (epoch != epoch_) return;
        if (reply.isError()) emit changed({}, epoch_);
        else setOwner(reply.value());
    });
}
void FocusLink::setOwner(const QString &owner) {
    if (owner == owner_) return;
    auto bus = QDBusConnection::sessionBus();
    if (!owner_.isEmpty()) bus.disconnect(owner_, path, interface, "StateChanged", this,
                                         SLOT(notification(QString,QDBusMessage)));
    owner_ = owner; ++epoch_; ++revision_;
    emit changed({}, epoch_);
    if (owner_.isEmpty()) return;
    bus.connect(owner_, path, interface, "StateChanged", this,
                SLOT(notification(QString,QDBusMessage)));
    query();
}
bool FocusLink::accept(const QString &json) {
    const auto state = QJsonDocument::fromJson(json.toUtf8()).object();
    if (state.value("protocol").toInt() != 2 || state.value("generation").toInt() <= 0
        || !state.value("focused").isBool() || !state.value("sensitive").isBool()
        || !state.value("noKeyboard").isBool()) return false;
    emit changed(state, epoch_);
    return true;
}
void FocusLink::notification(const QString &json, const QDBusMessage &message) {
    if (owner_.isEmpty() || message.service() != owner_) return;
    ++revision_;
    if (!accept(json)) emit changed({}, epoch_);
}
void FocusLink::query(int attempt) {
    if (owner_.isEmpty()) return;
    const auto epoch=epoch_, revision=revision_;
    auto request=QDBusMessage::createMethodCall(owner_,path,interface,"State");
    auto *pending=new QDBusPendingCallWatcher(QDBusConnection::sessionBus().asyncCall(request, 500),this);
    connect(pending,&QDBusPendingCallWatcher::finished,this,[this,epoch,revision,attempt](auto *p) {
        QDBusPendingReply<QString> reply=*p;p->deleteLater();
        if(epoch!=epoch_ || revision!=revision_) return;
        if(!reply.isError() && accept(reply.value())) return;
        emit changed({},epoch_);
        // The service name can appear before the addon. Bounded startup retries;
        // once connected there is no timer and no idle State traffic.
        if(attempt<4) QTimer::singleShot(250*(attempt+1),this,[this,epoch,revision,attempt]{
            if(epoch==epoch_ && revision==revision_) query(attempt+1);
        });
    });
}
void FocusLink::refresh() { ++revision_; query(); }
QDBusMessage FocusLink::call(const QString &method,const QVariantList &args) {
    if(owner_.isEmpty()) return QDBusMessage::createError("org.pcadmin.Disconnected","No input service");
    auto request=QDBusMessage::createMethodCall(owner_,path,interface,method);
    request.setArguments(args);
    return QDBusConnection::sessionBus().call(request,QDBus::Block,300);
}

bool FocusLink::ownsCurrentService() const {
    if(owner_.isEmpty())return false;
    const auto current=QDBusConnection::sessionBus().interface()->serviceOwner(service);
    return current.isValid() && current.value()==owner_;
}
