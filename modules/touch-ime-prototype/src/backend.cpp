#include "engine.h"
#include "target_gate.h"
#include "focus_link.h"
#include "hypr_shortcut.h"
#include "voice_output.h"
#include <QProcessEnvironment>
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusMessage>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QSocketNotifier>
#include <QTemporaryDir>
#include <QTimer>
#include <QSettings>
#include <QFileInfo>
#include <QThread>
#include <QPointer>
#include <QElapsedTimer>
#include <fcntl.h>
#include <unistd.h>
#include <iostream>

class Backend : public QObject {
    omt::Engine engine_;
    QSettings settings_;
    bool learning_ = true;
    QString notice_;
    bool editingPhrase_ = false;
    QString phraseDraft_;
    QStringList phrases_;
    QString handwritingModel_;
    QProcess handwriting_;
    bool handwritingStopping_ = false;
    QTimer handwritingLimit_;
    uint32_t handwritingGeneration_ = 0;
    int handwritingRevision_ = 0;
    QStringList handwritingCandidates_;
    QByteArray handwritingOutput_;
    uint32_t generation_ = 0, voiceGeneration_ = 0;
    uint32_t context_ = 0;
    bool focused_ = false, sensitive_ = false, visible_ = false, noKeyboard_ = false;
    bool editingVoice_ = false;
    QString mode_ = "t9", error_, voiceText_, voicePhase_ = "idle";
    QProcess recorder_, recognizer_;
    FocusLink focusLink_;
    uint32_t bridgeGeneration_ = 0;
    quint64 ownerEpoch_ = 0;
    QString frontend_;
    omt::ShortcutTarget shortcutTarget_, heldPasswordTarget_;
    QElapsedTimer sensitiveCommit_;
    QTimer focusLossHide_;
    QPointer<QProcess> targetProbe_;
    quint64 targetTicket_ = 0;
    void captureShortcutTarget() {
        shortcutTarget_={};const auto ticket=++targetTicket_;
        if(targetProbe_){targetProbe_->kill();targetProbe_->deleteLater();targetProbe_=nullptr;}
        if(!visible_ || !focused_ || !frontend_.startsWith("wayland"))return;
        const auto generation=bridgeGeneration_;const auto epoch=ownerEpoch_;
        auto *probe=new QProcess(this);targetProbe_=probe;
        connect(probe,qOverload<int,QProcess::ExitStatus>(&QProcess::finished),this,
            [this,probe,ticket,generation,epoch](int code,QProcess::ExitStatus status){
                if(ticket==targetTicket_ && generation==bridgeGeneration_ && epoch==ownerEpoch_
                    && visible_ && focused_ && code==0 && status==QProcess::NormalExit)
                {
                    shortcutTarget_=omt::ShortcutTarget::parse(probe->readAllStandardOutput());
                    if(focusLossHide_.isActive()) {
                        focusLossHide_.stop();
                        if(!shortcutTarget_.valid() || shortcutTarget_!=heldPasswordTarget_)visible_=false;
                        heldPasswordTarget_={};publish();
                    }
                }
                probe->deleteLater();
            });
        QTimer::singleShot(250,probe,[probe]{if(probe->state()!=QProcess::NotRunning)probe->kill();});
        probe->start("/usr/bin/hyprctl",{"-j","activewindow"});
    }
    QTimer voiceLimit_, recognitionLimit_, stopLimit_;
    std::unique_ptr<QTemporaryDir> audioDir_;
    QByteArray input_, lastState_;
    bool current(uint32_t expected) const { return omt::validTarget(expected, generation_, focused_, focusLossHide_.isActive()); }
    bool commitTarget(const QString &text) {
        if(visible_ && sensitive_ && frontend_.startsWith("wayland"))sensitiveCommit_.start();
        auto r = focusLink_.call("Commit", {bridgeGeneration_, text});
        bool ok = r.type() == QDBusMessage::ReplyMessage && !r.arguments().isEmpty() && r.arguments().first().toBool();
        if (!ok) error_ = "输入位置已改变，请重新点输入框";
        return ok;
    }
    bool commit(const QString &text) {
        if(editingPhrase_){if(phraseDraft_.size()+text.size()<=64)phraseDraft_+=text;return true;}
        if (editingVoice_) { voiceText_ += text; return true; }
        return commitTarget(text);
    }
    void editingKey(const QString &key) {
        if (frontend_.startsWith("wayland") && key.startsWith("Control+")) {
            const auto expected = bridgeGeneration_;
            const auto epoch = ownerEpoch_;
            auto allowed = [&] {
                const auto reply=focusLink_.call("State", {});
                if(reply.type()!=QDBusMessage::ReplyMessage || reply.arguments().isEmpty())return false;
                const auto fresh=QJsonDocument::fromJson(reply.arguments().first().toString().toUtf8()).object();
                return omt::shortcutStateAllowed(fresh,expected,bridgeGeneration_,epoch,ownerEpoch_,focused_,key);
            };
            auto run=[](const QString &program,const QStringList &args) {
                QProcess child;child.start(program,args);
                if(!child.waitForFinished(250)) {child.kill();child.waitForFinished(250);return omt::CommandResult{false,{}};}
                return omt::CommandResult{child.exitStatus()==QProcess::NormalExit && child.exitCode()==0,child.readAllStandardOutput()};
            };
            const bool ok=omt::sendHyprShortcut(key,shortcutTarget_,run,allowed);
            // Only these low-frequency edit chords wait for the official 50 ms
            // release. No timer/polling is added to idle, focus or text paths.
            if(ok)QThread::msleep(70);
            else error_="编辑快捷键未完成，请重新点输入框后重试";
            return; // Never fall back to sending a bare letter through Wayland.
        }
        auto r = focusLink_.call("Key", {bridgeGeneration_, key});
        if (r.type()!=QDBusMessage::ReplyMessage || r.arguments().isEmpty() || !r.arguments().first().toBool())
            error_ = "当前没有可用的输入位置";
    }
    void cancelVoice() {
        voicePhase_ = "idle"; voiceText_.clear(); editingVoice_=false; voiceLimit_.stop(); recognitionLimit_.stop();stopLimit_.stop();
        if (recorder_.state()!=QProcess::NotRunning) { recorder_.terminate(); if (!recorder_.waitForFinished(500)) { recorder_.kill(); recorder_.waitForFinished(500); } }
        if (recognizer_.state()!=QProcess::NotRunning) { recognizer_.kill(); recognizer_.waitForFinished(500); }
        audioDir_.reset();
    }
    void stopVoice() {
        if (voicePhase_!="recording") return;
        voicePhase_="stopping"; voiceLimit_.stop(); recorder_.terminate();stopLimit_.start(2000);
    }
    void startVoice() {
        if (!focused_ || sensitive_ || voicePhase_!="idle") return;
        if(editingPhrase_){error_="请先保存或取消短语";return;}
        if (!engine_.snapshot().preedit.empty()) { error_="请先选字或清空拼音，再开始语音"; return; }
        QString runtime = qEnvironmentVariable("XDG_RUNTIME_DIR");
        if (runtime.isEmpty()) { error_="录音运行目录不可用"; return; }
        audioDir_ = std::make_unique<QTemporaryDir>(runtime+"/omt-audio-XXXXXX");
        if (!audioDir_->isValid()) { audioDir_.reset(); error_="不能创建临时录音"; return; }
        voiceGeneration_=generation_; voiceText_.clear(); voicePhase_="recording";
        recorder_.start("pw-record", {"--rate", "16000", "--channels", "1", "--format", "s16", audioDir_->filePath("speech.wav")});
        voiceLimit_.start(60000);
    }
public:
    Backend(const std::string &data, const std::string &user) : engine_(data,user), settings_(QString::fromStdString(user)+"/ime-settings.ini",QSettings::IniFormat) {
        focusLossHide_.setSingleShot(true);focusLossHide_.setInterval(150);
        connect(&focusLossHide_,&QTimer::timeout,this,[this]{visible_=false;heldPasswordTarget_={};captureShortcutTarget();publish();});
        phrases_=settings_.value("phrases",QStringList{}).toStringList();
        learning_=settings_.value("learning",true).toBool();engine_.setLearning(learning_);
        handwritingModel_=QFileInfo(QString::fromStdString(data)+"/../vendor/handwriting/models/handwriting-zh_CN.model").absoluteFilePath();
        handwritingLimit_.setSingleShot(true);handwritingLimit_.setInterval(3000);
        connect(&handwritingLimit_,&QTimer::timeout,this,[this]{clearHandwriting(true);error_="手写识别超时，请重写";publish();});
        connect(&handwriting_,&QProcess::readyReadStandardOutput,this,[this]{
            handwritingOutput_+=handwriting_.readAllStandardOutput();
            if(handwritingOutput_.size()>65536){clearHandwriting(true);return;}
            int end;while((end=handwritingOutput_.indexOf('\n'))>=0){
                auto line=handwritingOutput_.left(end);handwritingOutput_.remove(0,end+1);auto result=QJsonDocument::fromJson(line).object();
                if(result.value("revision").toInt(-1)!=handwritingRevision_ || !current(handwritingGeneration_) || sensitive_ || mode_!="handwriting")continue;
                handwritingLimit_.stop();handwritingCandidates_.clear();
                for(auto value:result.value("candidates").toArray())handwritingCandidates_.append(value.toString());
                error_=result.value("error").toString();publish();
            }
        });
        connect(&handwriting_,&QProcess::errorOccurred,this,[this](QProcess::ProcessError){if(handwritingStopping_)return;handwritingLimit_.stop();error_="手写识别器不可用，可继续使用拼音";publish();});
        connect(&handwriting_,qOverload<int,QProcess::ExitStatus>(&QProcess::finished),this,[this](int code,QProcess::ExitStatus){if(!handwritingStopping_&&code!=0&&mode_=="handwriting"){handwritingLimit_.stop();handwritingCandidates_.clear();error_="手写识别器已停止，请重新选择手写";publish();}});
        connect(&focusLink_, &FocusLink::changed, this, [this](const QJsonObject &s, quint64 epoch){ applyFocus(s, epoch); });
        voiceLimit_.setSingleShot(true); recognitionLimit_.setSingleShot(true);
        stopLimit_.setSingleShot(true);
        connect(&stopLimit_, &QTimer::timeout,this,[this]{cancelVoice();error_="录音未能正常停止，已取消并清理";publish();});
        connect(&voiceLimit_, &QTimer::timeout, this, [this]{stopVoice();});
        connect(&recognitionLimit_, &QTimer::timeout, this, [this]{cancelVoice();error_="语音识别超时，请重试";publish();});
        connect(&recorder_, &QProcess::errorOccurred, this, [this](QProcess::ProcessError e){
            if(e==QProcess::FailedToStart) {voicePhase_="idle";audioDir_.reset();error_="录音程序无法启动";publish();}
        });
        connect(&recorder_, qOverload<int,QProcess::ExitStatus>(&QProcess::finished), this, [this](int,QProcess::ExitStatus){
            stopLimit_.stop();
            if(voicePhase_=="recording") {cancelVoice();error_="录音意外停止，请重试";publish();return;}
            if(voicePhase_!="stopping" || !audioDir_ || !current(voiceGeneration_) || sensitive_) return;
            voicePhase_="transcribing";
            auto env=QProcessEnvironment::systemEnvironment();env.insert("RUST_LOG","off");recognizer_.setProcessEnvironment(env);
            recognizer_.start("voxtype", {"--quiet", "transcribe", audioDir_->filePath("speech.wav")});
            recognitionLimit_.start(120000);publish();
        });
        connect(&recognizer_, &QProcess::errorOccurred, this, [this](QProcess::ProcessError e){
            if(e==QProcess::FailedToStart) {voicePhase_="idle";audioDir_.reset();recognitionLimit_.stop();error_="离线识别程序无法启动";publish();}
        });
        connect(&recognizer_, qOverload<int,QProcess::ExitStatus>(&QProcess::finished), this, [this](int code,QProcess::ExitStatus status){
            recognitionLimit_.stop();
            if(voicePhase_!="transcribing") return;
            const auto result=omt::parseVoiceOutput(recognizer_.readAllStandardOutput());
            audioDir_.reset();voicePhase_="idle";
            if(current(voiceGeneration_) && !sensitive_ && code==0 && status==QProcess::NormalExit) {
                if(result.valid){voiceText_=result.text;if(voiceText_.isEmpty())error_="没有识别到说话内容，请重试";}
                else error_="语音结果格式不兼容，已阻止运行信息进入输入框";
            }
            else error_="识别未完成或输入位置已改变，请重试";
            publish();
        });
        auto *notifier=new QSocketNotifier(STDIN_FILENO,QSocketNotifier::Read,this);
        fcntl(STDIN_FILENO,F_SETFL,fcntl(STDIN_FILENO,F_GETFL)|O_NONBLOCK);
        connect(notifier,&QSocketNotifier::activated,this,[this,notifier]{
            char buffer[4096];ssize_t n;
            while((n=::read(STDIN_FILENO,buffer,sizeof buffer))>0) input_.append(buffer,n);
            if(n==0) {notifier->setEnabled(false);QCoreApplication::quit();return;}
            if(input_.size()>65536) {input_.clear();error_="输入请求过大";publish();return;}
            int end;
            while((end=input_.indexOf('\n'))>=0) {auto line=input_.left(end);input_.remove(0,end+1);auto d=QJsonDocument::fromJson(line);if(d.isObject()) action(d.object());}
        });
        focusLink_.start();
    }
    void clearHandwriting(bool stopWorker=false) {
        handwritingRevision_++;handwritingCandidates_.clear();handwritingLimit_.stop();
        if(stopWorker&&handwriting_.state()!=QProcess::NotRunning){handwritingStopping_=true;handwriting_.kill();handwriting_.waitForFinished(300);}
        handwritingOutput_.clear();
    }
    ~Backend() override {cancelVoice();clearHandwriting(true);}

    void applyFocus(const QJsonObject &s, quint64 epoch) {
        const bool mayHold=!s.value("focused").toBool() && epoch==ownerEpoch_
            && omt::holdPasswordPanel(visible_,sensitive_,frontend_.startsWith("wayland"),
                sensitiveCommit_.isValid()?sensitiveCommit_.elapsed():-1,shortcutTarget_);
        const auto previousTarget=shortcutTarget_;
        frontend_=s.value("frontend").toString();
        const auto next=uint32_t(s.value("generation").toInt());
        const bool focus=s.value("focused").toBool();
        if(next!=bridgeGeneration_ || focus!=focused_ || epoch!=ownerEpoch_
           || sensitive_!=s.value("sensitive").toBool() || noKeyboard_!=s.value("noKeyboard").toBool()) {
            editingPhrase_=false;phraseDraft_.clear();cancelVoice();clearHandwriting(true);engine_.clear();
            ++generation_;bridgeGeneration_=next;focused_=focus;ownerEpoch_=epoch;
            context_=uint32_t(s.value("context").toInt());
            sensitive_=s.value("sensitive").toBool();noKeyboard_=s.value("noKeyboard").toBool();
            // Only explicit P1/manual actions open the panel.
            if(!focused_ || noKeyboard_) {
                if(mayHold && !noKeyboard_) {heldPasswordTarget_=previousTarget;focusLossHide_.start();}
                else {visible_=false;focusLossHide_.stop();heldPasswordTarget_={};}
            } else if(focusLossHide_.isActive() && (!sensitive_ || !frontend_.startsWith("wayland"))) {
                visible_=false;focusLossHide_.stop();heldPasswordTarget_={};
            }
            error_.clear();
            if(sensitive_ || focusLossHide_.isActive()) mode_="abc";
            else {mode_="t9";engine_.mode("t9");}
            captureShortcutTarget();
        }
        if(s.isEmpty()) error_="等待输入服务连接，请稍后按 P1 重试";
        publish();
    }
    void publish() {
        auto e=engine_.snapshot();QJsonArray candidates;
        if(mode_=="handwriting"){for(auto &c:handwritingCandidates_)candidates.append(c);e.preedit="";}
        else for(auto &c:e.candidates)candidates.append(QString::fromStdString(c));
        QJsonArray phraseArray;for(auto &p:phrases_)phraseArray.append(p);
        QJsonObject s{{"editingPhrase",editingPhrase_},{"phraseDraft",phraseDraft_},{"phrases",phraseArray},{"learning",learning_},{"notice",notice_},{"handwritingRevision",handwritingRevision_},{"generation",int(generation_)},{"focused",focused_ && !focusLossHide_.isActive()},{"sensitive",sensitive_ || focusLossHide_.isActive()},
            {"visible",visible_},{"mode",mode_},{"preedit",QString::fromStdString(e.preedit)},
            {"candidates",candidates},{"page",e.page},{"lastPage",e.lastPage},{"error",error_},{"voicePhase",voicePhase_},{"voiceText",voiceText_},{"editingVoice",editingVoice_}};
        auto data=QJsonDocument(s).toJson(QJsonDocument::Compact);
        if(data!=lastState_) {lastState_=data;std::cout<<data.constData()<<'\n'<<std::flush;}
    }
    void action(const QJsonObject &a) {
        auto op=a.value("op").toString();error_.clear();
        if(op=="hide") {visible_=false;focusLossHide_.stop();heldPasswordTarget_={};captureShortcutTarget();editingPhrase_=false;phraseDraft_.clear();cancelVoice();clearHandwriting(true);publish();return;}
        if(op=="show" || op=="toggle") {if(!focused_)focusLink_.refresh();visible_=op=="show"?true:!visible_;focusLossHide_.stop();heldPasswordTarget_={};captureShortcutTarget();if(!visible_){editingPhrase_=false;phraseDraft_.clear();cancelVoice();clearHandwriting(true);}publish();return;}
        if(!current(uint32_t(a.value("generation").toInt()))) {error_="请先点选输入框";publish();return;}
        if(voicePhase_!="idle" && op!="voice") {error_="请先结束语音识别";publish();return;}
        if(op=="phraseStart" && !sensitive_) {engine_.clear();cancelVoice();editingPhrase_=true;phraseDraft_.clear();}
        else if(op=="phraseSave" && !sensitive_ && editingPhrase_) {
            if(!engine_.snapshot().preedit.empty())error_="请先选字，再保存短语";
            else if(!phraseDraft_.trimmed().isEmpty() && phrases_.size()<20){
                auto value=phraseDraft_.trimmed();value.replace('\n',' ');value.replace('\r',' ');value.replace('\t',' ');
                if(!phrases_.contains(value))phrases_.append(value);settings_.setValue("phrases",phrases_);settings_.sync();editingPhrase_=false;phraseDraft_.clear();notice_="常用短语已保存";
            }else error_="请先输入短语，最多保存20条";
        } else if(op=="phraseCancel") {editingPhrase_=false;phraseDraft_.clear();engine_.clear();}
        else if(op=="phraseDelete" && !sensitive_) {phrases_.removeAll(a.value("text").toString());settings_.setValue("phrases",phrases_);settings_.sync();notice_="短语已移除";}
        else if(op=="forget" && !sensitive_ && mode_!="handwriting") {
            auto state=engine_.snapshot();if(a.value("preedit").toString()!=QString::fromStdString(state.preedit)||a.value("page").toInt(-1)!=state.page)error_="候选已更新，请重新操作";
            else notice_=engine_.forgetCandidate(size_t(a.value("index").toInt(-1)))?"已降低该词候选优先级":"此候选无法移除";
        }
        else if(op=="learning" && !sensitive_) {
            if(!engine_.snapshot().preedit.empty())error_="请先选字或清空拼音，再切换学习";
            else{learning_=a.value("enabled").toBool();engine_.setLearning(learning_);settings_.setValue("learning",learning_);settings_.sync();notice_=learning_?"常用词学习已开启":"学习已暂停，暂不使用个人词频";}
        } else if(op=="dictionaryBackup" && !sensitive_) {
            if(!engine_.snapshot().preedit.empty())error_="请先选字，再备份词库";
            else notice_=engine_.backupDictionary()?"个人词库已备份到本机 Rime 同步目录":"词库备份未完成，请稍后重试";
        } else if(op=="handwritingClear") {
            if(mode_=="handwriting"){handwritingCandidates_.clear();handwritingRevision_=a.value("revision").toInt();handwritingLimit_.stop();}
        } else if(op=="handwriting" && mode_=="handwriting" && !sensitive_) {
            handwritingRevision_=a.value("revision").toInt();handwritingGeneration_=generation_;handwritingCandidates_.clear();
            if(handwriting_.state()==QProcess::NotRunning){handwritingStopping_=false;handwriting_.start(QCoreApplication::applicationDirPath()+"/omt-handwriting",{handwritingModel_});if(!handwriting_.waitForStarted(500)){error_="手写识别器无法启动";publish();return;}}
            auto request=QJsonDocument(a).toJson(QJsonDocument::Compact)+'\n';handwriting_.write(request);handwritingLimit_.start();
        } else if(op=="mode") {
            auto m=a.value("mode").toString();
            if(QStringList{"t9","pinyin","abc","number","symbols","handwriting"}.contains(m) && (!sensitive_ || (m!="t9"&&m!="pinyin"&&m!="handwriting"))) {
                clearHandwriting(true);engine_.clear();mode_=m;if(m=="t9"||m=="pinyin")engine_.mode(m.toStdString());
            }
        } else if(op=="choose" && !sensitive_) {
            if(mode_=="handwriting") {
                int index=a.value("index").toInt(-1);
                if(a.value("revision").toInt(-1)!=handwritingRevision_ || index<0||index>=handwritingCandidates_.size())error_="手写候选已更新，请重新选字";
                else{commit(handwritingCandidates_[index]);clearHandwriting();}
            }
            else if(a.value("preedit").toString()!=QString::fromStdString(engine_.snapshot().preedit) || a.value("page").toInt(-1)!=engine_.snapshot().page) error_="候选已更新，请重新选字";
            else {auto t=engine_.choose(size_t(a.value("index").toInt(-1)));if(!t.empty())commit(QString::fromStdString(t));}
        } else if(op=="page" && !sensitive_) {
            engine_.page(a.value("next").toBool());
        } else if(op=="clear") {clearHandwriting(true);engine_.clear();voiceText_.clear();phraseDraft_.clear();editingVoice_=false;notice_="本次输入已清空";}
        else if(op=="clearField" && !sensitive_) {
            if(!focusLink_.ownsCurrentService() || !a.value("confirmed").toBool() || editingVoice_ || editingPhrase_ || !engine_.snapshot().preedit.empty())error_="请确认清空当前输入框";
            else {
                const auto expected=bridgeGeneration_;const auto epoch=ownerEpoch_;
                editingKey("Control+a");
                const auto reply=focusLink_.call("State",{});
                const auto fresh=reply.type()==QDBusMessage::ReplyMessage && !reply.arguments().isEmpty()?QJsonDocument::fromJson(reply.arguments().first().toString().toUtf8()).object():QJsonObject{};
                if(error_.isEmpty() && epoch==ownerEpoch_ && focusLink_.ownsCurrentService() && fresh.value("protocol").toInt()==2 && fresh.value("focused").toBool() && fresh.value("sensitive").isBool() && !fresh.value("sensitive").toBool() && fresh.value("generation").toInt(-1)==int(expected))editingKey("BackSpace");
                else error_="输入位置发生变化，已取消清空";
            }
        }
        else if(op=="voice" && !sensitive_) {if(voicePhase_=="recording")stopVoice();else startVoice();}
        else if(op=="voiceEdit" && !sensitive_ && !voiceText_.isEmpty()) {editingVoice_=!editingVoice_;engine_.clear();}
        else if(op=="voiceCommit" && !sensitive_ && current(voiceGeneration_)) {
            if(!engine_.snapshot().preedit.empty()) error_="请先选字，再输入预览文字";
            else if(commitTarget(voiceText_)) {voiceText_.clear();editingVoice_=false;}
        }
        else if(op=="text") {
            if(!engine_.snapshot().preedit.empty()) error_="请先选字，再输入符号";
            else commit(a.value("text").toString());
        }
        else if(op=="key") {
            auto key=a.value("key").toString();auto before=engine_.snapshot();
            bool composing=!before.preedit.empty();
            if(key=="BackSpace" && a.value("localScope").toBool()) {
                if(composing)engine_.key(0xff08);
                else if(editingPhrase_){if(!phraseDraft_.isEmpty())phraseDraft_.chop(phraseDraft_.back().isLowSurrogate()&&phraseDraft_.size()>1?2:1);}
                else if(!voiceText_.isEmpty()){editingVoice_=true;voiceText_.chop(voiceText_.back().isLowSurrogate()&&voiceText_.size()>1?2:1);}
                // This press started on a local draft. Never fall through after it empties.
            }
            else if(key=="BackSpace" && composing) engine_.key(0xff08);
            else if((key=="Return" || key=="space") && composing) {engine_.key(' ');auto t=engine_.takeCommit();if(!t.empty())commit(QString::fromStdString(t));}
            else if(editingPhrase_ && key=="BackSpace") {
                if(!phraseDraft_.isEmpty()){int n=phraseDraft_.back().isLowSurrogate()&&phraseDraft_.size()>1?2:1;phraseDraft_.chop(n);}
            }
            else if(editingPhrase_ && key=="Return") {error_="请点保存短语";}
            else if(editingVoice_ && key=="BackSpace") {
                if(!voiceText_.isEmpty()) {int n=voiceText_.back().isLowSurrogate()&&voiceText_.size()>1?2:1;voiceText_.chop(n);}
            }
            else if(editingVoice_ && key=="Return") commit("\n");
            else if(key=="BackSpace" || key=="Return" || key=="Left" || key=="Right" || (!editingVoice_ && !editingPhrase_ && !composing && QStringList{"Control+a","Control+c","Control+x","Control+v"}.contains(key) && (!sensitive_ || key=="Control+v")))editingKey(key);
            else if(key=="space")commit(" ");
            else if(key.size()==1) {
                if(!sensitive_ && (mode_=="t9"||mode_=="pinyin")) {
                    auto utf=key.toLatin1();bool handled=engine_.key(utf[0]);auto t=engine_.takeCommit();
                    if(!t.empty())commit(QString::fromStdString(t));else if(!handled)commit(key);
                }else commit(key);
            }
        }
        publish();
    }
};
int main(int argc,char **argv) {
    QCoreApplication app(argc,argv);
    if(argc!=3) return 2;
    try {Backend backend(argv[1],argv[2]);return app.exec();}
    catch(const std::exception &) {std::cout<<"{\"visible\":false,\"error\":\"输入引擎初始化失败，请稍后按P1重试\"}\n"<<std::flush;return 1;}
}
