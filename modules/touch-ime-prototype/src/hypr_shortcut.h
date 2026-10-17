#pragma once
#include <QByteArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QStringList>
#include <functional>

namespace omt {
struct CommandResult { bool ok; QByteArray output; };
using CommandRunner = std::function<CommandResult(const QString &, const QStringList &)>;

struct ShortcutTarget {
    QString address;
    int pid = 0;
    bool valid() const {
        static const QRegularExpression pattern("^0x[0-9a-fA-F]{1,16}$");
        return pattern.match(address).hasMatch() && address.mid(2).toULongLong(nullptr,16)!=0 && pid>0;
    }
    static ShortcutTarget parse(const QByteArray &data) {
        const auto state=QJsonDocument::fromJson(data).object();
        return {state.value("address").toString(),state.value("pid").toInt()};
    }
    bool operator==(const ShortcutTarget &) const = default;
};
// Presentation grace only after our own sensitive commit. Permissions still
// become unfocused immediately; no hidden panel is ever opened by this rule.
inline bool holdPasswordPanel(bool visible, bool sensitive, bool wayland,
                              qint64 commitAgeMs, const ShortcutTarget &target) {
    return visible && sensitive && wayland && commitAgeMs>=0 && commitAgeMs<100 && target.valid();
}
inline bool shortcutStateAllowed(const QJsonObject &fresh, quint32 expected,
                                 quint32 current, quint64 epoch, quint64 currentEpoch,
                                 bool focused, const QString &key) {
    return focused && expected==current && epoch==currentEpoch
        && fresh.value("protocol").toInt()==2 && fresh.value("generation").toInt(-1)==int(expected)
        && fresh.value("focused").toBool() && fresh.value("sensitive").isBool()
        && (!fresh.value("sensitive").toBool() || key=="Control+v");
}
// The expected window was captured when this focus generation became visible,
// never adopted at button dispatch. Reject a different compositor target even
// while Fcitx is still reporting the previous generation.
inline bool sendHyprShortcut(const QString &key, const ShortcutTarget &expected,
                             const CommandRunner &run, const std::function<bool()> &stillAllowed) {
    if (!QStringList{"Control+a", "Control+c", "Control+x", "Control+v"}.contains(key) || !expected.valid())
        return false;
    const auto window = run("/usr/bin/hyprctl", {"-j", "activewindow"});
    if (!window.ok) return false;
    const auto target=ShortcutTarget::parse(window.output);
    if (!target.valid() || target!=expected) return false;
    const auto address=target.address;
    const auto pid=target.pid;
    const auto lock = run("/usr/bin/omarchy-shell", {"lock", "isLocked"});
    if (!lock.ok || lock.output.trimmed()!="false" || !stillAllowed()) return false;
    const auto letter = key.right(1).toUpper();
    // Match Omarchy clipboard.lua: explicit down/up, released by the compositor
    // even if our process exits. Bind both events to the validated window.
    const auto script = QString(
        "local w=hl.get_active_window(); "
        "assert(w and w.address==\"%1\" and w.pid==%2 and w.active and w.accepts_input,\"input target changed\"); "
        "hl.dispatch(hl.dsp.send_key_state({mods=\"CTRL\",key=\"%3\",state=\"down\",window=w})); "
        "hl.timer(function() hl.dispatch(hl.dsp.send_key_state({mods=\"CTRL\",key=\"%3\",state=\"up\",window=w})) "
        "end,{timeout=50,type=\"oneshot\"})").arg(address).arg(pid).arg(letter);
    const auto sent = run("/usr/bin/hyprctl", {"eval", script});
    return sent.ok && sent.output.trimmed()=="ok";
}
}
