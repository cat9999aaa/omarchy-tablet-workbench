#pragma once
#include <QByteArray>
#include <QString>
#include <QRegularExpression>
namespace omt {
struct VoiceOutput { bool valid = false; QString text; };
// voxtype 1.1 transcribe prints a human-readable header even with --quiet.
// Accept its known framing only; never guess that unknown stdout is dictation.
inline VoiceOutput parseVoiceOutput(QByteArray bytes) {
    if(bytes.size()>65536)return {};
    bytes.replace("\r\n","\n");
    const QString data=QString::fromUtf8(bytes);
    static const QRegularExpression header(
        R"(^Loading audio file: "[^\n]*"\nAudio format: [0-9]+ Hz, [0-9]+ channel\(s\), (?:Int|Float)\n(?:Resampling from [0-9]+ Hz to 16000 Hz\.\.\.\n)?Processing [0-9]+ samples \([0-9]+\.[0-9]+s\)\.\.\.\n(?:VAD: [0-9]+\.[0-9]+s speech \([0-9]+\.[0-9]+% of audio\)\n)?)");
    const auto match=header.match(data);
    if(!match.hasMatch())return {};
    const auto body=data.mid(match.capturedLength());
    if(body=="No speech detected, skipping transcription.\n")return {true,{}};
    if(!body.startsWith('\n'))return {};
    return {true,body.mid(1).trimmed()};
}
}
