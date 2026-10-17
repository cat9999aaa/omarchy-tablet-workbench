#pragma once
#include <QObject>
#include <QDBusMessage>
#include <QDBusServiceWatcher>
#include <QJsonObject>

// Event-only after initial synchronization. Bind both actions and notifications
// to a unique bus owner so a replaced service cannot inherit pending input.
class FocusLink final : public QObject {
    Q_OBJECT
    QString owner_;
    QDBusServiceWatcher watcher_;
    quint64 epoch_ = 0, revision_ = 0;
    void setOwner(const QString &owner);
    void query(int attempt = 0);
    bool accept(const QString &json);
private slots:
    void notification(const QString &json, const QDBusMessage &message);
public:
    explicit FocusLink(QObject *parent = nullptr);
    void start();
    void refresh();
    QDBusMessage call(const QString &method, const QVariantList &args);
signals:
    void changed(const QJsonObject &state, quint64 epoch);
};
